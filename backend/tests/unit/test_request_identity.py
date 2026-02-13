from starlette.requests import Request

from app.api.stores import _request_identity


def test_request_identity_prefers_x_forwarded_for():
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.42, 10.0.0.1")],
        "client": ("10.0.0.9", 12345),
    }
    request = Request(scope)
    assert _request_identity(request) == "203.0.113.42"


def test_request_identity_falls_back_to_client_host():
    scope = {"type": "http", "headers": [], "client": ("10.0.0.9", 12345)}
    request = Request(scope)
    assert _request_identity(request) == "10.0.0.9"
