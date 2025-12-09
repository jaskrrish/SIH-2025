from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings
from django.utils import timezone

from .km_client import km_client, KMServiceClient
from .models import LocalQKDKey


def _parse_expires_at(raw_expires_at: Optional[str], ttl_seconds: int) -> datetime:
    """
    Parse an expires_at string from KM or fall back to ttl-based expiry.
    """
    if raw_expires_at:
        try:
            parsed = datetime.fromisoformat(raw_expires_at)
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone=timezone.utc)
            return parsed
        except Exception:
            # Fall back to ttl handling below
            pass
    return timezone.now() + timedelta(seconds=ttl_seconds)


class LocalKeyManager:
    """
    Local key manager that caches keys from the remote KM service in the
    backend database. Callers use this instead of talking to KM directly
    for key requests; cache hits avoid remote calls.
    """

    def __init__(self, remote_client: KMServiceClient, prefetch: Optional[int] = None):
        self.remote_client = remote_client
        self.prefetch = (
            prefetch
            if prefetch is not None
            else getattr(settings, "LOCAL_KM_PREFETCH", 2)
        )

    def request_key(
        self,
        requester_sae: str,
        recipient_sae: str,
        key_size: int = 256,
        ttl: int = 3600,
    ) -> dict:
        """
        Get a key for requester->recipient. Prefer cached unused keys; on miss
        fetch from remote KM, store extras (prefetch), and return one key.
        """
        cached = self._get_cached_key(requester_sae, recipient_sae, key_size)
        if cached:
            print(f"[LocalKM] ✅ Cache hit: Using key {cached.key_id} from local cache")
            return self._to_response(cached)

        # Check if we have any non-consumed keys for this pair (for debugging)
        now = timezone.now()
        available_count = LocalQKDKey.objects.filter(
            requester_sae=requester_sae,
            recipient_sae=recipient_sae,
            state__in=[LocalQKDKey.STATE_STORED, LocalQKDKey.STATE_SERVED],
            expires_at__gt=now,
        ).count()
        
        if available_count > 0:
            print(f"[LocalKM] ⚠️  Cache miss: Found {available_count} keys but none match key_size={key_size}")

        # Try to fetch from remote KM service
        try:
            fetched = []
            fetch_count = max(1, int(self.prefetch) + 1)
            for _ in range(fetch_count):
                remote_key = self.remote_client.request_key(
                    requester_sae=requester_sae,
                    recipient_sae=recipient_sae,
                    key_size=key_size,
                    ttl=ttl,
                )
                fetched.append(remote_key)
                self._persist_key(
                    remote_key,
                    requester_sae=requester_sae,
                    recipient_sae=recipient_sae,
                    key_size=key_size,
                    ttl=ttl,
                    state=LocalQKDKey.STATE_STORED,
                )

            # Serve the first fetched key and mark it served to avoid reuse.
            first_key = LocalQKDKey.objects.get(key_id=fetched[0]["key_id"])
            first_key.state = LocalQKDKey.STATE_SERVED
            first_key.served_at = timezone.now()
            first_key.save(update_fields=["state", "served_at"])

            print(f"[LocalKM] ✅ Fetched {len(fetched)} key(s) from remote KM and cached locally")
            return self._to_response(first_key)
        except Exception as e:
            # If remote fetch fails, check if we can use a larger key from cache
            fallback_key = (
                LocalQKDKey.objects.filter(
                    requester_sae=requester_sae,
                    recipient_sae=recipient_sae,
                    key_size__gte=key_size,
                    state__in=[LocalQKDKey.STATE_STORED, LocalQKDKey.STATE_SERVED],
                    expires_at__gt=now,
                )
                .order_by("created_at")
                .first()
            )
            
            if fallback_key:
                print(f"[LocalKM] ⚠️  Remote KM unavailable, using fallback key {fallback_key.key_id} (size={fallback_key.key_size})")
                fallback_key.state = LocalQKDKey.STATE_SERVED
                fallback_key.served_at = timezone.now()
                fallback_key.save(update_fields=["state", "served_at"])
                return self._to_response(fallback_key)
            
            # No fallback available, re-raise the original error
            raise Exception(f"KM service unavailable and no local keys found: {str(e)}")

    def get_key_by_id(self, key_id: str, requester_sae: str) -> dict:
        """
        Delegate retrieval to remote KM. Local cache does not hold recipient
        (KM2) keys, so this remains a pass-through.
        """
        return self.remote_client.get_key_by_id(key_id=key_id, requester_sae=requester_sae)

    def consume_key(self, key_id: str, requester_sae: str) -> bool:
        """
        Mark key as consumed both locally (if present) and remotely.
        """
        updated = LocalQKDKey.objects.filter(key_id=key_id).update(
            state=LocalQKDKey.STATE_CONSUMED,
            consumed_at=timezone.now(),
        )
        remote_ok = self.remote_client.consume_key(
            key_id=key_id, requester_sae=requester_sae
        )
        return bool(updated) or remote_ok

    def _get_cached_key(
        self, requester_sae: str, recipient_sae: str, key_size: int
    ) -> Optional[LocalQKDKey]:
        """
        Return an unexpired non-consumed key and mark it served for one-time use.
        Looks for stored keys first, but will also reuse served keys if no stored ones exist.
        """
        now = timezone.now()
        
        # First try to find a stored (unused) key
        key = (
            LocalQKDKey.objects.filter(
                requester_sae=requester_sae,
                recipient_sae=recipient_sae,
                key_size=key_size,
                state=LocalQKDKey.STATE_STORED,
                expires_at__gt=now,
            )
            .order_by("created_at")
            .first()
        )
        
        # If no stored key found, try to reuse a served (but not consumed) key
        if not key:
            key = (
                LocalQKDKey.objects.filter(
                    requester_sae=requester_sae,
                    recipient_sae=recipient_sae,
                    key_size=key_size,
                    state=LocalQKDKey.STATE_SERVED,
                    expires_at__gt=now,
                )
                .order_by("created_at")
                .first()
            )
        
        # If still no key, try with any key_size >= requested (for flexibility)
        if not key:
            key = (
                LocalQKDKey.objects.filter(
                    requester_sae=requester_sae,
                    recipient_sae=recipient_sae,
                    key_size__gte=key_size,
                    state__in=[LocalQKDKey.STATE_STORED, LocalQKDKey.STATE_SERVED],
                    expires_at__gt=now,
                )
                .order_by("created_at")
                .first()
            )

        if key:
            key.state = LocalQKDKey.STATE_SERVED
            key.served_at = now
            key.save(update_fields=["state", "served_at"])
        else:
            # Cleanup expired keys opportunistically
            LocalQKDKey.objects.filter(expires_at__lte=now).delete()
        return key

    def _persist_key(
        self,
        remote_key: dict,
        requester_sae: str,
        recipient_sae: str,
        key_size: int,
        ttl: int,
        state: str,
    ):
        expires_at = _parse_expires_at(remote_key.get("expires_at"), ttl)
        LocalQKDKey.objects.update_or_create(
            key_id=remote_key["key_id"],
            defaults={
                "requester_sae": requester_sae,
                "recipient_sae": recipient_sae,
                "key_material_b64": remote_key["key_material"],
                "key_size": key_size,
                "algorithm": remote_key.get("algorithm", "BB84"),
                "expires_at": expires_at,
                "state": state,
            },
        )

    @staticmethod
    def _to_response(key_obj: LocalQKDKey) -> dict:
        """
        Convert cached model to the response shape used by callers.
        """
        return {
            "key_id": key_obj.key_id,
            "key_material": key_obj.key_material_b64,
            "size": key_obj.key_size,
            "algorithm": key_obj.algorithm,
            "expires_at": key_obj.expires_at.isoformat(),
        }


# Singleton instance used by crypto modules
local_km_manager = LocalKeyManager(km_client)

