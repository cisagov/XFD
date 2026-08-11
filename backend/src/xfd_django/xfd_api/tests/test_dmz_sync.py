"""Test DMZ Sync API endpoints."""

# Standard Python Libraries
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
import secrets
import uuid

SALT = os.getenv("CHECKSUM_SALT", "default_salt")

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
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
#######################################################
#                ASM_sync Sync Tests
#######################################################


@pytest.fixture
def admin_user():
    """Create user fixture."""
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
    """Create data_source_fixture."""
    data_source = DataSource.objects.create(
        name="Test Source",
        description="Test Description",
        last_run=datetime.now(),
    )
    yield data_source
    data_source.delete()


@pytest.fixture
def organization():
    """Create org fixture."""
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


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_list_data_sources_success(admin_user, data_source):
    """Test listing data sources with the correct permissions."""
    response = client.get(
        "/dmz_sync/data_sources",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == data_source.name
    assert data[0]["description"] == data_source.description


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_list_data_sources_unauthorized():
    """Test listing data sources without authorization."""
    response = client.get("/dmz_sync/data_sources")

    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_success(admin_user, organization):
    """Test DMZ ASM Sync with valid parameters."""
    # Create a mock request payload (replace this with the actual data structure)
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "since_date": "2023-01-01T00:00:00",
    }

    response = client.post(
        "/dmz_sync/asm_sync",
        headers={
            "Authorization": "Bearer {}".format(create_jwt_token(admin_user)),
            "Content-Type": "application/json",
        },
        json=asm_sync_payload,
    )

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
    """Test DMZ ASM Sync without authorization."""
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "page": 1,
        "since_date": "2023-01-01T00:00:00",
    }

    response = client.post("/dmz_sync/asm_sync", json=asm_sync_payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_no_organization(admin_user):
    """Test DMZ ASM Sync with a non-existing organization."""
    asm_sync_payload = {
        "acronym": "NON_EXISTENT",
        "page_size": 25,
        "since_date": "2023-01-01T00:00:00",
    }

    response = client.post(
        "/dmz_sync/asm_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
        json=asm_sync_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_dmz_asm_sync_invalid_date_format(admin_user):
    """Test DMZ ASM Sync with an invalid date format."""
    asm_sync_payload = {
        "acronym": "DHS",
        "page_size": 25,
        "page": 1,
        "since_date": " ",
    }

    response = client.post(
        "/dmz_sync/asm_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=asm_sync_payload,
    )

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

    response = client.post(
        "/dmz_sync/asm_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
        json=asm_sync_request_payload,
    )

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

    response = client.post(
        "/dmz_sync/asm_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
        json=asm_sync_request_payload,
    )

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
    """Test ASM sync with an invalid `last_seen` date format in the request."""
    # Prepare request payload with an invalid date format
    asm_sync_request_payload = {
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
        "since_date": "invalid-date-format",  # Invalid date
    }

    # Send request to asm_sync endpoint
    response = client.post(
        "/dmz_sync/asm_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=asm_sync_request_payload,
    )
    LOGGER.info(response.json())
    # Check response
    assert response.status_code == 422  # Assuming it returns a 422 for invalid input
    assert response.json() == {"detail": "Invalid request parameters."}


#######################################################
#                Shodan Sync Tests
#######################################################
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

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

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
    """Test shodan sync missing date."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
    }

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "since_date is required."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_unauthorized_user():
    """Test shodan sync unauthorized header."""
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

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


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

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_success():
    """Test censys sync success."""
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

    response = client.post(
        "/dmz_sync/censys_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "censys_subdomains" in body["payload"]["data"]
    assert "X-Salted-Checksum" in response.headers


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_missing_date():
    """Test censys sync missing since_date."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
    }

    response = client.post(
        "/dmz_sync/censys_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "since_date is required."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_unauthorized_user():
    """Test censys sync unauthorized header."""
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

    response = client.post(
        "/dmz_sync/censys_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_censys_sync_org_not_found():
    """Test censys sync organization not found."""
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

    response = client.post(
        "/dmz_sync/censys_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Organization not found"


#######################################################
#                Cred Sync Tests
#######################################################


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_success(admin_user, organization):
    """Test successful credential synchronization."""
    cred_sync_payload = {
        "since_date": "2023-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = client.post(
        "/dmz_sync/cred_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=cred_sync_payload,
    )
    LOGGER.info(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "total_pages" in data
    assert "credential_exposures" in data
    assert isinstance(data["credential_exposures"], list)


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_unauthorized(organization):
    """Test credential synchronization without authorization."""
    cred_sync_payload = {
        "since_date": "2023-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = client.post("/dmz_sync/cred_sync", json=cred_sync_payload)
    LOGGER.info(response.json())
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_invalid_date_format(admin_user):
    """Test credential synchronization with an invalid date format."""
    cred_sync_payload = {
        "since_date": "invalid-date",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = client.post(
        "/dmz_sync/cred_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=cred_sync_payload,
    )
    LOGGER.info(response.json())
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request parameters."}


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_missing_acronym(admin_user):
    """Test credential synchronization with missing parameters."""
    cred_sync_payload = {
        "since_date": "2023-01-01T00:00:00",
    }  # Missing page and page_size

    response = client.post(
        "/dmz_sync/cred_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=cred_sync_payload,
    )
    LOGGER.info(response.json())
    assert response.status_code == 422  # Expecting validation error


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_cred_sync_no_results(admin_user):
    """Test credential synchronization when no records match the filter."""
    cred_sync_payload = {
        "since_date": "2030-01-01T00:00:00",  # Future date, no data should match
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = client.post(
        "/dmz_sync/cred_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=cred_sync_payload,
    )
    LOGGER.info(response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["total_pages"] == 1
    assert len(data["credential_exposures"]) == 0


@pytest.mark.django_db(databases=["default", "mini_data_lake"], transaction=True)
def test_checksum_header(admin_user):
    """Ensure the X-Salted-Checksum is correctly computed."""
    payload = {
        "since_date": "2024-01-01T00:00:00",
        "page": 1,
        "page_size": 25,
        "acronym": "DHS",
    }

    response = client.post(
        "/dmz_sync/cred_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=payload,
    )
    LOGGER.info(response.json())

    assert response.status_code == 200
    response_json = json.dumps(response.json(), sort_keys=True)
    expected_checksum = hashlib.sha256((SALT + response_json).encode()).hexdigest()
    assert response.headers["X-Salted-Checksum"] == expected_checksum


@pytest.fixture
def setup_test_data(organization):
    """Set up test data with a breach and two associated credential exposures."""
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
    """Ensure that requesting a page_size of 1 only returns one credential exposure."""
    payload = {
        "since_date": "2024-01-01T00:00:00",
        "page": 1,
        "page_size": 1,  # Should only return one record
        "acronym": "DHS",
    }

    response = client.post(
        "/dmz_sync/cred_sync",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
        json=payload,
    )
    LOGGER.info(response.json())
    assert response.status_code == 200

    data = response.json()

    # Validate pagination
    assert data["current_page"] == 1
    assert data["total_pages"] >= 2  # Since we have 2 records and page_size=1

    # Validate that only one credential exposure is returned
    assert len(data["credential_exposures"]) == 1

    # Ensure X-Salted-Checksum is correct
    response_json = json.dumps(response.json(), sort_keys=True)
    expected_checksum = hashlib.sha256((SALT + response_json).encode()).hexdigest()
    assert response.headers["X-Salted-Checksum"] == expected_checksum
