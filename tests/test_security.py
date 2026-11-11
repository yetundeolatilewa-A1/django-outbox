import pytest

from django_outbox.security import UnsafeURLError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/hook",
        "http://localhost/hook",
        "http://10.0.0.5/hook",
        "http://192.168.1.10/hook",
        "http://169.254.169.254/latest/meta-data",  # cloud metadata endpoint
        "http://[::1]/hook",
        "http://[::ffff:127.0.0.1]/hook",
        "http://0.0.0.0/hook",
    ],
)
def test_blocks_non_public_addresses(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/x", "http:///nohost"])
def test_blocks_bad_schemes_and_missing_host(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_allows_public_ip():
    validate_url("https://93.184.216.34/hook")


def test_allow_private_setting(settings):
    settings.OUTBOX = {**settings.OUTBOX, "ALLOW_PRIVATE_ADDRESSES": True}
    validate_url("http://127.0.0.1/hook")


def test_allowed_hosts_bypass(settings):
    settings.OUTBOX = {**settings.OUTBOX, "ALLOWED_HOSTS": ["localhost"]}
    validate_url("http://localhost/hook")
    with pytest.raises(UnsafeURLError):
        validate_url("http://127.0.0.1/hook")


def test_unresolvable_host_is_blocked():
    with pytest.raises(UnsafeURLError):
        validate_url("http://does-not-exist.invalid/hook")
