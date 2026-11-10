# django-outbox

Reliable, signed webhook delivery for Django, built on the **transactional outbox** pattern.

Sending a webhook straight from your view or signal handler has two failure modes: the request goes out
but your transaction rolls back (you told the world about something that never happened), or the
transaction commits but the process dies before the request is sent (the event is lost). `django-outbox`
avoids both. You record the event in the **same database transaction** as your change; a separate worker
delivers it afterwards, retrying with exponential backoff until it succeeds or is marked dead.

**Who it's for:** Django developers who need to notify other services (or customers) about events and
can't afford to lose or invent them. **Built with:** Python 3.10+, Django 4.2+, no other dependencies.

## Features

- Events written atomically with your data (`publish()` joins the caller's transaction)
- Per-endpoint event filters with wildcards (`order.*`)
- HMAC-SHA256 signed requests with a timestamp, plus a `verify()` helper for receivers
- Exponential backoff with jitter, a max-attempt limit and a "dead" state you can inspect and retry
- Safe to run several workers: rows are claimed with `SELECT ... FOR UPDATE SKIP LOCKED` where supported
- Django admin for endpoints, messages and deliveries, including a "retry" action
- `manage.py run_outbox` worker with graceful shutdown on SIGTERM/SIGINT

## Quick start

```bash
pip install django-outbox   # not yet on PyPI: pip install git+https://github.com/yetundeolatilewa-A1/django-outbox
```

```python
# settings.py
INSTALLED_APPS = [..., "django_outbox"]

OUTBOX = {            # all optional, these are the defaults
    "MAX_ATTEMPTS": 8,
    "BACKOFF_BASE_SECONDS": 10,
    "BACKOFF_MAX_SECONDS": 3600,
    "BACKOFF_JITTER": 0.1,
    "TIMEOUT_SECONDS": 10,
    "BATCH_SIZE": 50,
}
```

```bash
python manage.py migrate
```

Create an endpoint (in the admin, or in code), then publish inside your transaction:

```python
from django.db import transaction
from django_outbox import publish

with transaction.atomic():
    order.mark_paid()
    publish("order.paid", {"order_id": order.id, "total": str(order.total)})
```

Run the worker (one or more processes):

```bash
python manage.py run_outbox            # loop forever
python manage.py run_outbox --once     # single pass, handy for cron
```

## What the receiver gets

`POST` with a JSON body and these headers:

| Header | Meaning |
|---|---|
| `X-Outbox-Id` | Unique message id. Use it to de-duplicate. |
| `X-Outbox-Event` | Event type, e.g. `order.paid` |
| `X-Outbox-Signature` | `t=<unix time>,v1=<hex HMAC-SHA256 of "<t>.<raw body>">` |

```python
from django_outbox.signing import verify

ok = verify(secret, request.headers["X-Outbox-Signature"], request.body, tolerance=300)
```

Any `2xx` response counts as delivered. Anything else (or a network error) is retried.

## Guarantees and limits

- **At-least-once.** A receiver can see the same message twice (for example if it answers after the
  timeout). Treat `X-Outbox-Id` as an idempotency key.
- **No ordering guarantee** between messages, especially across retries.
- The worker keeps row locks while it makes HTTP calls, so keep `TIMEOUT_SECONDS` and `BATCH_SIZE` modest.
- Endpoint URLs are trusted (admin-managed). There is no private-network blocking yet; see the roadmap.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```

See [ROADMAP.md](ROADMAP.md) for planned work and [CONTRIBUTING.md](CONTRIBUTING.md) to help.

## License

MIT, see [LICENSE](LICENSE).
