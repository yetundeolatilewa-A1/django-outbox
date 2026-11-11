import pytest
from django.db import transaction

from django_outbox import publish
from django_outbox.models import Delivery, Endpoint, Message

pytestmark = pytest.mark.django_db


def make_endpoint(name, event_types=None, **kw):
    return Endpoint.objects.create(
        name=name, url=f"https://{name}.example.com/hook", secret="s", event_types=event_types or [], **kw
    )


def test_creates_one_delivery_per_matching_endpoint():
    a = make_endpoint("a")  # empty list = everything
    b = make_endpoint("b", ["order.*"])
    make_endpoint("c", ["user.created"])
    make_endpoint("d", is_active=False)

    message = publish("order.paid", {"id": 1})

    endpoints = set(message.deliveries.values_list("endpoint__name", flat=True))
    assert endpoints == {a.name, b.name}


def test_exact_and_wildcard_patterns():
    make_endpoint("exact", ["user.created"])
    make_endpoint("star", ["*"])
    message = publish("user.created", {})
    assert message.deliveries.count() == 2
    assert publish("user.deleted", {}).deliveries.count() == 1


@pytest.mark.django_db(transaction=True)
def test_rolls_back_with_the_surrounding_transaction():
    make_endpoint("a")

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            publish("order.paid", {"id": 1})
            raise RuntimeError("business logic failed")

    assert Message.objects.count() == 0
    assert Delivery.objects.count() == 0
