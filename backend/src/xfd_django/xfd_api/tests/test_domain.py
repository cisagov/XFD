"""Test domain API (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
from http.cookies import SimpleCookie
import logging
import secrets

# Third-Party Libraries
from django.db import transaction
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
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
    """Prime TestClient with auth + csrf cookies using production helper."""
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


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def sample_domain_ip_vuln(organization):
    """Create subdomain, IP, and their association."""
    data_source_domain = DataSource.objects.create(
        name="Test Source",
        description="Used in tests",
        last_run=datetime.now().date(),
    )

    data_source_shodan = DataSource.objects.create(
        name="shodan", description="Test shodan source", last_run=datetime.now().date()
    )

    ip = Ip.objects.create(
        ip=search_fields["ip"],
        organization=organization,
        ip_hash=secrets.token_hex(8),
        from_cidr=True,
    )

    subdomain = SubDomains.objects.create(
        sub_domain="example.crossfeed.local",
        reverse_name="local.crossfeed.example",
        organization=organization,
        data_source=data_source_domain,
    )

    IpsSubs.objects.create(ip=ip, sub_domain=subdomain, current=True)

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
    u = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield u
    u.delete()


@pytest.fixture
def organization():
    """Create org fixture."""
    org = Organization.objects.create(
        name=search_fields["organization_name"],
        root_domains=["crossfeed.local"],
        ip_blocks=[],
        is_passive=False,
    )
    transaction.commit()
    assert org.name == search_fields["organization_name"]
    yield org


@pytest.fixture(autouse=True)
def _auth(user):
    """Clear TestClient cookies before and after each test."""
    client.cookies.clear()
    _prime_client_auth_and_csrf(user)
    yield
    client.cookies.clear()


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


# =============================================================================
# Tests
# =============================================================================
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_domain_by_id(user, domain, refresh_vuln_views):
    """Test domain by id."""
    response = client.get(f"/domain/{domain.id}", headers=_csrf_headers())

    assert response.status_code == 200
    data = response.json()
    assert data is not None, "Response is empty"
    assert data["id"] == str(domain.id)
    assert data["ip"] == domain.ip


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_domain_by_id_fails_404(user, domain, refresh_vuln_views):
    """Test domain by id to fail."""
    response = client.get(f"/domain/{bad_id}", headers=_csrf_headers())
    assert response.status_code == 404


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domain_by_ip(user, domain, refresh_vuln_views):
    """Test domain by ip."""
    response = client.post(
        "/domain/search",
        json={"page": 1, "filters": {"ip": search_fields["ip"]}, "page_size": 25},
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data is not None, "Response is empty"
    assert "result" in data, "Response does not contain 'result' key"
    assert len(data["result"]) > 0, "No result found for the given IP"

    for result in data["result"]:
        assert result["ip"] == search_fields["ip"], "Expected IP {}, but got {}".format(
            search_fields["ip"], result["ip"]
        )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_domain_by_organization(user, domain, refresh_vuln_views):
    """Test domain by org."""
    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {"organization": str(domain.organization.id)},
            "page_size": 25,
        },
        headers=_csrf_headers(),
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

    response = client.post(
        "/domain/search",
        json={
            "page": 1,
            "filters": {"organization_name": search_fields["organization_name"]},
            "page_size": 25,
        },
        headers=_csrf_headers(),
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
        headers=_csrf_headers(),
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
    response = client.post(
        "/domain/search",
        json={"page": 1, "filters": {"ip": "Does not exist"}, "page_size": 25},
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["result"]) == 0, "No result found for the given organization name"
