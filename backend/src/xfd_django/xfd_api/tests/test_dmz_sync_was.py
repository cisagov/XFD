"""Tests for the /dmz_sync/was_findings endpoint (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import date, datetime, timezone
from http.cookies import SimpleCookie
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import User, WasFindings

client = TestClient(app)

CSRF_HEADER_NAME = "X-CSRF-Token"


def is_hex_sha256(candidate: str) -> bool:
    """Return True if the provided string appears to be a 64-char lowercase hex sha256."""
    if not candidate or len(candidate) != 64:
        return False
    for ch in candidate:
        if ch not in "0123456789abcdef":
            return False
    return True


# =============================================================================
# Cookie auth + CSRF helpers (same pattern as your passing api_key tests)
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


def _auth_post(user: User, url: str, params: dict):
    """POST with cookie auth + CSRF."""
    client.cookies.clear()
    _prime_client_auth_and_csrf(user)
    return client.post(url, headers=_csrf_headers(), params=params)


# =============================================================================
# Tests
# =============================================================================
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_empty_db():
    """Endpoint should return ok, empty payload, and checksum when DB has no findings."""
    now = datetime.now(timezone.utc)
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="globalAdmin",  # must match string check in is_global_write_admin
        created_at=now,
        updated_at=now,
    )

    response = _auth_post(
        admin_user,
        "/dmz_sync/was_findings",
        params={"page": 1, "per_page": 100},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert body["payload"] == []
    assert "X-Salted-Checksum" in response.headers
    assert is_hex_sha256(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_with_data():
    """Endpoint returns seeded WAS findings and valid checksum."""
    today = date.today()
    finding_1 = WasFindings.objects.create(
        name="Example Finding 1",
        last_detected=today,
    )
    finding_2 = WasFindings.objects.create(
        name="Example Finding 2",
        last_detected=today,
    )

    now = datetime.now(timezone.utc)
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="globalAdmin",  # must match string check
        created_at=now,
        updated_at=now,
    )

    response = _auth_post(
        admin_user,
        "/dmz_sync/was_findings",
        params={"page": 1, "per_page": 100},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    ids = {item["finding_uid"] for item in body["payload"]}
    assert str(finding_1.finding_uid) in ids
    assert str(finding_2.finding_uid) in ids
    assert "X-Salted-Checksum" in response.headers
    assert is_hex_sha256(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_forbidden_non_admin():
    """Non-admin requests must be forbidden."""
    now = datetime.now(timezone.utc)
    non_admin = User.objects.create(
        first_name="Regular",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="standard",  # anything != "globalAdmin"
        created_at=now,
        updated_at=now,
    )

    response = _auth_post(
        non_admin,
        "/dmz_sync/was_findings",
        params={"page": 1, "per_page": 100},
    )

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_forbidden_no_user_type():
    """Requests with no role should be forbidden by the write-admin gate."""
    now = datetime.now(timezone.utc)
    no_type_user = User.objects.create(
        first_name="NoType",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="",  # explicitly no role
        invite_pending=False,  # ensure user is active so auth passes
        created_at=now,
        updated_at=now,
    )

    response = _auth_post(
        no_type_user,
        "/dmz_sync/was_findings",
        params={"page": 1, "per_page": 100},
    )

    assert response.status_code == 403
    body = response.json()
    assert body.get("detail") in {
        "You do not have permission to perform this action.",
        "Insufficient permissions.",
    }
