import pytest
from django.core.management import call_command

from django_outbox import publish
from django_outbox.models import Delivery, Endpoint

pytestmark = pytest.mark.django_db


def test_system_checks_pass():
    call_command("check")


def test_run_outbox_once(monkeypatch, capsys):
    Endpoint.objects.create(name="a", url="https://a.example.com/h", secret="s")
    publish("thing.happened", {})
    monkeypatch.setattr("django_outbox.transport.send_http", lambda *a, **k: 200)

    call_command("run_outbox", "--once")

    assert Delivery.objects.get().status == "delivered"
    assert "delivered=1" in capsys.readouterr().out
