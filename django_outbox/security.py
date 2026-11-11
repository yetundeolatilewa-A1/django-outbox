"""SSRF protection for webhook URLs."""

import ipaddress
import socket
from urllib.parse import urlsplit

from . import conf


class UnsafeURLError(Exception):
    """The webhook URL points somewhere that is not allowed."""


def _is_public(ip: str) -> bool:
    address = ipaddress.ip_address(ip.split("%", 1)[0])  # drop IPv6 zone id
    if getattr(address, "ipv4_mapped", None):
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast


def validate_url(url: str) -> None:
    """Raise ``UnsafeURLError`` unless ``url`` is an http(s) URL to a public address.

    Every address the hostname resolves to must be public. Hosts listed in
    ``OUTBOX["ALLOWED_HOSTS"]`` and ``OUTBOX["ALLOW_PRIVATE_ADDRESSES"] = True``
    skip the address check (the scheme is always checked).

    Limitation: the name is resolved here and again when the request is made, so a
    hostile DNS server could still answer differently the second time (DNS
    rebinding). Run the worker in a network that cannot reach internal services
    if that matters for you.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeURLError(f"unsupported URL scheme: {parts.scheme or url!r}")
    host = parts.hostname
    if not host:
        raise UnsafeURLError("URL has no host")
    if conf.get("ALLOW_PRIVATE_ADDRESSES") or host in conf.get("ALLOWED_HOSTS"):
        return
    try:
        infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve {host!r}: {exc}") from exc
    for info in infos:
        ip = info[4][0]
        if not _is_public(ip):
            raise UnsafeURLError(f"{host!r} resolves to non-public address {ip}")
