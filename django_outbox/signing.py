"""Request signing, Stripe-style: ``t=<unix ts>,v1=<hex hmac of "<ts>.<body>">``.

During a secret rotation the header carries one ``v1`` value per active secret,
so a receiver can verify with either the old or the new secret.
"""

import hashlib
import hmac
import time


def _mac(secret: str, body: bytes, ts: int) -> str:
    return hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def sign(secret: str, body: bytes, timestamp: int | None = None, previous_secret: str = "") -> str:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    header = f"t={ts},v1={_mac(secret, body, ts)}"
    if previous_secret:
        header += f",v1={_mac(previous_secret, body, ts)}"
    return header


def verify(secret, header: str, body: bytes, tolerance: int = 300, now: float | None = None) -> bool:
    """Check a signature header. Use this in the *receiving* service.

    ``secret`` may be a single string or an iterable of strings (all accepted),
    which lets a receiver accept old and new secrets while rotating.
    """
    secrets = [secret] if isinstance(secret, str) else list(secret)
    ts = None
    signatures = []
    try:
        for item in header.split(","):
            key, sep, value = item.strip().partition("=")
            if not sep:
                return False
            if key == "t":
                ts = int(value)
            elif key == "v1":
                signatures.append(value)
    except ValueError:
        return False
    if ts is None or not signatures:
        return False
    current = time.time() if now is None else now
    if tolerance is not None and abs(current - ts) > tolerance:
        return False
    return any(
        hmac.compare_digest(_mac(s, body, ts), given) for s in secrets for given in signatures
    )
