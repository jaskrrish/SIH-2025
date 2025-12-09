from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from .local_km import LocalKeyManager
from .km_client import KMServiceClient
from .models import LocalQKDKey


class LocalKMCacheTests(TestCase):
    def setUp(self):
        # Use a mock remote client for deterministic tests
        self.remote_client = mock.Mock(spec=KMServiceClient)
        self.local_km = LocalKeyManager(self.remote_client, prefetch=0)

    def _remote_response(self, key_id="k1"):
        return {
            "key_id": key_id,
            "key_material": "YWJj",  # base64("abc")
            "size": 256,
            "algorithm": "BB84",
            "expires_at": (timezone.now() + timedelta(hours=1)).isoformat(),
        }

    def test_cache_miss_fetches_remote_and_persists(self):
        self.remote_client.request_key.return_value = self._remote_response("k-miss")

        resp = self.local_km.request_key(
            requester_sae="alice@example.com",
            recipient_sae="bob@example.com",
            key_size=256,
            ttl=3600,
        )

        self.assertEqual(resp["key_id"], "k-miss")
        self.assertEqual(LocalQKDKey.objects.count(), 1)
        entry = LocalQKDKey.objects.first()
        self.assertEqual(entry.state, LocalQKDKey.STATE_SERVED)
        self.remote_client.request_key.assert_called_once()

    def test_cache_hit_returns_without_remote(self):
        expires_at = timezone.now() + timedelta(hours=1)
        LocalQKDKey.objects.create(
            key_id="k-hit",
            requester_sae="alice@example.com",
            recipient_sae="bob@example.com",
            key_material_b64="YWJj",
            key_size=256,
            algorithm="BB84",
            expires_at=expires_at,
            state=LocalQKDKey.STATE_STORED,
        )

        resp = self.local_km.request_key(
            requester_sae="alice@example.com",
            recipient_sae="bob@example.com",
            key_size=256,
            ttl=3600,
        )

        self.assertEqual(resp["key_id"], "k-hit")
        entry = LocalQKDKey.objects.get(key_id="k-hit")
        self.assertEqual(entry.state, LocalQKDKey.STATE_SERVED)
        self.remote_client.request_key.assert_not_called()
