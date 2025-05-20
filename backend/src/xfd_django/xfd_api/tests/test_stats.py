"""Test Stats endpoint."""
# Standard Python Libraries
from asyncio import Semaphore
from datetime import datetime, timedelta
import secrets
import uuid

# Third-Party Libraries
from django.core.management import call_command
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from redis import asyncio as aioredis
from xfd_api.auth import create_jwt_token
from xfd_api.tasks.syncdb_helpers import (
    create_domain_view,
    create_service_view,
    create_vuln_materialized_views,
    create_vuln_normal_views,
)
from xfd_django.asgi import app
from xfd_mini_dl.models import (
    DataSource,
    Domain,
    HostSummary,
    Ip,
    IpsSubs,
    Organization,
    PortScanSummary,
    Role,
    ShodanAssets,
    ShodanVulns,
    SubDomains,
    User,
    UserType,
    Vulnerability,
    VulnScanSummary,
)

client = TestClient(app)

search_fields = {
    "title": "DNS Twist Domains",
    "cpe": "cpe:/a:openbsd:openssh:7.4",
    "severity": "Low",
    "state": "open",
    "substate": "unconfirmed",
    "is_kev": None,
    "port": "80",
    "reverse_name": "local.crossfeed.quizzical-wing",
    "ip": "127.116.195.151",
    "organization_name": "Wizardly Agency",
    "tag": "",
}


@pytest.fixture
def sample_domain_ip_vuln(organization):
    """Create subdomain, IP, and their association."""
    # Create required DataSource
    data_source_domain = DataSource.objects.create(
        name="Test Source",
        description="Used in tests",
        last_run=datetime.now().date(),
    )

    data_source_shodan = DataSource.objects.create(
        name="shodan", description="Test shodan source", last_run=datetime.now().date()
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
        timestamp=datetime.utcnow(),
        product="Apache httpd",
        server="Apache",
        tags=["self-signed", "vpn"],
        data_source=data_source_shodan,
    )

    ShodanVulns.objects.create(
        organization=organization,
        ip=ip,
        ip_string=ip.ip,
        port=search_fields["port"],
        protocol="http",
        timestamp=datetime.now().date(),
        cve="CVE-1234-5678",
        severity=search_fields["severity"],
        cvss=8.7,
        summary="Sample vuln",
        name=search_fields["title"],
        data_source=data_source_shodan,
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
    )
    transaction.commit()
    assert organization.name == search_fields["organization_name"]
    yield organization


# Create the views
@pytest.fixture(autouse=True, scope="session")
def ensure_vuln_views_created(django_db_setup, django_db_blocker):
    """Ensure all necessary views for vulnerability testing are created."""
    with django_db_blocker.unblock():
        create_domain_view("mini_data_lake")
        create_vuln_normal_views("mini_data_lake")
        create_service_view("mini_data_lake")


@pytest.fixture
def refresh_vuln_views(django_db_blocker):
    """Fixture that returns a function to refresh vuln materialized views."""

    def _refresh():
        with django_db_blocker.unblock():
            create_vuln_materialized_views("mini_data_lake")

    return _refresh


@pytest.fixture
def vulnerability(organization, sample_domain_ip_vuln, refresh_vuln_views):
    """Get domain from view after creating source data."""
    domain = Domain.objects.get(
        name="example.crossfeed.local", organization=organization
    )
    return Vulnerability.objects.get(title=search_fields["title"], domain=domain)


@pytest.fixture(scope="session")
def redis_client():
    """Ensure Redis is properly initialized before tests."""
    redis_url = "redis://redis"
    client = aioredis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=100,
        socket_timeout=5,
    )

    yield client  # Redis client available for tests

    client.flushdb()  # Clean Redis after tests
    client.close()


