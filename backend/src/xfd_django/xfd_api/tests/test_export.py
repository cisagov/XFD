"""Test export API (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
from http.cookies import SimpleCookie
import secrets

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


# =============================================================================
# Cookie auth + CSRF helpers
# =============================================================================
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


# =============================================================================
# Tests
# =============================================================================
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_summary_columns_default():
    """Test default summary columns."""
    client.cookies.clear()
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    response_no_cols = client.post(
        "/export",
        headers=_csrf_headers(),
        json={"collection": "summary", "mode": "json", "filters": {}, "columns": []},
    )
    assert response_no_cols.status_code == 200

    response_invalid_col = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {},
            "columns": ["invalid_column"],
        },
    )
    assert response_invalid_col.status_code == 422


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vulnerability_columns_default():
    """Test default vulnerability columns."""
    client.cookies.clear()
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    response_no_cols = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {},
            "columns": [],
        },
    )
    assert response_no_cols.status_code == 200

    response_invalid_col = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {},
            "columns": ["invalid_column"],
        },
    )
    assert response_invalid_col.status_code == 422


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_summary_user_filters():
    """Test summary filters for user based on user type."""
    client.cookies.clear()
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    _prime_client_auth_and_csrf(user)

    response = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response.status_code == 200

    # Regional admin - should succeed
    client.cookies.clear()
    user_two = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    _prime_client_auth_and_csrf(user_two)

    response_two = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_two.status_code == 200

    # Standard user - should be forbidden by the endpoint logic
    client.cookies.clear()
    user_three = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    _prime_client_auth_and_csrf(user_three)

    response_three = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_three.status_code == 403
    assert response_three.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vulnerability_user_filters():
    """Test vulnerability filters for user based on user type."""
    client.cookies.clear()
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    _prime_client_auth_and_csrf(user)

    response = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response.status_code == 200

    # Regional admin - should succeed
    client.cookies.clear()
    user_two = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    _prime_client_auth_and_csrf(user_two)

    response_two = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_two.status_code == 200

    # Standard user - should be forbidden by the endpoint logic
    client.cookies.clear()
    user_three = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    _prime_client_auth_and_csrf(user_three)

    response_three = client.post(
        "/export",
        headers=_csrf_headers(),
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_three.status_code == 403
    assert response_three.json() == {
        "detail": "You do not have permission to perform this action."
    }
