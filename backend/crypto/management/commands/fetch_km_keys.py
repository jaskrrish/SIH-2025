from django.core.management.base import BaseCommand
from django.utils import timezone

from crypto.km_client import km_client
from crypto.local_km import _parse_expires_at
from crypto.models import LocalQKDKey


DEFAULT_SENDER = "jaskrrishpvt@gmail.com"
DEFAULT_RECIPIENT = "jeyasurya0207@gmail.com"
DEFAULT_KEY_SIZE = 1024


class Command(BaseCommand):
    help = (
        "Fetch QKD keys from remote KM service and cache them locally in the DB "
        "for reuse by the crypto app."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=30,
            help="Number of keys to prefetch from KM (default: 30)",
        )

    def handle(self, *args, **options):
        count = max(1, options["count"])
        stored = 0
        skipped_consumed = 0
        consumed_ids = []

        for _ in range(count):
            remote_key = km_client.request_key(
                requester_sae=DEFAULT_SENDER,
                recipient_sae=DEFAULT_RECIPIENT,
                key_size=DEFAULT_KEY_SIZE,
                ttl=3600,
            )

            expires_at = _parse_expires_at(remote_key.get("expires_at"), 3600)

            obj, created = LocalQKDKey.objects.update_or_create(
                key_id=remote_key["key_id"],
                defaults={
                    "requester_sae": DEFAULT_SENDER,
                    "recipient_sae": DEFAULT_RECIPIENT,
                    "key_material_b64": remote_key["key_material"],
                    "key_size": DEFAULT_KEY_SIZE,
                    "algorithm": remote_key.get("algorithm", "BB84"),
                    "expires_at": expires_at,
                    # Keep existing state if already consumed; otherwise store
                    "state": LocalQKDKey.STATE_STORED,
                },
            )

            if not created and obj.state == LocalQKDKey.STATE_CONSUMED:
                skipped_consumed += 1
                consumed_ids.append(obj.key_id)
                continue

            # If this was previously consumed but recreated via defaults above, restore consumed flag
            if obj.state == LocalQKDKey.STATE_CONSUMED:
                skipped_consumed += 1
                consumed_ids.append(obj.key_id)
                continue

            obj.state = LocalQKDKey.STATE_STORED
            obj.served_at = None
            obj.consumed_at = None
            obj.save(update_fields=["state", "served_at", "consumed_at"])

            stored += 1

        consumed_note = (
            f" Skipped {skipped_consumed} consumed keys: {', '.join(consumed_ids)}"
            if skipped_consumed
            else ""
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Fetched {stored} key(s) of size {DEFAULT_KEY_SIZE} bits "
                f"for {DEFAULT_SENDER} -> {DEFAULT_RECIPIENT}.{consumed_note}"
            )
        )