@pytest.fixture(scope="session", autouse=True)
def ensure_fastapi_state(redis_client):
    """Ensure FastAPI's app.state.redis is set before running any tests."""
    print("Setting up FastAPI Redis state...")
    app.state.redis = redis_client  # Inject into FastAPI state
    app.state.redis_semaphore = Semaphore(20)
    yield
    print("Cleaning up FastAPI Redis state...")
    del app.state.redis  # Cleanup after tests


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_stats_by_org_user(
    refresh_vuln_views,
    redis_client,
):
    """Test retrieving stats as an org user and ensure results are scoped."""
    # --- Org 1 Setup ---
    org1 = Organization.objects.create(
        name="Org1",
        root_domains=["org1.com"],
        ip_blocks=[],
        is_passive=False,
    )

    # Add vuln to Org 1
    data_source = DataSource.objects.create(
        name="Test Source", description="desc", last_run=datetime.now().date()
    )

    ip1 = Ip.objects.create(
        ip="1.1.1.1", organization=org1, ip_hash=secrets.token_hex(8), from_cidr=True
    )

    subdomain1 = SubDomains.objects.create(
        sub_domain="sub.org1.com",
        reverse_name="org1-rev",
        organization=org1,
        data_source=data_source,
    )

    IpsSubs.objects.create(ip=ip1, sub_domain=subdomain1, current=True)

    ShodanAssets.objects.create(
        organization=org1,
        ip=ip1,
        ip_string="1.1.1.1",
        port=80,
        protocol="http",
        timestamp=datetime.now(),
        product="Apache",
        server="Apache",
        data_source=data_source,
    )

    ShodanVulns.objects.create(
        organization=org1,
        ip=ip1,
        ip_string="1.1.1.1",
        port=80,
        protocol="http",
        timestamp=datetime.now(),
        cve="CVE-2020-1234",
        severity="Critical",
        cvss=9.5,
        summary="Exploit",
        name="Critical Vuln",
        data_source=data_source,
        cpe=["cpe:/a:apache:http_server:2.4.41"],
    )

    # --- Org 2 Setup (should be excluded) ---
    org2 = Organization.objects.create(
        name="Org2",
        root_domains=["org2.com"],
        ip_blocks=[],
        is_passive=False,
    )

    ip2 = Ip.objects.create(
        ip="2.2.2.2", organization=org2, ip_hash=secrets.token_hex(8), from_cidr=True
    )

    subdomain2 = SubDomains.objects.create(
        sub_domain="sub.org2.com",
        reverse_name="org2-rev",
        organization=org2,
        data_source=data_source,
    )

    IpsSubs.objects.create(ip=ip2, sub_domain=subdomain2, current=True)

    ShodanAssets.objects.create(
        organization=org2,
        ip=ip2,
        ip_string="2.2.2.2",
        port=443,
        protocol="https",
        timestamp=datetime.now(),
        product="nginx",
        server="nginx",
        data_source=data_source,
    )

    ShodanVulns.objects.create(
        organization=org2,
        ip=ip2,
        ip_string="2.2.2.2",
        port=443,
        protocol="https",
        timestamp=datetime.now(),
        cve="CVE-2020-5678",
        severity="Low",
        cvss=3.0,
        summary="Less bad",
        name="Low Vuln",
        data_source=data_source,
        cpe=["cpe:/a:nginx:nginx:1.18.0"],
    )

    # --- Refresh views ---
    refresh_vuln_views()

    # --- User Setup ---
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Role.objects.create(user=user, organization=org1, role="user")

    # --- Redis cache population ---
    call_command("populate_services_cache")
    call_command("populate_ports_cache")
    call_command("populate_vulns_cache")
    call_command("populate_most_common_vulns_cache")
    call_command("populate_latest_vulns_cache")
    call_command("populate_severity_count_cache")
    call_command("populate_by_orgs_cache")

    # --- Test Execution ---
    response = client.post(
        "/stats",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={"filters": {"organizations": [str(org1.id)]}},
    )

    assert response.status_code == 200
    data = response.json()
    assert "domains" in data["result"]
    vuln_ids = [x["id"] for x in data["result"]["domains"]["num_vulnerabilities"]]
    assert any("sub.org1.com|Critical" in v for v in vuln_ids)
    assert all("sub.org2.com" not in v for v in vuln_ids)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_stats_by_global_view_user(
    refresh_vuln_views,
    redis_client,
):
    """Test retrieving stats as a Global View user with filters."""
    # --- Org 1 Setup ---
    org1 = Organization.objects.create(
        name="Org1",
        root_domains=["org1.com"],
        ip_blocks=[],
        is_passive=False,
    )

    # Add vuln to Org 1
    data_source = DataSource.objects.create(
        name="Test Source", description="desc", last_run=datetime.now().date()
    )

    ip1 = Ip.objects.create(
        ip="1.1.1.1", organization=org1, ip_hash=secrets.token_hex(8), from_cidr=True
    )

    subdomain1 = SubDomains.objects.create(
        sub_domain="sub.org1.com",
        reverse_name="org1-rev",
        organization=org1,
        data_source=data_source,
    )

    IpsSubs.objects.create(ip=ip1, sub_domain=subdomain1, current=True)

    ShodanAssets.objects.create(
        organization=org1,
        ip=ip1,
        ip_string="1.1.1.1",
        port=80,
        protocol="http",
        timestamp=datetime.now(),
        product="Apache",
        server="Apache",
        data_source=data_source,
    )

    ShodanVulns.objects.create(
        organization=org1,
        ip=ip1,
        ip_string="1.1.1.1",
        port=80,
        protocol="http",
        timestamp=datetime.now(),
        cve="CVE-2020-1234",
        severity="Critical",
        cvss=9.5,
        summary="Exploit",
        name="Critical Vuln",
        data_source=data_source,
        cpe=["cpe:/a:apache:http_server:2.4.41"],
    )

    # --- Org 2 Setup (should be excluded) ---
    org2 = Organization.objects.create(
        name="Org2",
        root_domains=["org2.com"],
        ip_blocks=[],
        is_passive=False,
    )

    ip2 = Ip.objects.create(
        ip="2.2.2.2", organization=org2, ip_hash=secrets.token_hex(8), from_cidr=True
    )

    subdomain2 = SubDomains.objects.create(
        sub_domain="sub.org2.com",
        reverse_name="org2-rev",
        organization=org2,
        data_source=data_source,
    )

    IpsSubs.objects.create(ip=ip2, sub_domain=subdomain2, current=True)

    ShodanAssets.objects.create(
        organization=org2,
        ip=ip2,
        ip_string="2.2.2.2",
        port=443,
        protocol="https",
        timestamp=datetime.now(),
        product="nginx",
        server="nginx",
        data_source=data_source,
    )

    ShodanVulns.objects.create(
        organization=org2,
        ip=ip2,
        ip_string="2.2.2.2",
        port=443,
        protocol="https",
        timestamp=datetime.now(),
        cve="CVE-2020-5678",
        severity="Low",
        cvss=3.0,
        summary="Less bad",
        name="Low Vuln",
        data_source=data_source,
        cpe=["cpe:/a:nginx:nginx:1.18.0"],
    )

    # --- Refresh views ---
    refresh_vuln_views()

    # Just re-run the same setup here or refactor into a shared fixture

    # -- User setup --
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Populate Redis
    call_command("populate_services_cache")
    call_command("populate_ports_cache")
    call_command("populate_vulns_cache")
    call_command("populate_most_common_vulns_cache")
    call_command("populate_latest_vulns_cache")
    call_command("populate_severity_count_cache")
    call_command("populate_by_orgs_cache")

    response = client.post(
        "/stats",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={"filters": {"organizations": [str(org2.id)]}},
    )

    assert response.status_code == 200
    data = response.json()
    assert "domains" in data["result"]
    vuln_ids = [x["id"] for x in data["result"]["domains"]["num_vulnerabilities"]]
    assert any("sub.org2.com|Low" in v for v in vuln_ids)
    assert all("sub.org1.com" not in v for v in vuln_ids)


