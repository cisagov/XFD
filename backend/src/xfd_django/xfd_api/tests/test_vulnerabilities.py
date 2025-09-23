"""Test Vulnerability API."""
# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import logging
import secrets

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.tasks.helpers.syncdb_helpers.create_db_views import (
    create_domain_materialized_view,
    create_service_mat_view,
    create_vuln_materialized_views,
    create_vuln_normal_views,
)
from xfd_django.asgi import app
from xfd_mini_dl.models import (
    DataSource,
    Domain,
    Ip,
    IpsSubs,
    Organization,
    ShodanAssets,
    ShodanVulns,
    SubDomains,
    Ticket,
    TicketEvent,
    User,
    UserType,
    Vulnerability,
    VulnScan,
)

client = TestClient(app)

LOGGER = logging.getLogger(__name__)

created_at_date = datetime.now() - timedelta(days=10)
updated_at_date = created_at_date + timedelta(days=2)

bad_id = "c0effe93-3647-475a-a0c5-0b629c348590"
search_fields = {
    "title": "DNS Twist Domains",
    "cpe": "cpe:/a:openbsd:openssh:7.4",
    "severity": "Low",
    "state": "open",
    "substate": "unconfirmed",
    "is_kev": True,
    "port": "80",
    "reverse_name": "local.crossfeed.quizzical-wing",
    "ip": "127.116.195.151",
    "organization_name": "Wizardly Agency",
    "tag": "",
    "earliest_date": created_at_date,
    "latest_date": created_at_date + timedelta(days=10),
    "created_at": created_at_date,
    "updated_at": updated_at_date,
    "os": "Linux",
    "public_id": "CVE-1234-5678",
    "scan_type": "shodan",
}


def iso_to_datetime(iso_date):
    """Convert ISO 8601 date string to datetime object."""
    return datetime.fromisoformat(iso_date.replace("Z", "+00:00"))


@pytest.fixture
def sample_domain_ip_vuln(organization):
    """Create subdomain, IP, and their association."""
    # Create required DataSource
    data_source_domain, _ = DataSource.objects.get_or_create(
        name="Test Source",
        defaults={"description": "Used in tests", "last_run": datetime.now()},
    )

    # Create the IP
    ip = Ip.objects.create(
        ip=search_fields["ip"],
        organization=organization,
        ip_hash=secrets.token_hex(8),
        from_cidr=True,
    )

    # Create the subdomain
    subdomain = SubDomains.objects.create(
        sub_domain="example.crossfeed.local",
        reverse_name="local.crossfeed.example",
        organization=organization,
        data_source=data_source_domain,
    )

    # Link IP and subdomain
    IpsSubs.objects.create(ip=ip, sub_domain=subdomain, current=True)

    # Create a Shodan entries
    ShodanAssets.objects.create(
        organization=organization,
        ip=ip,
        ip_string=ip.ip,
        port=search_fields["port"],
        protocol="http",
        timestamp=datetime.now(),
        product="Apache httpd",
        server="Apache",
        tags=["self-signed", "vpn"],
        data_source=data_source_domain,
    )

    ShodanVulns.objects.create(
        organization=organization,
        ip=ip,
        ip_string=ip.ip,
        port=search_fields["port"],
        protocol="http",
        # timestamp=datetime.now().date(),
        timestamp=datetime.now().date(),
        cve=search_fields["public_id"],
        severity=search_fields["severity"],
        cvss=8.7,
        summary="Sample vuln",
        name=search_fields["title"],
        data_source=data_source_domain,
        cpe=[search_fields["cpe"]],
    )

    return subdomain


