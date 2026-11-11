from fnmatch import fnmatchcase

from django.db import transaction

from .models import Delivery, Endpoint, Message


def _matches(endpoint: Endpoint, event_type: str) -> bool:
    patterns = endpoint.event_types or ["*"]
    return any(fnmatchcase(event_type, pattern) for pattern in patterns)


def publish(event_type: str, payload: dict, *, using: str | None = None) -> Message:
    """Record an event for delivery to every matching active endpoint.

    Call this *inside* the same transaction as the change it describes. If that
    transaction rolls back, the message and its deliveries roll back with it, so
    no webhook is ever sent for a change that did not happen.
    """
    with transaction.atomic(using=using):
        message = Message.objects.using(using).create(event_type=event_type, payload=payload)
        endpoints = [
            e for e in Endpoint.objects.using(using).filter(is_active=True) if _matches(e, event_type)
        ]
        Delivery.objects.using(using).bulk_create(
            [Delivery(message=message, endpoint=e, next_attempt_at=message.created_at) for e in endpoints]
        )
    return message
