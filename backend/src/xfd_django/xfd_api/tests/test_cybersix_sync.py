"""Test DMZ Sync CyberSix API endpoint (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
from http.cookies import SimpleCookie
import uuid

# Third-Party Libraries
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
import xfd_api.api_methods.dmz_sync as cybersix_module  # adjust path if needed
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)

CSRF_HEADER_NAME = "X-CSRF-Token"


def _apply_set_cookie_headers_to_client(resp: StarletteResponse) -> None:
    """Copy Set-Cookie headers from a Starlette response into the TestClient cookie jar."""
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
    """Prime TestClient with auth + csrf cookies using production helper."""
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
    """Return dict with CSRF header for TestClient based on its cookies."""
    csrf_cookie_name = None
    for k in client.cookies.keys():
        lk = k.lower()
        if "csrf" in lk or "xsrf" in lk:
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


@pytest.fixture
def admin_user(db):
    """Create a global-admin user."""
    return User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_success(admin_user, monkeypatch):
    """When fetch_cybersix_data returns payload+checksum, endpoint 201+headers."""
    dummy_payload = {
        "alerts": [],
        "mentions": [],
        "breaches": [],
        "exposures": [],
        "subdomains": [],
        "topcves": [],
    }
    dummy_checksum = "deadbeef"

    async def fake_fetch():
        return dummy_payload, dummy_checksum

    monkeypatch.setattr(cybersix_module, "fetch_cybersix_data", fake_fetch)

    _prime_client_auth_and_csrf(admin_user)

    response = client.post(
        "/dmz_sync/cybersix_sync",
        headers=_csrf_headers(),
    )

    assert response.status_code == 201

    expected = {
        "status": "ok",
        "payload": {
            "alerts": [],
            "mentions": [],
            "breaches": [],
            "exposures": [],
            "subdomains": [],
            "topcves": [],
            "current_page": 1,
            "total_pages": 1,
        },
    }
    assert response.json() == expected
    assert response.headers["X-Salted-Checksum"] == dummy_checksum


def test_cybersix_sync_unauthenticated():
    """Missing auth (no cookies) -> 401 from auth layer (CSRF not enforced)."""
    client.cookies.clear()

    response = client.post("/dmz_sync/cybersix_sync")
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_fetch_error(admin_user, monkeypatch):
    """Generic exception in fetch_cybersix_data → 500 Sync error."""

    async def fake_fetch():
        raise RuntimeError("database down")

    monkeypatch.setattr(cybersix_module, "fetch_cybersix_data", fake_fetch)

    _prime_client_auth_and_csrf(admin_user)

    response = client.post(
        "/dmz_sync/cybersix_sync",
        headers=_csrf_headers(),
    )

    assert response.status_code == 500
    assert "Sync error: database down" in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_http_exception(admin_user, monkeypatch):
    """A HTTPException in fetch_cybersix_data is re-raised as is."""

    async def fake_fetch():
        raise FastAPIHTTPException(status_code=418, detail="I'm a teapot")

    monkeypatch.setattr(cybersix_module, "fetch_cybersix_data", fake_fetch)

    _prime_client_auth_and_csrf(admin_user)

    response = client.post(
        "/dmz_sync/cybersix_sync",
        headers=_csrf_headers(),
    )

    assert response.status_code == 418
    assert response.json()["detail"] == "I'm a teapot"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_cookie_auth_missing_csrf_header_is_forbidden(admin_user):
    """Auth cookie present but CSRF header missing -> 403."""
    client.cookies.clear()
    _prime_client_auth_and_csrf(admin_user)

    # Intentionally omit CSRF header
    response = client.post("/dmz_sync/cybersix_sync")

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"
