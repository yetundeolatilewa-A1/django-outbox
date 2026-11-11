import uuid

from django.db import models
from django.utils import timezone


class Endpoint(models.Model):
    """A webhook destination."""

    name = models.CharField(max_length=100, unique=True)
    url = models.URLField(max_length=500)
    secret = models.CharField(
        max_length=200, help_text="Shared secret used to sign every request (HMAC-SHA256)."
    )
    previous_secret = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional old secret, still used to sign requests during a rotation. "
        "Clear it once the receiver only accepts the new secret.",
    )
    event_types = models.JSONField(
        default=list,
        blank=True,
        help_text='Patterns of event types to receive, e.g. ["order.*", "user.created"]. '
        'Empty or ["*"] receives everything.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    """An event recorded in the same transaction as the business change."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=200, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.event_type} ({self.id})"


class Delivery(models.Model):
    """One message to be delivered to one endpoint, with retry state."""

    class Status(models.TextChoices):
        PENDING = "pending"
        DELIVERED = "delivered"
        DEAD = "dead"

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="deliveries")
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name="deliveries")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_status_code = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "deliveries"
        constraints = [
            models.UniqueConstraint(fields=["message", "endpoint"], name="outbox_one_delivery_per_endpoint")
        ]
        indexes = [models.Index(fields=["status", "next_attempt_at"], name="outbox_due_idx")]

    def __str__(self):
        return f"{self.message_id} -> {self.endpoint.name} [{self.status}]"
