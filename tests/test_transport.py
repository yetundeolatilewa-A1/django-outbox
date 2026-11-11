import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from django_outbox.transport import TransportError, send_http


@pytest.fixture(autouse=True)
def allow_local(settings):
    # The test server listens on 127.0.0.1, which SSRF protection blocks by default.
    settings.OUTBOX = {**settings.OUTBOX, "ALLOW_PRIVATE_ADDRESSES": True}


def serve(status, location=None):
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            received["sig"] = self.headers.get("X-Outbox-Signature")
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, received


@pytest.mark.parametrize("status", [200, 204, 404, 500])
def test_returns_status_code(status):
    server, received = serve(status)
    try:
        url = f"http://127.0.0.1:{server.server_port}/hook"
        code = send_http(url, b"{}", {"X-Outbox-Signature": "abc"}, timeout=5)
    finally:
        server.shutdown()
    assert code == status
    assert received == {"body": b"{}", "sig": "abc"}


def test_connection_refused_raises_transport_error():
    with pytest.raises(TransportError):
        send_http("http://127.0.0.1:1/hook", b"{}", {}, timeout=2)


def test_redirects_are_not_followed():
    target, target_received = serve(200)
    redirector, _ = serve(302, location=f"http://127.0.0.1:{target.server_port}/internal")
    try:
        code = send_http(f"http://127.0.0.1:{redirector.server_port}/hook", b"{}", {}, timeout=5)
    finally:
        target.shutdown()
        redirector.shutdown()
    assert code == 302
    assert target_received == {}


def test_blocked_url_raises_transport_error(settings):
    settings.OUTBOX = {**settings.OUTBOX, "ALLOW_PRIVATE_ADDRESSES": False}
    with pytest.raises(TransportError, match="blocked"):
        send_http("http://169.254.169.254/latest/meta-data", b"{}", {}, timeout=2)


def test_rejects_non_http_schemes():
    with pytest.raises(TransportError):
        send_http("file:///etc/passwd", b"{}", {}, timeout=2)
