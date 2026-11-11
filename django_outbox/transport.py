"""HTTP transport. Replaceable in tests or via ``process_pending(send=...)``."""

import urllib.error
import urllib.request


class TransportError(Exception):
    """The request could not be completed (DNS, refused, timeout, bad scheme...)."""


def send_http(url: str, body: bytes, headers: dict, timeout: float) -> int:
    """POST ``body`` and return the HTTP status code (4xx/5xx are returned, not raised)."""
    if not url.lower().startswith(("http://", "https://")):
        raise TransportError(f"unsupported URL scheme: {url!r}")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TransportError(str(exc)) from exc
