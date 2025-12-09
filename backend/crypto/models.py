from django.db import models
from django.utils import timezone


class LocalQKDKey(models.Model):
    """
    Local cache entry for QKD keys fetched from the remote KM service.
    Keys are stored for reuse to reduce remote KM calls on key requests.
    """

    STATE_STORED = "stored"
    STATE_SERVED = "served"
    STATE_CONSUMED = "consumed"

    STATE_CHOICES = (
        (STATE_STORED, "Stored"),
        (STATE_SERVED, "Served"),
        (STATE_CONSUMED, "Consumed"),
    )

    key_id = models.CharField(max_length=100, unique=True)
    requester_sae = models.CharField(max_length=255)
    recipient_sae = models.CharField(max_length=255)
    key_material_b64 = models.TextField()
    key_size = models.IntegerField(default=256)
    algorithm = models.CharField(max_length=50, default="BB84")
    expires_at = models.DateTimeField()
    state = models.CharField(
        max_length=16, choices=STATE_CHOICES, default=STATE_STORED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    served_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["requester_sae", "recipient_sae", "key_size"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["state"]),
        ]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def __str__(self) -> str:
        return f"{self.key_id} ({self.requester_sae} -> {self.recipient_sae})"
