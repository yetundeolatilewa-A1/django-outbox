import json
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import conf, transport
from .backoff import compute_delay
from .models import Delivery
from .signing import sign


@dataclass
class Stats:
    delivered: int = 0
    retried: int = 0
    dead: int = 0

    @property
    def processed(self) -> int:
        return self.delivered + self.retried + self.dead


def build_body(message) -> bytes:
    envelope = {
        "id": str(message.id),
        "type": message.event_type,
        "created_at": message.created_at.isoformat(),
        "data": message.payload,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()


def _attempt(delivery, send, now):
    body = build_body(delivery.message)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "django-outbox/0.1",
        "X-Outbox-Id": str(delivery.message_id),
        "X-Outbox-Event": delivery.message.event_type,
        "X-Outbox-Signature": sign(
            delivery.endpoint.secret, body, previous_secret=delivery.endpoint.previous_secret
        ),
    }
    delivery.attempts += 1
    try:
        status = send(delivery.endpoint.url, body, headers, conf.get("TIMEOUT_SECONDS"))
    except transport.TransportError as exc:
        delivery.last_status_code = None
        delivery.last_error = str(exc)[:1000]
        return False
    delivery.last_status_code = status
    if 200 <= status < 300:
        delivery.last_error = ""
        return True
    delivery.last_error = f"HTTP {status}"
    return False


def process_pending(*, batch_size=None, now=None, send=None, using=None) -> Stats:
    """Deliver due deliveries once and record the outcome of each.

    Rows are locked with ``SELECT ... FOR UPDATE SKIP LOCKED`` where the database
    supports it, so several dispatcher processes can run side by side without
    delivering the same row twice.
    """
    send = send or transport.send_http
    batch_size = batch_size or conf.get("BATCH_SIZE")
    now = now or timezone.now()
    stats = Stats()

    with transaction.atomic(using=using):
        due = (
            Delivery.objects.using(using)
            .select_for_update(skip_locked=True, of=("self",))
            .select_related("message", "endpoint")
            .filter(status=Delivery.Status.PENDING, next_attempt_at__lte=now, endpoint__is_active=True)
            .order_by("next_attempt_at")[:batch_size]
        )
        for delivery in due:
            if _attempt(delivery, send, now):
                delivery.status = Delivery.Status.DELIVERED
                delivery.delivered_at = timezone.now()
                stats.delivered += 1
            elif delivery.attempts >= conf.get("MAX_ATTEMPTS"):
                delivery.status = Delivery.Status.DEAD
                stats.dead += 1
            else:
                wait = compute_delay(
                    delivery.attempts,
                    conf.get("BACKOFF_BASE_SECONDS"),
                    conf.get("BACKOFF_MAX_SECONDS"),
                    conf.get("BACKOFF_JITTER"),
                )
                delivery.next_attempt_at = now + timedelta(seconds=wait)
                stats.retried += 1
            delivery.save(using=using)
    return stats
