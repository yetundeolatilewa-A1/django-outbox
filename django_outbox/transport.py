"""HTTP transport. Replaceable in tests or via ``process_pending(send=...)``."""

import urllib.error
import urllib.request

from .security import UnsafeURLError, validate_url


class TransportError(Exception):
    """The request could not be completed (DNS, refused, timeout, blocked URL...)."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: a public URL could redirect to an internal one."""

    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def send_http(url: str, body: bytes, headers: dict, timeout: float) -> int:
    """POST ``body`` and return the HTTP status code (3xx/4xx/5xx are returned, not raised)."""
    try:
        validate_url(url)
    except UnsafeURLError as exc:
        raise TransportError(f"blocked: {exc}") from exc
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with _opener.open(request, timeout=timeout) as response:  # noqa: S310
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TransportError(str(exc)) from exc
