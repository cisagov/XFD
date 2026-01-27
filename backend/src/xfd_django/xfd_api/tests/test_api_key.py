"""Test API key endpoints (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
import hashlib
from http.cookies import SimpleCookie
import secrets
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import ApiKey, User, UserType

client = TestClient(app)

CSRF_HEADER_NAME = "X-CSRF-Token"
AUTH_COOKIE_NAMES = ("crossfeed-token", "token")


def _apply_set_cookie_headers_to_client(resp: StarletteResponse) -> None:
    """Copy Set-Cookie headers from a Starlette response into the TestClient cookie jar."""
    # Starlette response supports getlist
    set_cookie_headers = resp.headers.getlist("set-cookie")
    if not set_cookie_headers:
        raise AssertionError(
            "No Set-Cookie headers were set by set_auth_and_csrf_cookies()"
        )

    for set_cookie in set_cookie_headers:
        c: SimpleCookie = SimpleCookie()
        c.load(set_cookie)

        # Each Set-Cookie header typically contains exactly one cookie,
        # but SimpleCookie supports multiple.
        for name, morsel in c.items():
            value = morsel.value
            # Domain/path flags in Set-Cookie don't matter for TestClient cookie jar;
            # we just need the name/value sent back on subsequent requests.
            client.cookies.set(name, value)


def _prime_client_auth_and_csrf(user: User) -> None:
    """Prime TestClient with auth + csrf cookies using production helper."""
    token = create_jwt_token(user)

    # Fake minimal request object for helper (adjust headers/scheme if your helper uses them)
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
    """Find the CSRF cookie and echo it back in the CSRF header."""
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


# ---------------- Tests ----------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_api_key_as_global_view_admin():
    """Test creating an API key as a global-view admin user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.post("/api-keys", headers=_csrf_headers())

    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert len(data["api_key"]) == 32

    assert ApiKey.objects.filter(user=user).exists()
    api_key_instance = ApiKey.objects.get(user=user)
    assert api_key_instance.last_four == data["api_key"][-4:]
    assert (
        hashlib.sha256(data["api_key"].encode()).hexdigest()
        == api_key_instance.hashed_key
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_api_key_as_regular_user_fails():
    """Test creating an API key as a regular standard user fails."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.post("/api-keys", headers=_csrf_headers())

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}
    assert not ApiKey.objects.filter(user=user).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_api_key_as_global_view_admin():
    """Test deleting an API key as a global-view admin user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.delete(f"/api-keys/{api_key.id}", headers=_csrf_headers())

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "API Key deleted successfully",
    }
    assert not ApiKey.objects.filter(id=api_key.id).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_api_key_as_regular_user_fails():
    """Test deleting an API key as a regular standard user fails."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.delete(f"/api-keys/{api_key.id}", headers=_csrf_headers())

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}
    assert ApiKey.objects.filter(id=api_key.id).exists()