@pytest.fixture
def user():
    """Create user fixture."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield user
    user.delete()  # Clean up after the test


@pytest.fixture
def organization():
    """Create org fixture."""
    organization = Organization.objects.create(
        name=search_fields["organization_name"],
        root_domains=["crossfeed.local"],
        ip_blocks=[],
        is_passive=False,
        enrolled_in_vs_timestamp=datetime.now(timezone.utc),  # Ensure timestamp is set
        period_start_vs_timestamp=datetime.now(timezone.utc),
    )
    transaction.commit()
    assert organization.name == search_fields["organization_name"]
    yield organization


@pytest.fixture
def shodan_vuln_setup(db):
    """Create Shodan vuln for testing."""
    organization = Organization.objects.create(
        name="Shodan Org",
        root_domains=[],
        ip_blocks=[],
        enrolled_in_vs_timestamp=datetime.now(timezone.utc),
        period_start_vs_timestamp=datetime.now(timezone.utc),
    )

    ip = Ip.objects.create(
        ip="192.0.2.5", organization=organization, ip_hash="efgh5678", from_cidr=True
    )

    datasource, _ = DataSource.objects.get_or_create(
        name="shodan",
        defaults={"description": "Used in tests", "last_run": datetime.now()},
    )

    ShodanVulns.objects.create(
        organization=organization,
        organization_name=organization.name,
        ip=ip,
        port="80",
        protocol="tcp",
        timestamp=datetime.now(timezone.utc),
        cve=search_fields["public_id"],
        severity="High",
        cvss=9.1,
        summary="SSL-related issue",
        product="nginx",
        tags=["shodan", "vpn"],
        data_source=datasource,
        # os="Linux",
        # scan_type="shodan",
    )


@pytest.fixture
def ticket_vuln_setup(db):
    """Create ticket for testing."""
    organization = Organization.objects.create(
        name="Test Org",
        root_domains=[],
        ip_blocks=[],
        enrolled_in_vs_timestamp=datetime.now(),
        period_start_vs_timestamp=datetime.now(timezone.utc),
    )

    ip = Ip.objects.create(
        ip="192.0.2.1", organization=organization, ip_hash="abcd1234", from_cidr=True
    )

    scan = VulnScan.objects.create(
        ip=ip,
        ip_string=ip.ip,
        cve_string=search_fields["public_id"],
        organization=organization,
        cvss_base_score="7.5",
        cvss_vector="AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        description="Example vulnerability",
    )

    ticket = Ticket.objects.create(
        # id="ticket1",
        ip=ip,
        ip_string=ip.ip,
        organization=organization,
        vuln_name="Example vulnerability",
        cve_string=search_fields["public_id"],
        false_positive=False,
        is_kev=True,
        is_kev_ransomware=False,
        is_open=True,
        vuln_port=80,
        port_protocol="tcp",
        service_name="httpd",
        operating_system="Linux",
        vuln_source="shodan",
        opened_timestamp=search_fields["earliest_date"],
        updated_timestamp=search_fields["latest_date"],
    )

    TicketEvent.objects.create(
        ticket=ticket,
        vuln_scan=scan,
        action="OPENED",
        event_timestamp=datetime.now(),
    )
    transaction.commit()
    return ticket


# Create the views
@pytest.fixture(autouse=True, scope="session")
def ensure_vuln_views_created(django_db_setup, django_db_blocker):
    """Ensure all necessary views for vulnerability testing are created."""
    with django_db_blocker.unblock():
        create_vuln_normal_views("mini_data_lake")


@pytest.fixture
def refresh_vuln_views(django_db_blocker):
    """Refresh the materialized vuln views after data is inserted."""
    with django_db_blocker.unblock():
        create_service_mat_view("mini_data_lake")
        create_domain_materialized_view("mini_data_lake")
        create_vuln_normal_views("mini_data_lake")
        create_vuln_materialized_views("mini_data_lake")


@pytest.fixture
def vulnerability(organization, sample_domain_ip_vuln, refresh_vuln_views):
    """Get domain from view after creating source data."""
    domain = Domain.objects.get(
        name="example.crossfeed.local", organization=organization
    )
    return Vulnerability.objects.get(title=search_fields["title"], domain=domain)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_vulnerability_by_id(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Get vulnerability by Id.
    response = client.get(
        "/vulnerabilities/{}".format(str(vulnerability.id)),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == str(vulnerability.id)
    assert data["domain"]["id"] == str(vulnerability.domain.id)
    assert data["severity"] == vulnerability.severity


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_vulnerability_by_id_fails_404(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Get error 404 if vulnerability does not exist
    response = client.get(
        "/vulnerabilities/{}".format(bad_id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 404


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_get_vulnerability_by_id(user, vulnerability, refresh_vuln_views):
    """Test v2 vulnerability by ID endpoint with default query params."""
    response = client.get(
        "/v2/vulnerabilities/{}".format(str(vulnerability.id)),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == str(vulnerability.id)
    assert data["domain"]["id"] == str(vulnerability.domain.id)
    assert data["severity"] == vulnerability.severity


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_get_vulnerability_by_id_with_history(
    user, vulnerability, refresh_vuln_views
):
    """Test v2 vulnerability by ID with ticket history query params."""
    response = client.get(
        f"/v2/vulnerabilities/{vulnerability.id}?history=true&scan_limit=5",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == str(vulnerability.id)
    # Optional: assert on ticket_history if it's available based on test data
    assert "ticket_history" in data


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_get_vulnerability_by_source_id(user, vulnerability, refresh_vuln_views):
    """Test v2 vulnerability_details endpoint with scan_source query param."""
    response = client.get(
        "/v2/vulnerability_details/{}".format(str(vulnerability.id)),
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == search_fields["title"]
    # Depending on which source you’re testing for, add more assertions


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_v2_get_vulnerability_by_id_not_found(user):
    """Test v2 vulnerability by ID returns 404 when not found."""
    bad_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(
        f"/v2/vulnerabilities/{bad_id}",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )

    assert response.status_code == 404


# @pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
# def test_update_vulnerability(user, vulnerability, refresh_vuln_views):
#     """Test vulnerability."""
#     original_vuln_id = str(vulnerability.id)
#     new_data = {
#         "id": str(vulnerability.id),
#         "created_at": str(vulnerability.created_at),
#         "updated_at": str(datetime.now()),
#         "last_seen": str(datetime.now()),
#         "title": "Updated Vulnerability",
#         "cve": vulnerability.cve,
#         "cwe": vulnerability.cwe,
#         "cpe": vulnerability.cpe,
#         "description": "Updated description.",
#         "references": None,
#         "severity": "Medium",
#         "cvss": None,
#         "needs_population": False,
#         "state": vulnerability.state,
#         "substate": vulnerability.substate,
#         "source": "source2",
#         "notes": "updated notes",
#         "actions": ["action1"],
#         "structured_data": {"key": "value"},
#         "is_kev": True,
#         "domain_id": str(vulnerability.domain.id),
#     }

#     response = client.put(
#         "/vulnerabilities/{}".format(str(vulnerability.id)),
#         json=new_data,
#         headers={"Authorization": "Bearer " + create_jwt_token(user)},
#     )

#     assert response.status_code == 200

#     vulnerability.refresh_from_db()
#     assert vulnerability.title == new_data["title"]
#     assert vulnerability.description == new_data["description"]
#     assert vulnerability.needs_population == new_data["needs_population"]
#     assert vulnerability.source == new_data["source"]
#     assert vulnerability.notes == new_data["notes"]
#     assert vulnerability.severity == new_data["severity"]
#     assert vulnerability.cvss == new_data["cvss"]
#     assert vulnerability.is_kev == new_data["is_kev"]
#     assert vulnerability.actions == new_data["actions"]

#     assert str(vulnerability.id) == original_vuln_id


# @pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
# def test_update_vulnerability_fails_404(user, vulnerability, refresh_vuln_views):
#     """Test vulnerability."""
#     new_data = {
#         "id": str(vulnerability.id),
#         "created_at": str(vulnerability.created_at),
#         "updated_at": str(datetime.now()),
#         "last_seen": str(datetime.now()),
#         "title": "Updated Vulnerability",
#         "cve": vulnerability.cve,
#         "cwe": vulnerability.cwe,
#         "cpe": vulnerability.cpe,
#         "description": "Updated description.",
#         "references": None,
#         "severity": "Medium",
#         "cvss": 7.5,
#         "needs_population": False,
#         "state": vulnerability.state,
#         "substate": vulnerability.substate,
#         "source": "source2",
#         "notes": "updated notes",
#         "actions": ["action1"],
#         "structured_data": {"key": "value"},
#         "is_kev": True,
#         "domain_id": str(vulnerability.domain.id),
#     }

#     response = client.put(
#         "/vulnerabilities/{}".format(bad_id),
#         json=new_data,
#         headers={"Authorization": "Bearer " + create_jwt_token(user)},
#     )
#     assert response.status_code == 404


# @pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
# def test_update_vulnerability_fails_422(user, vulnerability, refresh_vuln_views):
#     """Test vulnerability."""
#     new_data = {
#         "title": "Updated Vulnerability",
#         "cve": vulnerability.cve,
#         "cwe": vulnerability.cwe,
#         "cpe": vulnerability.cpe,
#         "description": "Updated description.",
#         "references": None,
#         "severity": "High",
#         "cvss": 7.5,
#         "needsPopulation": False,
#         "state": vulnerability.state,
#         "substate": vulnerability.substate,
#         "source": "source2",
#         "notes": "updated notes",
#         "actions": ["action1"],
#         "structuredData": {"key": "value"},
#         "is_kev": True,
#         "domain_id": None,
#         "service_id": None,
#     }

#     response = client.put(
#         "/vulnerabilities/{}".format(vulnerability.id),
#         json=new_data,
#         headers={"Authorization": "Bearer " + create_jwt_token(user)},
#     )
#     assert response.status_code == 422


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_id(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Search vulnerabilities by ip.
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"id": str(vulnerability.id), "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given ID"
    for vuln in data["result"]:
        assert vuln["id"] == str(
            vulnerability.id
        ), "Vulnerability ID {} does not match the expected {}".format(
            vuln["id"], vulnerability.id
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_title(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Test search vulnerabilities by title

    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"title": search_fields["title"], "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given title"
    for vuln in data["result"]:
        assert (
            vuln["title"] == search_fields["title"]
        ), "Vulnerability title {} does not match the expected {}".format(
            vuln["title"], search_fields["title"]
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_cpe(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Test search vulnerabilities by cpe
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"cpe": search_fields["cpe"], "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given CPE"

    for vuln in data["result"]:
        assert (
            vuln["cpe"] == search_fields["cpe"]
        ), "Vulnerability CPE {} does not match the expected {}".format(
            vuln["cpe"], search_fields["cpe"]
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_severity(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Test search vulnerabilities by severity
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"severity": search_fields["severity"], "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"

    assert len(data["result"]) > 0, "No result found for the given severity"

    for vuln in data["result"]:
        assert (
            vuln["severity"] == search_fields["severity"]
        ), "Vulnerability severity {} does not match the expected {}".format(
            vuln["severity"], search_fields["severity"]
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_domain_id(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Test search vulnerabilities by domain id
    domain_name = str(vulnerability.domain.name)
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"domain": domain_name, "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No vulnerabilities found for the given domain"

    for vuln in data["result"]:
        assert (
            str(vuln["domain"]["name"]) == domain_name
        ), "Vulnerability with ID {} does not have the expected domain_id {}".format(
            vuln["id"], domain_name
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_state(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    state_to_search = search_fields["state"]

    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"state": state_to_search, "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No vulnerabilities found for the given state"

    for vuln in data["result"]:
        assert (
            vuln["state"] == state_to_search
        ), "Vulnerability with ID {} does not have the expected state {}".format(
            vuln["id"], state_to_search
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_substate(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    substate_to_search = search_fields["substate"]

    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"substate": substate_to_search, "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No vulnerabilities found for the given substate"

    for vuln in data["result"]:
        assert (
            vuln["substate"] == substate_to_search
        ), "Vulnerability with ID {} does not have the expected substate {}".format(
            vuln["id"], substate_to_search
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_organization_id(
    user, vulnerability, refresh_vuln_views
):
    """Test vulnerability."""
    organization_id = str(vulnerability.domain.organization.id)

    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"organization": organization_id, "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    data = response.json()
    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given organization"

    for vulnerability_data in data["result"]:
        domain_id = vulnerability_data.get("domain_id", None)
        if domain_id:
            domain = Domain.objects.get(id=domain_id)
            assert (
                str(domain.organization.id) == organization_id
            ), "Vulnerability with ID {} does not belong to the expected organization".format(
                vulnerability_data.get("id", "N/A")
            )
        else:
            LOGGER.warning(
                "Warning: 'domain_id' key not found in vulnerability with ID %s",
                vulnerability_data.get("id", "N/A"),
            )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_is_kev(user, vulnerability, refresh_vuln_views):
    """Verify that filtering by is_kev returns the single seeded vulnerability."""
    is_kev_to_search = vulnerability.is_kev

    # Skip the test if is_kev is None (null in DB)
    if is_kev_to_search is None:
        pytest.skip("Skipping test because is_kev is null (None)")

    resp = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"is_kev": is_kev_to_search, "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )
    assert resp.status_code == 200, resp.text

    data = resp.json()

    assert data["result"], f"No results for is_kev={is_kev_to_search}"

    for v in data["result"]:
        assert (
            v["is_kev"] == is_kev_to_search
        ), f"Returned is_kev={v['is_kev']} but expected {is_kev_to_search}"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_multiple_criteria(
    user, vulnerability, refresh_vuln_views
):
    """Test vulnerability."""
    state_to_search = search_fields["state"]
    substate_to_search = search_fields["substate"]

    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {
                "state": state_to_search,
                "substate": substate_to_search,
                "false_positive": None,
            },
            "page_size": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert (
        len(data["result"]) > 0
    ), "No vulnerabilities found for the given 'state' = {} and 'substate' = {}".format(
        state_to_search, substate_to_search
    )

    for vuln in data["result"]:
        assert (
            vuln["state"] == state_to_search
        ), "Vulnerability with ID {} does not have the expected 'state' value {}".format(
            vuln["id"], state_to_search
        )
        assert (
            vuln["substate"] == substate_to_search
        ), "Vulnerability with ID {} does not have the expected 'substate' value {}".format(
            vuln["id"], substate_to_search
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_does_not_exist(user, vulnerability, refresh_vuln_views):
    """Test vulnerability."""
    # Test search vulnerabilities by state
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"title": "Does Not Exist", "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    data = response.json()

    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) == 0, "Result is not an empty array"
    assert "count" in data, "Response does not contain 'count' key"
    assert data["count"] == 0, "Count is not 0"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_earliest_and_latest_date(
    user, ticket_vuln_setup, shodan_vuln_setup, refresh_vuln_views
):
    """Test vulnerability."""
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {
                "earliest_date": search_fields["earliest_date"].isoformat(),
                "latest_date": search_fields["latest_date"].isoformat(),
                "false_positive": None,
            },
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) > 0
    for vuln in data["result"]:
        vuln_date = vuln.get("created_at")
        assert vuln_date >= search_fields["earliest_date"].isoformat()
        assert vuln_date <= search_fields["latest_date"].isoformat()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_os(user, ticket_vuln_setup, refresh_vuln_views):
    """Test vulnerability."""
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"os": search_fields["os"], "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) > 0
    for vuln in data["result"]:
        if vuln.get("os"):
            assert vuln["os"].lower() == search_fields["os"].lower()
        else:
            assert vuln["os"] is None


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_public_id(
    user, ticket_vuln_setup, shodan_vuln_setup, refresh_vuln_views
):
    """Test vulnerability."""
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {
                "public_id": search_fields["public_id"],
                "false_positive": None,
            },
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) > 0
    for vuln in data["result"]:
        assert search_fields["public_id"] in (vuln.get("cve") or "") or search_fields[
            "public_id"
        ] in (vuln.get("cwe") or "")


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_scan_type(
    user, shodan_vuln_setup, refresh_vuln_views
):
    """Test vulnerability."""
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {
                "scan_type": search_fields["scan_type"],
                "false_positive": None,
            },
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) > 0
    for vuln in data["result"]:
        scan_type = search_fields.get("scan_type", "")
        source = vuln.get("source", "")

        # Only perform lower comparison if both values are not None
        if scan_type and source:
            assert (
                scan_type.lower() in source.lower()
            ), f"Expected scan type '{scan_type}' not found in vulnerability source '{source}'"
        else:
            assert (
                False
            ), f"Scan type or source is None: scan_type={scan_type}, source={source}"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_vulnerabilities_by_port(user, shodan_vuln_setup, refresh_vuln_views):
    """Test vulnerability."""
    response = client.post(
        "/vulnerabilities/search",
        json={
            "page": 1,
            "filters": {"port": search_fields["port"], "false_positive": None},
            "pageSize": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) > 0
    for vuln in data["result"]:
        assert vuln["port"] == search_fields["port"]
