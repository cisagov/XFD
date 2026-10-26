"""Test domain API."""
# Standard Python Libraries
from datetime import datetime
import logging
import secrets
from unittest.mock import patch

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from xfd_api.api_methods.domain import apply_domain_access_filter
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
    Role,
    Service,
    ShodanAssets,
    ShodanVulns,
    SubDomains,
    User,
    UserType,
)

client = TestClient(app)

LOGGER = logging.getLogger(__name__)

nonexistent_domain_id = "00000000-0000-0000-0000-000000000000"
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
def foreign_domain(foreign_organization, refresh_vuln_views):
    """Create a domain belonging to an organization the user cannot access."""
    data_source = DataSource.objects.create(
        name="Foreign Test Source",
        description="Used for cross-organization access tests",
        last_run=datetime.now().date(),
    )
    SubDomains.objects.create(
        sub_domain="foreign.crossfeed.local",
        reverse_name="local.crossfeed.foreign",
        organization=foreign_organization,
        data_source=data_source,
    )
    refresh_vuln_views()
    return Domain.objects.get(name="foreign.crossfeed.local")


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


@pytest.fixture
def foreign_organization():
    """Create a second organization for access-control tests."""
    organization = Organization.objects.create(
        name="Foreign Test Organization",
        root_domains=["foreign.crossfeed.local"],
        ip_blocks=[],
        is_passive=False,
    )
    transaction.commit()
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
def test_standard_user_can_get_domain_from_member_organization(user, domain):
    """Standard users can retrieve domains from their organization memberships."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])
    Role.objects.create(user=user, organization=domain.organization, role="user")

    response = client.get(
        "/domain/{}".format(domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(domain.id)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_cannot_get_domain_from_other_organization(
    user, domain, foreign_domain
):
    """Standard users cannot retrieve domains outside their memberships."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])
    Role.objects.create(user=user, organization=domain.organization, role="user")

    response = client.get(
        "/domain/{}".format(foreign_domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "You do not have access to this domain."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_user_without_memberships_cannot_get_domain(user, domain):
    """Users without organization memberships cannot retrieve domains."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])

    response = client.get(
        "/domain/{}".format(domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_regional_admin_is_limited_to_their_region(user, domain):
    """Regional administrators can only retrieve domains in their region."""
    domain.organization.region_id = "7"
    domain.organization.save(update_fields=["region_id"])
    user.user_type = UserType.REGIONAL_ADMIN
    user.region_id = "7"
    user.save(update_fields=["user_type", "region_id"])

    response = client.get(
        "/domain/{}".format(domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200

    domain.organization.region_id = "8"
    domain.organization.save(update_fields=["region_id"])

    response = client.get(
        "/domain/{}".format(domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_regional_admin_without_region_cannot_get_domain(user, domain):
    """Regional administrators without a region cannot retrieve domains."""
    user.user_type = UserType.REGIONAL_ADMIN
    user.region_id = None
    user.save(update_fields=["user_type", "region_id"])

    response = client.get(
        "/domain/{}".format(domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_global_view_user_can_get_any_domain(user, foreign_domain):
    """Global view users can retrieve domains from any organization."""
    user.user_type = UserType.GLOBAL_VIEW
    user.save(update_fields=["user_type"])

    response = client.get(
        "/domain/{}".format(foreign_domain.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(foreign_domain.id)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_domain_by_id_fails_404(user, domain, refresh_vuln_views):
    """Test domain by id to fail."""
    # Get domain by Id.
    response = client.get(
        "/domain/{}".format(nonexistent_domain_id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 404


def test_get_domain_by_id_unauthenticated():
    """Unauthenticated users cannot retrieve a domain."""
    response = client.get("/domain/{}".format(nonexistent_domain_id))

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_standard_user_sees_member_organizations(
    user, domain, foreign_domain
):
    """Standard users only see domains from their organization memberships."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])
    Role.objects.create(user=user, organization=domain.organization, role="user")

    response = client.post(
        "/domain/search",
        json={"page": 1, "page_size": 25},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert [result["id"] for result in response.json()["result"]] == [str(domain.id)]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_standard_user_cannot_filter_foreign_organization(
    user, domain, foreign_domain
):
    """Standard users cannot bypass access with a foreign organization filter."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])
    Role.objects.create(user=user, organization=domain.organization, role="user")

    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {"organization": str(foreign_domain.organization.id)},
            "page_size": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json()["result"] == []


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_regional_admin_sees_only_their_region(
    user, domain, foreign_domain
):
    """Regional administrators only see domains in their region."""
    domain.organization.region_id = "7"
    domain.organization.save(update_fields=["region_id"])
    foreign_domain.organization.region_id = "8"
    foreign_domain.organization.save(update_fields=["region_id"])
    user.user_type = UserType.REGIONAL_ADMIN
    user.region_id = "7"
    user.save(update_fields=["user_type", "region_id"])

    response = client.post(
        "/domain/search",
        json={"page": 1, "page_size": 25},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert [result["id"] for result in response.json()["result"]] == [str(domain.id)]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_regional_admin_cannot_see_other_region(
    user, domain, foreign_domain
):
    """Regional administrators cannot see domains outside their region."""
    domain.organization.region_id = "7"
    domain.organization.save(update_fields=["region_id"])
    foreign_domain.organization.region_id = "8"
    foreign_domain.organization.save(update_fields=["region_id"])
    user.user_type = UserType.REGIONAL_ADMIN
    user.region_id = "7"
    user.save(update_fields=["user_type", "region_id"])

    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {"organization": str(foreign_domain.organization.id)},
            "page_size": 25,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json()["result"] == []


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_global_view_user_sees_any_organization(
    user, domain, foreign_domain
):
    """Global-view users can see domains from every organization."""
    user.user_type = UserType.GLOBAL_VIEW
    user.save(update_fields=["user_type"])

    response = client.post(
        "/domain/search",
        json={"page": 1, "page_size": 25},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert {result["id"] for result in response.json()["result"]} == {
        str(domain.id),
        str(foreign_domain.id),
    }


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domains_user_without_memberships_sees_no_domains(user, domain):
    """Users without organization memberships see no domains."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])

    response = client.post(
        "/domain/search",
        json={"page": 1, "page_size": 25},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json()["result"] == []


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_apply_domain_access_filter_global_users_bypass(user, domain, foreign_domain):
    """Global admin and global-view users can access every domain."""
    queryset = Domain.objects.all()

    for user_type in (UserType.GLOBAL_ADMIN, UserType.GLOBAL_VIEW):
        user.user_type = user_type
        user.save(update_fields=["user_type"])
        assert set(
            apply_domain_access_filter(queryset, user).values_list("id", flat=True)
        ) == {domain.id, foreign_domain.id}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_apply_domain_access_filter_standard_memberships(user, domain, foreign_domain):
    """Standard users are filtered to their organization memberships."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])
    Role.objects.create(user=user, organization=domain.organization, role="user")

    assert list(
        apply_domain_access_filter(Domain.objects.all(), user).values_list(
            "id", flat=True
        )
    ) == [domain.id]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_apply_domain_access_filter_empty_memberships(user, domain):
    """Standard users without memberships receive an empty queryset."""
    user.user_type = UserType.STANDARD
    user.save(update_fields=["user_type"])

    assert not apply_domain_access_filter(Domain.objects.all(), user).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_apply_domain_access_filter_regional_membership(user, domain, foreign_domain):
    """Regional administrators are filtered to organizations in their region."""
    domain.organization.region_id = "7"
    domain.organization.save(update_fields=["region_id"])
    foreign_domain.organization.region_id = "8"
    foreign_domain.organization.save(update_fields=["region_id"])
    user.user_type = UserType.REGIONAL_ADMIN
    user.region_id = "7"
    user.save(update_fields=["user_type", "region_id"])

    assert list(
        apply_domain_access_filter(Domain.objects.all(), user).values_list(
            "id", flat=True
        )
    ) == [domain.id]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_apply_domain_access_filter_missing_regional_assignment(user, domain):
    """Regional administrators without a region receive an empty queryset."""
    user.user_type = UserType.REGIONAL_ADMIN
    user.region_id = None
    user.save(update_fields=["user_type", "region_id"])

    assert not apply_domain_access_filter(Domain.objects.all(), user).exists()


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


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_domains")
def test_domains_search_autofill_endpoint_auth_user_200(mock_search):
    """Test domain search autocomplete endpoint."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    response = client.post(
        "/search/domains",
        json={
            "search_term": "127",
            "search_field": "name",
            "regions": [],
            "organizations": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_domains")
def test_domains_search_autofill_endpoint_regional_auth(mock_search):
    """Test domain search autocomplete endpoint."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="8",
    )
    response = client.post(
        "/search/domains",
        json={
            "search_term": "127",
            "search_field": "name",
            "regions": ["3"],
            "organizations": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_domains")
def test_domains_search_autofill_endpoint_global_auth(mock_search):
    """Test domain search autocomplete endpoint."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="8",
    )
    response = client.post(
        "/search/domains",
        json={
            "search_term": "127",
            "search_field": "name",
            "regions": ["3"],
            "organizations": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
