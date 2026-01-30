"""Test DMZ Sync API endpoints (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime, timedelta
import hashlib
from http.cookies import SimpleCookie
import json
import logging
import os
import secrets
import uuid

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    DataSource,
    Ip,
    IpsSubs,
    Organization,
    ShodanAssets,
    ShodanVulns,
    SubDomains,
    User,
    UserType,
)

client = TestClient(app)
LOGGER = logging.getLogger(__name__)

SALT = os.getenv("CHECKSUM_SALT", "default_salt")

CSRF_HEADER_NAME = "X-CSRF-Token"


# =============================================================================
# Cookie auth + CSRF helpers
# =============================================================================
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
    """Use production helper to set auth + csrf cookies, then load them into client."""
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
    """Echo CSRF cookie back via CSRF header."""
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


def _auth_post(
    user: User, url: str, json_body: dict, extra_headers: dict | None = None
):
    """POST with cookie auth + csrf."""
    client.cookies.clear()
    _prime_client_auth_and_csrf(user)
    headers = {"Content-Type": "application/json", **_csrf_headers()}
    if extra_headers:
        headers.update(extra_headers)
    return client.post(url, headers=headers, json=json_body)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def admin_user():
    """Create and yield a global admin user for tests."""
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield admin_user
    admin_user.delete()


@pytest.fixture
def data_source():
    """Create and yield a data source for tests."""
    data_source = DataSource.objects.create(
        name="Test Source",
        description="Test Description",
        last_run=datetime.now(),
    )
    yield data_source
    data_source.delete()


@pytest.fixture
def organization():
    """Create and yield an organization for tests."""
    organization = Organization.objects.create(
        name="Test_organization",
        acronym="DHS",
        root_domains=[],
        ip_blocks=[],
        is_passive=False,
    )
    transaction.commit()
    assert organization.name == "Test_organization"
    yield organization


# =============================================================================
# Data sources (GET)
# =============================================================================
@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_list_data_sources_success(admin_user, data_source):
    """Test the /dmz_sync/data_sources endpoint."""
    # For GET, cookie auth should still work; no CSRF expected.
    client.cookies.clear()
    _prime_client_auth_and_csrf(admin_user)

    response = client.get("/dmz_sync/data_sources")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == data_source.name
    assert data[0]["description"] == data_source.description


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_list_data_sources_unauthorized():
    """Test the /dmz_sync/data_sources endpoint unauthenticated."""
    client.cookies.clear()
    response = client.get("/dmz_sync/data_sources")

    # With CSRF middleware, GET typically doesn't require CSRF.
    # If your auth layer is cookie-based only, unauth may be 401.
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


# =============================================================================
# ASM Sync tests (POST)
# =============================================================================
@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_success(admin_user, organization):
    """Test successful ASM sync request."""
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "since_date": "2023-01-01T00:00:00",
    }

    response = _auth_post(admin_user, "/dmz_sync/asm_sync", asm_sync_payload)

    assert response.status_code == 200
    data = response.json()
    assert "ip_data" in data
    assert "loose_subs" in data

    assert "has_more_ips" in data
    assert "has_more_loose_subs" in data

    assert "next_cursor_ips" in data
    assert "next_cursor_loose_subs" in data


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_unauthorized():
    """Test ASM sync request without authentication."""
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "page": 1,
        "since_date": "2023-01-01T00:00:00",
    }

    client.cookies.clear()
    response = client.post("/dmz_sync/asm_sync", json=asm_sync_payload)

    # New CSRF behavior: no auth cookie => CSRF is NOT enforced, auth returns 401.
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_no_organization(admin_user):
    """Test ASM sync request with non-existent organization acronym."""
    asm_sync_payload = {
        "acronym": "NON_EXISTENT",
        "page_size": 25,
        "since_date": "2023-01-01T00:00:00",
    }

    response = _auth_post(admin_user, "/dmz_sync/asm_sync", asm_sync_payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_invalid_date_format(admin_user):
    """Test ASM sync request with invalid since_date format."""
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "page": 1,
        "since_date": " ",
    }

    response = _auth_post(admin_user, "/dmz_sync/asm_sync", asm_sync_payload)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request parameters."}


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_asm_sync_success(admin_user, organization, data_source):
    """Test successful ASM sync using cursor pagination."""
    ip1 = Ip.objects.create(
        id=str(uuid.uuid4()),
        ip="192.0.2.1",
        ip_hash="abc123hashvalue",
        organization=organization,
        ip_version="IPv4",
        live=True,
        false_positive=False,
        last_seen_timestamp=datetime(2023, 6, 1, 12, 0, 0),
    )
    ip2 = Ip.objects.create(
        id=str(uuid.uuid4()),
        ip="10.0.0.1",
        ip_hash="xyz456hashvalue",
        organization=organization,
        ip_version="IPv4",
        live=True,
        false_positive=False,
        last_seen_timestamp=datetime(2023, 7, 1, 12, 0, 0),
    )

    sub1 = SubDomains.objects.create(
        sub_domain="sub1.example.com",
        organization=organization,
        last_seen=datetime(2023, 6, 1, 12, 0, 0),
        data_source=data_source,
        current=True,
    )
    sub2 = SubDomains.objects.create(
        sub_domain="sub2.example.com",
        organization=organization,
        last_seen=datetime(2023, 7, 1, 12, 0, 0),
        data_source=data_source,
        current=True,
    )
    SubDomains.objects.create(
        sub_domain="sub3.example.com",
        organization=organization,
        last_seen=datetime(2023, 7, 1, 12, 0, 0),
        data_source=data_source,
        current=True,
    )

    IpsSubs.objects.create(
        ip=ip1, sub_domain=sub1, last_seen=datetime(2023, 6, 1, 12, 0, 0), current=True
    )
    IpsSubs.objects.create(
        ip=ip2, sub_domain=sub2, last_seen=datetime(2023, 7, 1, 12, 0, 0), current=True
    )

    asm_sync_request_payload = {
        "page_size": 25,
        "acronym": "DHS",
        "since_date": "2023-06-01T00:00:00",
    }

    response = _auth_post(admin_user, "/dmz_sync/asm_sync", asm_sync_request_payload)

    assert response.status_code == 200
    data = response.json()

    # ---- Cursor-based contract ----
    assert "ip_data" in data
    assert "loose_subs" in data
    assert "has_more_ips" in data
    assert "has_more_loose_subs" in data
    assert "next_cursor_ips" in data
    assert "next_cursor_loose_subs" in data

    # ---- IP validation (ascending by last_seen) ----
    ip_data = data["ip_data"]
    assert len(ip_data) == 2

    assert ip_data[0]["ip"] == "192.0.2.1"
    assert ip_data[1]["ip"] == "10.0.0.1"

    assert ip_data[0]["ip_sub_list"][0]["sub_domain"] == "sub1.example.com"
    assert ip_data[1]["ip_sub_list"][0]["sub_domain"] == "sub2.example.com"

    # ---- Loose subdomains (not linked to IPs) ----
    loose_subs = data["loose_subs"]
    assert len(loose_subs) == 1
    assert loose_subs[0]["sub_domain"] == "sub3.example.com"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_asm_sync_no_results(admin_user, organization):
    """Test ASM sync when no IPs or subdomains match the since_date filter."""
    asm_sync_request_payload = {
        "page_size": 25,
        "acronym": "DHS",
        "since_date": "2024-01-01T00:00:00",
    }

    response = _auth_post(admin_user, "/dmz_sync/asm_sync", asm_sync_request_payload)

    assert response.status_code == 200
    data = response.json()

    # ---- Cursor-based contract ----
    assert "ip_data" in data
    assert "loose_subs" in data
    assert "has_more_ips" in data
    assert "has_more_loose_subs" in data
    assert "next_cursor_ips" in data
    assert "next_cursor_loose_subs" in data

    # ---- No results ----
    assert data["ip_data"] == []
    assert data["loose_subs"] == []
    assert data["has_more_ips"] is False
    assert data["has_more_loose_subs"] is False
    assert data["next_cursor_ips"] is None
    assert data["next_cursor_loose_subs"] is None


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_asm_sync_invalid_date_format(admin_user):
    """Test ASM sync request with invalid since_date format."""
    asm_sync_request_payload = {
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
        "since_date": "invalid-date-format",
    }

    response = _auth_post(admin_user, "/dmz_sync/asm_sync", asm_sync_request_payload)

    assert response.status_code == 422
    assert "Input should be a valid datetime" in response.json()["detail"][0]["msg"]


# =============================================================================
# Shodan Sync tests (POST)
# =============================================================================
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_success():
    """Test shodan sync success with cursor-based pagination."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="SyncOrg",
        acronym="SYNC_ORG",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    data_source = DataSource.objects.create(
        name="Shodan",
        description="Shodan data source",
        last_run=datetime.now().date(),
    )

    ShodanAssets.objects.create(
        organization=organization,
        organization_name="SyncOrg",
        ip_string="8.8.8.8",
        port=443,
        protocol="https",
        timestamp=datetime.now(),
        data_source=data_source,
    )

    ShodanVulns.objects.create(
        organization=organization,
        organization_name="SyncOrg",
        ip_string="8.8.8.8",
        port="443",
        protocol="https",
        timestamp=datetime.now(),
        data_source=data_source,
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = _auth_post(user, "/dmz_sync/shodan_sync", payload)

    assert response.status_code == 200
    body = response.json()

    payload = body["payload"]

    assert "shodan_assets" in payload
    assert "shodan_vulns" in payload
    assert "next_cursor_assets" in payload
    assert "next_cursor_vulns" in payload
    assert "has_more_assets" in payload
    assert "has_more_vulns" in payload

    # ---- Data validation ----
    assert len(payload["shodan_assets"]) == 1
    assert len(payload["shodan_vulns"]) == 1

    assert payload["shodan_assets"][0]["ip_string"] == "8.8.8.8"
    assert payload["shodan_vulns"][0]["ip_string"] == "8.8.8.8"

    # ---- No pagination overflow ----
    assert payload["has_more_assets"] is False
    assert payload["has_more_vulns"] is False
    assert payload["next_cursor_assets"] is not None
    assert payload["next_cursor_vulns"] is not None


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_missing_date():
    """Test Shodan sync request missing since_date."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"acronym": "SYNC_ORG", "page": 1, "page_size": 10}

    response = _auth_post(user, "/dmz_sync/shodan_sync", payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "since_date is required."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_unauthorized_user():
    """Test Shodan sync request by unauthorized user."""
    user = User.objects.create(
        first_name="Test",
        last_name="Viewer",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = _auth_post(user, "/dmz_sync/shodan_sync", payload)

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to perform this action."
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_org_not_found():
    """Test shodan sync when organization does not exist."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "NON_EXISTENT_ORG",
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = _auth_post(user, "/dmz_sync/shodan_sync", payload)

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"


# =============================================================================
# Censys Sync tests (POST)
# =============================================================================
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_success():
    """Test Censys sync returns expected asset and vuln data."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="SyncOrg",
        acronym="SYNC_ORG",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    data_source = DataSource.objects.create(
        name="Censys",
        description="Censys data source",
        last_run=datetime.now().date(),
    )

    SubDomains.objects.create(
        organization=organization,
        sub_domain="test.syncorg.gov",
        last_seen=datetime.now(),
        current=True,
        from_root_domain="syncorg.gov",
        subdomain_source="censys",
        data_source=data_source,
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = _auth_post(user, "/dmz_sync/censys_sync", payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "censys_subdomains" in body["payload"]["data"]
    assert "X-Salted-Checksum" in response.headers


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_missing_date():
    """Test Censys sync request missing since_date."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"acronym": "SYNC_ORG", "page": 1, "page_size": 10}

    response = _auth_post(user, "/dmz_sync/censys_sync", payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "since_date is required."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_unauthorized_user():
    """Test Censys sync request by unauthorized user."""
    user = User.objects.create(
        first_name="Test",
        last_name="Viewer",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = _auth_post(user, "/dmz_sync/censys_sync", payload)

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "You do not have permission to perform this action."
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_org_not_found():
    """Test Censys sync request with non-existent organization acronym."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "NON_EXISTENT_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = _auth_post(user, "/dmz_sync/censys_sync", payload)

    assert response.status_code == 404
    assert response.json()["detail"] in {
        "Organization not found",
        "Parent organization not found",
    }


# =============================================================================
# Cred Sync tests (POST)
# =============================================================================
@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_success(admin_user, organization):
    """Test successful Credential sync request."""
    cred_sync_payload = {
        "since_date": "2023-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = _auth_post(admin_user, "/dmz_sync/cred_sync", cred_sync_payload)

    assert response.status_code == 200
    data = response.json()
    assert "total_pages" in data
    assert "credential_exposures" in data
    assert isinstance(data["credential_exposures"], list)


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_unauthorized(organization):
    """Test Credential sync request without authentication."""
    cred_sync_payload = {
        "since_date": "2023-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    client.cookies.clear()
    response = client.post("/dmz_sync/cred_sync", json=cred_sync_payload)

    # New CSRF behavior: no auth cookie => CSRF is NOT enforced, auth returns 401.
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_invalid_date_format(admin_user):
    """Test Credential sync request with invalid since_date format."""
    cred_sync_payload = {
        "since_date": "invalid-date",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = _auth_post(admin_user, "/dmz_sync/cred_sync", cred_sync_payload)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request parameters."}


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_missing_acronym(admin_user):
    """Test Credential sync request missing organization acronym."""
    cred_sync_payload = {"since_date": "2023-01-01T00:00:00"}

    response = _auth_post(admin_user, "/dmz_sync/cred_sync", cred_sync_payload)

    assert response.status_code == 422


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_no_results(admin_user):
    """Test Credential sync returns empty data when no records match since_date."""
    cred_sync_payload = {
        "since_date": "2030-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = _auth_post(admin_user, "/dmz_sync/cred_sync", cred_sync_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["total_pages"] == 1
    assert len(data["credential_exposures"]) == 0


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_checksum_header(admin_user):
    """Test that the X-Salted-Checksum header is correctly computed."""
    payload = {
        "since_date": "2024-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = _auth_post(admin_user, "/dmz_sync/cred_sync", payload)

    assert response.status_code == 200
    response_json = json.dumps(response.json(), sort_keys=True)
    expected_checksum = hashlib.sha256((SALT + response_json).encode()).hexdigest()
    assert response.headers["X-Salted-Checksum"] == expected_checksum


@pytest.fixture
def setup_test_data(organization):
    """Set up test data for credential exposures and breaches."""
    breach = CredentialBreaches.objects.create(
        breach_name="Test Breach",
        breach_date=datetime(2024, 1, 1),
        added_date=datetime(2024, 2, 1),
        description="Test breach description.",
    )

    credential_1 = CredentialExposures.objects.create(
        email="user1@example.com",
        password="hashedpassword1",  # nosec
        credential_breach=breach,
        created_at=datetime(2024, 2, 1),
        modified_date=datetime(2024, 2, 10),
        breach_name="Test Breach",
        organization=organization,
        sub_domain_string="example.com",
        root_domain="example.com",
    )

    credential_2 = CredentialExposures.objects.create(
        email="user2@example.com",
        password="hashedpassword2",  # nosec
        credential_breach=breach,
        created_at=datetime(2024, 2, 1),
        modified_date=datetime(2024, 2, 10),
        breach_name="Test Breach",
        organization=organization,
        sub_domain_string="example.com",
        root_domain="example.com",
    )

    yield breach, credential_1, credential_2


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_pagination(admin_user, setup_test_data):
    """Test Credential sync pagination and checksum header."""
    payload = {
        "since_date": "2024-01-01T00:00:00",
        "page": 1,
        "page_size": 1,
        "acronym": "DHS",
    }

    response = _auth_post(admin_user, "/dmz_sync/cred_sync", payload)

    assert response.status_code == 200
    data = response.json()

    assert data["current_page"] == 1
    assert data["total_pages"] >= 2
    assert len(data["credential_exposures"]) == 1

    response_json = json.dumps(response.json(), sort_keys=True)
    expected_checksum = hashlib.sha256((SALT + response_json).encode()).hexdigest()
    assert response.headers["X-Salted-Checksum"] == expected_checksum


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_cookie_auth_missing_csrf_header_is_forbidden(admin_user):
    """Test ASM sync request missing CSRF header is forbidden."""
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "page": 1,
        "since_date": "2023-01-01T00:00:00",
    }

    client.cookies.clear()
    _prime_client_auth_and_csrf(admin_user)

    # Intentionally omit CSRF header
    response = client.post("/dmz_sync/asm_sync", json=asm_sync_payload)

    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF validation failed"