#####################################################################
#                 --------VS Summary Tests--------
#####################################################################


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_trends_success():
    """Test /stats/trends endpoint returns valid data."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-east"
    )

    user = User.objects.create(
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-east",
    )

    now = datetime.utcnow()
    HostSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        host_done_count=10,
        host_waiting_count=2,
        host_running_count=1,
        host_ready_count=7,
        up_host_count=8,
        down_host_count=3,
        scanned_asset_count=11,
    )

    PortScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        open_port_count=20,
        risky_port_count=5,
        nmi_service_count=2,
        unique_ip_count=10,
        unique_service_count=8,
    )

    VulnScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        assets_owned_count=100,
        false_positive_count=5,
        vulnerable_host_count=50,
        unique_service_count=12,
        unique_none_severity_count=1,
        unique_low_severity_count=2,
        unique_medium_severity_count=3,
        unique_high_severity_count=4,
        unique_critical_severity_count=5,
        risky_services_count=3,
        unsupported_software_count=7,
        unique_os_count=4,
        none_severity_count=10,
        low_severity_count=20,
        medium_severity_count=15,
        high_severity_count=25,
        critical_severity_count=5,
        critical_max_age=90,
        high_max_age=60,
        none_kev_count=1,
        low_kev_count=1,
        medium_kev_count=1,
        high_kev_count=1,
        critical_kev_count=1,
        kev_max_age=100,
        one_to_five_vulns_count=10,
        six_to_nine_vulns_count=5,
        ten_plus_vulns_count=3,
        top_5_occurring_cves=[],
        top_5_occurring_kevs=[],
        included_tickets=[],
        top_5_risky_hosts={},
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (now - timedelta(days=7)).date().isoformat(),
            "end_date": now.date().isoformat(),
            "sources": ["vs", "host", "port", "port_service"],
            "enhanced_data": True,
        }
    }

    response = client.post(
        "/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert "host_summaries" in data
    assert "port_scan_summaries" in data
    assert "vuln_scan_summaries" in data
    assert data["host_summaries"][0]["host_done_count"] == 10


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_condensed_trends_success():
    """Test /stats/condensed_trends endpoint returns valid flattened data."""
    org = Organization.objects.create(
        id=uuid.uuid4(), name="Test Org", region_id="us-west"
    )

    user = User.objects.create(
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-west",
    )

    now = datetime.utcnow()

    HostSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        host_done_count=12,
        host_waiting_count=3,
        host_running_count=0,
        host_ready_count=9,
        up_host_count=10,
        down_host_count=2,
        scanned_asset_count=12,
    )

    PortScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        open_port_count=30,
        risky_port_count=7,
        nmi_service_count=3,
        unique_ip_count=15,
        unique_service_count=10,
    )

    VulnScanSummary.objects.create(
        summary_date=now.date(),
        start_date=now - timedelta(days=7),
        end_date=now,
        organization=org,
        assets_owned_count=200,
        false_positive_count=0,
        vulnerable_host_count=100,
        unique_service_count=5,
        unique_none_severity_count=0,
        unique_low_severity_count=0,
        unique_medium_severity_count=0,
        unique_high_severity_count=0,
        unique_critical_severity_count=0,
        risky_services_count=0,
        unsupported_software_count=0,
        unique_os_count=0,
        none_severity_count=0,
        low_severity_count=0,
        medium_severity_count=0,
        high_severity_count=0,
        critical_severity_count=0,
        critical_max_age=0,
        high_max_age=0,
        none_kev_count=0,
        low_kev_count=0,
        medium_kev_count=0,
        high_kev_count=0,
        critical_kev_count=0,
        kev_max_age=0,
        one_to_five_vulns_count=0,
        six_to_nine_vulns_count=0,
        ten_plus_vulns_count=0,
    )

    payload = {
        "filters": {
            "organization_id": str(org.id),
            "start_date": (now - timedelta(days=7)).date().isoformat(),
            "end_date": now.date().isoformat(),
            "sources": ["vs", "host", "port_service", "port"],
            "enhanced_data": False,
        }
    }

    response = client.post(
        "/stats/condensed_trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert any("host_summary_host_done_count" in k for k in data.keys())
    assert data["host_summary_host_done_count"][0] == 12


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_trends_unauthorized(organization):
    """Test the /stats/trends endpoint without auth."""
    payload = {
        "filters": {
            "organization_id": str(organization.id),
            "start_date": (datetime.today() - timedelta(days=30)).isoformat(),
            "end_date": datetime.today().isoformat(),
            "enhanced_data": False,
        }
    }

    response = client.post("/stats/trends", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vs_trends_invalid_org():
    """Test the /stats/trends endpoint with invalid org ID."""
    user = User.objects.create(
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        first_name="Test",
        last_name="User",
        region_id="us-west",
    )

    payload = {
        "filters": {
            "organization_id": "Invalid-uuid",
            "start_date": (datetime.today() - timedelta(days=30)).date().isoformat(),
            "end_date": datetime.today().date().isoformat(),
            "enhanced_data": False,
        }
    }

    response = client.post(
        "/stats/trends",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )
    print(response)
    assert response.status_code == 404
    assert response.json()["detail"] == "Invalid organization ID."
