"""Test domain API."""
# Standard Python Libraries
from datetime import datetime
import logging
import secrets

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.tasks.helpers.syncdb_helpers.create_db_views import (
    create_domain_materialized_view,
    create_domain_search_mat_view,
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
    Service,
    ShodanAssets,
    ShodanVulns,
    SubDomains,
    User,
    UserType,
)

client = TestClient(app)

LOGGER = logging.getLogger(__name__)

bad_id = "960b7db7-f3af-411d-a247-33371"
search_fields = {
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
        severity="High",
        cvss=8.7,
        summary="Sample vuln",
        name="Example Vuln",
        data_source=data_source_shodan,
        cpe=["cpe:/a:example:software:1.0"],
    )

    return subdomain


@pytest.fixture
def domain(sample_domain_ip_vuln, refresh_vuln_views):
    """Get domain from view after creating source data."""
    refresh_vuln_views()
    return Domain.objects.get(name="example.crossfeed.local")


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
        create_vuln_normal_views("mini_data_lake")


@pytest.fixture
def refresh_vuln_views(django_db_blocker):
    """Fixture that returns a function to refresh vuln materialized views."""

    def _refresh():
        with django_db_blocker.unblock():
            create_service_mat_view("mini_data_lake")
            create_domain_materialized_view("mini_data_lake")
            create_vuln_normal_views("mini_data_lake")
            create_vuln_materialized_views("mini_data_lake")
            create_domain_search_mat_view("mini_data_lake")

    return _refresh


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_domain_by_id(user, domain, refresh_vuln_views):
    """Test domain by id."""
    # Get domain by Id.
    response = client.get(
        "/domain/{}".format(domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None, "Response is empty"
    assert data["id"] == str(domain.id)
    assert data["ip"] == domain.ip


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_domain_by_id_fails_404(user, domain, refresh_vuln_views):
    """Test domain by id to fail."""
    # Get domain by Id.
    response = client.get(
        "/domain/{}".format(bad_id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 404


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domain_by_ip(user, domain, refresh_vuln_views):
    """Test domain by ip."""
    # Search for the domain by IP
    response = client.post(
        "/domain/search",
        json={"page": 1, "filters": {"ip": search_fields["ip"]}, "page_size": 25},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given IP"

    # Validate result contain the correct IP
    for result in data["result"]:
        assert result["ip"] == search_fields["ip"], "Expected IP {}, but got {}".format(
            search_fields["ip"], result["ip"]
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domain_by_organization(user, domain, refresh_vuln_views):
    """Test domain by org."""
    # Test search domains by organization
    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {"organization": str(domain.organization.id)},
            "page_size": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given organization"

    for result in data["result"]:
        assert result["organization"]["name"] == str(domain.organization.name)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domain_by_organization_name(user, domain, refresh_vuln_views):
    """Test domain by org name."""
    LOGGER.info(
        "Domain in view: %s", Domain.objects.values("id", "organization_id", "name")
    )
    LOGGER.info("Org in DB: %s", Organization.objects.all().values("id", "name"))
    # Test search domains by organization
    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {"organization_name": search_fields["organization_name"]},
            "page_size": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given organization name"

    for result in data["result"]:
        assert (
            result["organization"] is not None
        ), "Response domain did not include an Organization ID"
        organization = Organization.objects.get(id=result["organization"]["id"])
        assert (
            organization.name == search_fields["organization_name"]
        ), "Domain with ID {} did not contain Organization Id {}".format(
            result["id"], search_fields["organization_name"]
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_multiple_criteria(user, domain, refresh_vuln_views):
    """Test domain by multi-criteria."""
    # Test search domains by multiple criteria
    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {
                "ip": search_fields["ip"],
                "organization_name": search_fields["organization_name"],
            },
            "page_size": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given ip and port"

    for result in data["result"]:
        assert (
            result["ip"] == search_fields["ip"]
        ), "Domain with ID {} does not have an IP {}".format(
            result["id"], search_fields["ip"]
        )
        domain_id = result.get("id", None)

        assert domain_id is not None, "Domain Id not found in Response"
        services = Service.objects.filter(domain=domain_id)
        for service in services:
            assert (
                str(service.port) == search_fields["port"]
            ), "Domain with ID {} does not have a service with port {}".format(
                domain_id, domain.services.first().port
            )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_does_not_exist(user, domain, refresh_vuln_views):
    """Test domain by domain not existing."""
    # Test search domains if record does not exist
    response = client.post(
        "/domain/search",
        json={"page": 1, "filters": {"ip": "Does not exist"}, "page_size": 25},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) == 0, "No result found for the given organization name"
