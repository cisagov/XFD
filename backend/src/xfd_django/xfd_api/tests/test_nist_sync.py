"""Tests for the NIST CVE sync API endpoint (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime, timezone
from http.cookies import SimpleCookie
import re
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import Cve as CveModel
from xfd_mini_dl.models import User, UserType

client = TestClient(app)

SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
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
        cookie_obj: SimpleCookie = SimpleCookie()
        cookie_obj.load(set_cookie)
        for name, morsel in cookie_obj.items():
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
def test_get_call_all_cves_empty_db():
    """Test the /cves endpoint with an empty database."""
    client.cookies.clear()

    now = datetime.now(timezone.utc)
    user = User.objects.create(
        first_name="T",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=now,
        updated_at=now,
    )

    _prime_client_auth_and_csrf(user)

    response = client.post("/dmz_sync/cves", headers=_csrf_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert body["payload"] == []

    assert "X-Salted-Checksum" in response.headers
    assert SHA256_HEX_RE.fullmatch(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_cves_with_data():
    """Test the /cves endpoint with existing CVE data."""
    client.cookies.clear()

    now = datetime.now(timezone.utc)
    cve1 = CveModel.objects.create(
        id=uuid.uuid4(),
        name="CVE-2025-0001",
        published_at=now,
        modified_at=now,
        status="PUBLISHED",
    )
    cve2 = CveModel.objects.create(
        id=uuid.uuid4(),
        name="CVE-2025-0002",
        published_at=now,
        modified_at=now,
        status="PUBLISHED",
    )

    user_now = datetime.now(timezone.utc)
    user = User.objects.create(
        first_name="T",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=user_now,
        updated_at=user_now,
    )

    _prime_client_auth_and_csrf(user)

    response = client.post("/dmz_sync/cves", headers=_csrf_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"

    ids = {item["id"] for item in body["payload"]}
    assert ids == {str(cve1.id), str(cve2.id)}
    for item in body["payload"]:
        assert item["status"] == "PUBLISHED"

    assert "X-Salted-Checksum" in response.headers
    assert SHA256_HEX_RE.fullmatch(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_cves_unauthorized():
    """Test the /cves endpoint without authorization."""
    client.cookies.clear()

    response = client.post("/dmz_sync/cves")

    # Keep original expectation: no credentials -> 401
    assert response.status_code == 401
    assert "detail" in response.json()
