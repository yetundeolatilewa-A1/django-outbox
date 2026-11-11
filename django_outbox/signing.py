"""Request signing, Stripe-style: ``t=<unix ts>,v1=<hex hmac of "<ts>.<body>">``."""

import hashlib
import hmac
import time


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def verify(secret: str, header: str, body: bytes, tolerance: int = 300, now: float | None = None) -> bool:
    """Check a signature header. Use this in the *receiving* service."""
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        ts = int(parts["t"])
        given = parts["v1"]
    except (KeyError, ValueError):
        return False
    current = time.time() if now is None else now
    if tolerance is not None and abs(current - ts) > tolerance:
        return False
    expected = sign(secret, body, ts).split("v1=", 1)[1]
    return hmac.compare_digest(expected, given)
