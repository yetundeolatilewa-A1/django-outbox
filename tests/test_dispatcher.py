import json
from datetime import timedelta

import pytest
from django.utils import timezone

from django_outbox import publish
from django_outbox.dispatcher import process_pending
from django_outbox.models import Delivery, Endpoint
from django_outbox.signing import verify
from django_outbox.transport import TransportError

pytestmark = pytest.mark.django_db


class FakeSend:
    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.calls = []

    def __call__(self, url, body, headers, timeout):
        self.calls.append((url, body, headers, timeout))
        result = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def endpoint():
    return Endpoint.objects.create(name="shop", url="https://shop.example.com/hook", secret="topsecret")


def test_successful_delivery_is_signed_and_marked_delivered(endpoint):
    message = publish("order.paid", {"id": 7})
    send = FakeSend(200)

    stats = process_pending(send=send)

    assert (stats.delivered, stats.retried, stats.dead) == (1, 0, 0)
    delivery = Delivery.objects.get()
    assert delivery.status == "delivered" and delivery.attempts == 1 and delivery.delivered_at
    url, body, headers, _ = send.calls[0]
    assert url == endpoint.url
    assert verify("topsecret", headers["X-Outbox-Signature"], body)
    assert headers["X-Outbox-Id"] == str(message.id)
    assert json.loads(body)["data"] == {"id": 7}


def test_failure_schedules_retry_with_backoff(endpoint):
    publish("order.paid", {})
    now = timezone.now()

    stats = process_pending(send=FakeSend(500), now=now)

    assert stats.retried == 1
    delivery = Delivery.objects.get()
    assert delivery.status == "pending" and delivery.attempts == 1
    assert delivery.last_status_code == 500
    assert delivery.next_attempt_at == now + timedelta(seconds=10)


def test_transport_error_is_recorded_and_retried(endpoint):
    publish("order.paid", {})
    process_pending(send=FakeSend(TransportError("connection refused")))
    delivery = Delivery.objects.get()
    assert delivery.last_status_code is None
    assert "connection refused" in delivery.last_error


def test_becomes_dead_after_max_attempts(endpoint):
    publish("order.paid", {})
    send = FakeSend(503)
    now = timezone.now()
    for i in range(3):  # MAX_ATTEMPTS = 3 in test settings
        stats = process_pending(send=send, now=now + timedelta(hours=i))
    assert stats.dead == 1
    delivery = Delivery.objects.get()
    assert delivery.status == "dead" and delivery.attempts == 3
    # Dead deliveries are never picked up again.
    assert process_pending(send=send, now=now + timedelta(days=1)).processed == 0


def test_not_due_yet_is_skipped(endpoint):
    publish("order.paid", {})
    now = timezone.now()
    process_pending(send=FakeSend(500), now=now)
    send = FakeSend(200)
    assert process_pending(send=send, now=now + timedelta(seconds=5)).processed == 0
    assert send.calls == []
    assert process_pending(send=send, now=now + timedelta(seconds=11)).delivered == 1


def test_delivered_is_not_sent_twice(endpoint):
    publish("order.paid", {})
    send = FakeSend(200)
    process_pending(send=send)
    process_pending(send=send)
    assert len(send.calls) == 1


def test_inactive_endpoint_is_skipped(endpoint):
    publish("order.paid", {})
    endpoint.is_active = False
    endpoint.save()
    send = FakeSend(200)
    assert process_pending(send=send).processed == 0
    assert send.calls == []


def test_batch_size_limits_work(endpoint):
    for i in range(5):
        publish("order.paid", {"i": i})
    assert process_pending(send=FakeSend(200), batch_size=2).delivered == 2


def test_signs_with_both_secrets_while_rotating(endpoint):
    endpoint.previous_secret = "oldsecret"
    endpoint.save()
    publish("order.paid", {})
    send = FakeSend(200)
    process_pending(send=send)
    _, body, headers, _ = send.calls[0]
    assert verify("topsecret", headers["X-Outbox-Signature"], body)
    assert verify("oldsecret", headers["X-Outbox-Signature"], body)
