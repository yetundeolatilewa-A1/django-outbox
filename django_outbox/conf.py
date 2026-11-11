"""Settings access. Configure via ``OUTBOX = {...}`` in your Django settings."""

from django.conf import settings

DEFAULTS = {
    # Attempts (including the first) before a delivery is marked dead.
    "MAX_ATTEMPTS": 8,
    # Delay after the first failure; doubles on every further failure.
    "BACKOFF_BASE_SECONDS": 10,
    "BACKOFF_MAX_SECONDS": 3600,
    # Fraction (0..1) of random extra delay, to avoid retry stampedes.
    "BACKOFF_JITTER": 0.1,
    # Per-request HTTP timeout.
    "TIMEOUT_SECONDS": 10,
    # Deliveries handled per dispatcher pass.
    "BATCH_SIZE": 50,
    # SSRF protection: webhook URLs resolving to private, loopback, link-local or
    # other non-public addresses are refused unless allowed here.
    "ALLOW_PRIVATE_ADDRESSES": False,
    # Hostnames that bypass the check, e.g. ["billing.internal.example.com"].
    "ALLOWED_HOSTS": [],
}


def get(name):
    return {**DEFAULTS, **getattr(settings, "OUTBOX", {})}[name]
