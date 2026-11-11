from django_outbox.signing import sign, verify

BODY = b'{"hello":"world"}'


def test_roundtrip():
    header = sign("s3cret", BODY, timestamp=1000)
    assert verify("s3cret", header, BODY, now=1000)


def test_wrong_secret_or_tampered_body_fails():
    header = sign("s3cret", BODY, timestamp=1000)
    assert not verify("other", header, BODY, now=1000)
    assert not verify("s3cret", header, BODY + b" ", now=1000)


def test_stale_timestamp_rejected():
    header = sign("s3cret", BODY, timestamp=1000)
    assert not verify("s3cret", header, BODY, tolerance=300, now=1500)
    assert verify("s3cret", header, BODY, tolerance=600, now=1500)


def test_malformed_header_rejected():
    assert not verify("s3cret", "garbage", BODY)
    assert not verify("s3cret", "t=abc,v1=00", BODY)
