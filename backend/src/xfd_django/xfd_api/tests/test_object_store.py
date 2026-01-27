"""Tests for the object-store API endpoint (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
from http.cookies import SimpleCookie
import secrets
from unittest.mock import patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_CANDIDATES = ("csrf", "xsrf", "csrf-token", "xsrf-token", "csrf_token")


def _apply_set_cookie_headers_to_client(resp: StarletteResponse) -> None:
    set_cookie_headers = resp.headers.getlist("set-cookie")
    if not set_cookie_headers:
        raise AssertionError(
            "No Set-Cookie headers were set by set_auth_and_csrf_cookies()"
        )

    for set_cookie in set_cookie_headers:
        c: SimpleCookie = SimpleCookie()
        c.load(set_cookie)
        for name, morsel in c.items():
            client.cookies.set(name, morsel.value)


def _prime_client_auth_and_csrf(user: User) -> None:
    token = create_jwt_token(user)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"host", b"testserver"),
            (b"x-forwarded-proto", b"http"),
        ],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
    }
    req = StarletteRequest(scope)

    resp = StarletteResponse()
    set_auth_and_csrf_cookies(resp, token, req)
    _apply_set_cookie_headers_to_client(resp)


def _csrf_headers() -> dict:
    csrf_cookie_name = None
    for k in client.cookies.keys():
        lk = k.lower()
        if any(tok in lk for tok in CSRF_COOKIE_CANDIDATES):
            csrf_cookie_name = k
            break

    if not csrf_cookie_name:
        raise AssertionError(
            f"No CSRF cookie found. Cookies present: {list(client.cookies.keys())}"
        )

    csrf_val = client.cookies.get(csrf_cookie_name)
    if not csrf_val:
        raise AssertionError(f"CSRF cookie '{csrf_cookie_name}' had no value")

    return {CSRF_HEADER_NAME: csrf_val}


@pytest.fixture(autouse=True)
def _clear_client_cookies_between_tests():
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.api_methods.object_store.S3Client")
@patch("xfd_api.api_methods.object_store.ALLOWED_BUCKETS", new=["ignored-bucket"])
def test_get_presigned_url_basic(mock_s3_client):
    """Basic test for /v1/object-store/presigned-url that skips bucket checks."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Prime cookie auth + CSRF
    _prime_client_auth_and_csrf(user)

    # Mock S3
    mock_s3_client_instance = mock_s3_client.return_value
    mock_s3_client_instance.get_presigned_url.return_value = (
        "https://mocked-url.com/object"
    )

    payload = {"bucket_name": "ignored-bucket", "object_key": "some/file.txt"}

    response = client.post(
        "/v1/object-store/presigned-url",
        json=payload,
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"url": "https://mocked-url.com/object"}


@pytest.mark.django_db
def test_get_object_not_found():
    """Test retrieving a nonexistent object."""
    response = client.get("/v1/object-store/nonexistent-key")
    assert response.status_code == 404
