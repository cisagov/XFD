"""Test organizations (cookie auth + CSRF aware)."""

# Standard Python Libraries
from datetime import datetime
from http.cookies import SimpleCookie
import logging
import secrets
from unittest.mock import patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import Organization, Role, Scan, ScanTask, User, UserType

client = TestClient(app)
LOGGER = logging.getLogger(__name__)

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_CANDIDATES = ("csrf", "xsrf", "csrf-token", "xsrf-token", "csrf_token")


# -----------------------------------------------------------------------------
# Helpers: prime cookie auth + CSRF for unsafe methods
# -----------------------------------------------------------------------------
def _apply_set_cookie_headers_to_client(resp: StarletteResponse) -> None:
    """Copy Set-Cookie headers from a Starlette response into the TestClient cookie jar."""
    set_cookie_headers = resp.headers.getlist("set-cookie")
    if not set_cookie_headers:
        raise AssertionError(
            "No Set-Cookie headers were set by set_auth_and_csrf_cookies()."
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
        "headers": [(b"host", b"testserver"), (b"x-forwarded-proto", b"http")],
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
        if any(tok in lk for tok in CSRF_COOKIE_CANDIDATES):
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


@pytest.fixture(autouse=True)
def _clear_client_cookies_between_tests():
    client.cookies.clear()
    yield
    client.cookies.clear()


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_org_by_global_admin():
    """Test organization by global admin should succeed."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)

    response = client.post(
        "/organizations/",
        json={
            "ip_blocks": [],
            "acronym": acronym,
            "name": name,
            "root_domains": ["cisa.gov"],
            "is_passive": False,
            "tags": [{"name": "test"}],
        },
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["created_by"]["id"] == str(user.id)
    assert data["name"] == name
    assert data["tags"][0]["name"] == "test"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_duplicate_org_fails():
    """Cannot add organization with the same acronym."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)

    client.post(
        "/organizations/",
        json={
            "ip_blocks": [],
            "acronym": acronym,
            "name": name,
            "root_domains": ["cisa.gov"],
            "is_passive": False,
            "tags": [],
        },
        headers=_csrf_headers(),
    )

    response = client.post(
        "/organizations/",
        json={
            "ip_blocks": [],
            "acronym": acronym,
            "name": name,
            "root_domains": ["cisa.gov"],
            "is_passive": False,
            "tags": [],
        },
        headers=_csrf_headers(),
    )

    assert response.status_code == 500


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_org_by_global_view_fails():
    """Creating an organization by global view user should fail."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)

    response = client.post(
        "/organizations/",
        json={
            "ip_blocks": [],
            "acronym": acronym,
            "name": name,
            "root_domains": ["cisa.gov"],
            "is_passive": False,
        },
        headers=_csrf_headers(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_org_by_global_admin():
    """Update organization by global admin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        acronym=secrets.token_hex(2),
        name=f"test-{secrets.token_hex(4)}",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    new_name = f"test-{secrets.token_hex(4)}"
    new_acronym = secrets.token_hex(2)
    new_root_domains = ["newdomain.com"]
    new_ip_blocks = ["1.1.1.1"]
    is_passive = True
    tags = [{"name": "updated"}]

    response = client.post(
        f"/update_organization/{organization.id}",
        json={
            "name": new_name,
            "acronym": new_acronym,
            "root_domains": new_root_domains,
            "ip_blocks": new_ip_blocks,
            "is_passive": is_passive,
            "tags": tags,
        },
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["root_domains"] == new_root_domains
    assert data["ip_blocks"] == new_ip_blocks
    assert data["is_passive"] == is_passive
    assert data["tags"][0]["name"] == tags[0]["name"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_org_by_global_view_fails():
    """Update organization by global view should fail."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        acronym=secrets.token_hex(2),
        name=f"test-{secrets.token_hex(4)}",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        f"/update_organization/{organization.id}",
        json={
            "name": f"test-{secrets.token_hex(4)}",
            "acronym": secrets.token_hex(2),
            "root_domains": ["newdomain.com"],
            "ip_blocks": ["1.1.1.1"],
            "is_passive": True,
            "tags": [{"name": "updated"}],
        },
        headers=_csrf_headers(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_org_by_global_admin():
    """Deleting an organization by global admin should succeed."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.delete(
        f"/organizations/{organization.id}",
        headers=_csrf_headers(),
    )

    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_org_by_org_admin_fails():
    """Deleting an organization by org admin should fail."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Role.objects.create(user=user, organization=organization, role="admin")

    response = client.delete(
        f"/organizations/{organization.id}",
        headers=_csrf_headers(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_org_by_global_view_fails():
    """Deleting an organization by global view should fail."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        acronym=secrets.token_hex(2),
        name=f"test-{secrets.token_hex(4)}",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.delete(
        f"/organizations/{organization.id}",
        headers=_csrf_headers(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# --- Everything below: only change is that POST/DELETE now includes cookie+CSRF.
#     GET endpoints can remain bearer-only, but we can also keep them cookie-auth.
#     For consistency, I’m priming cookies for tests that pass auth.
#     (It avoids edge cases where csrf_protect treats you as cookie-auth first.)
# -----------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_orgs_by_global_view_succeeds():
    """Global view user should get all organizations."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get("/organizations")
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_orgs_by_org_member_only_gets_their_org():
    """Standard user should get only their organization."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization1 = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Role.objects.create(user=user, organization=organization1, role="user")

    response = client.get("/organizations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(organization1.id)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_org_by_org_admin_succeeds():
    """Organization admin should get their organization."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Role.objects.create(user=user, organization=organization, role="admin")

    response = client.get(f"/organizations/{organization.id}")
    assert response.status_code == 200
    assert response.json()["name"] == organization.name


# --- Granular scan endpoints (POST -> needs CSRF) ----------------------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_enable_user_modifiable_scan_by_org_admin_succeeds():
    """Enable user-modifiable scan by org admin should succeed."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Role.objects.create(user=user, organization=organization, role="admin")

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        is_granular=True,
        is_user_modifiable=True,
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["granular_scans"]) == 1
    assert data["granular_scans"][0]["id"] == str(scan.id)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_disable_user_modifiable_scan_by_org_admin_succeeds():
    """Disable user-modifiable scan by org admin should succeed."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Role.objects.create(user=user, organization=organization, role="admin")

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        is_granular=True,
        is_user_modifiable=True,
    )

    scan_task = ScanTask.objects.create(scan=scan, status="created", type="fargate")
    scan_task.organizations.add(organization)

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": False},
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    assert len(response.json()["granular_scans"]) == 0


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_enable_user_modifiable_scan_by_global_admin_succeeds():
    """Enable user-modifiable scan by global admin should succeed."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        is_granular=True,
        is_user_modifiable=True,
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    assert len(response.json()["granular_scans"]) == 1


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_enable_non_user_modifiable_scan_by_org_admin_fails():
    """Enable non-user-modifiable scan by org admin should fail."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Role.objects.create(user=user, organization=organization, role="admin")

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        is_granular=True,
        is_user_modifiable=False,
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers=_csrf_headers(),
    )

    assert response.status_code == 404


# --- Role approve/remove endpoints (POST -> needs CSRF) ----------------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_approve_role_by_global_admin_succeeds():
    """Approve role by global admin should succeed."""
    admin = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(admin)

    user2 = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    role = Role.objects.create(
        role="user", approved=False, organization=organization, user=user2
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/approve",
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    role.refresh_from_db()
    assert role.approved is True


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_approve_role_by_org_admin_succeeds():
    """Approve role by org admin should succeed."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    user2 = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Role.objects.create(user=user, organization=organization, role="admin")

    role = Role.objects.create(
        role="user", approved=False, organization=organization, user=user2
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/approve",
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    role.refresh_from_db()
    assert role.approved is True


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_remove_role_by_global_admin_succeeds():
    """Remove role by global admin should succeed."""
    admin = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(admin)

    user2 = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        root_domains=[f"test-{secrets.token_hex(4)}"],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    role = Role.objects.create(
        role="user", approved=False, organization=organization, user=user2
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/remove",
        headers=_csrf_headers(),
    )

    assert response.status_code == 200


# --- Upsert + v2 org user add + search endpoints (POST -> needs CSRF) -------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_upsert_organization_create():
    """Test upsert organization creates new org when none exists."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)
    payload = {
        "ip_blocks": [],
        "acronym": acronym,
        "name": name,
        "is_passive": False,
        "root_domains": ["unauthorized.com"],
        "state": "CA",
        "state_name": "California",
        "country": "USA",
        "type": "Government",
    }

    response = client.post(
        "/organizations_upsert", json=payload, headers=_csrf_headers()
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_upsert_organization_update():
    """Test upsert organization updates existing org when one exists."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    Organization.objects.create(
        acronym="TEST",
        name="Old Name",
        root_domains=["old.com"],
        ip_blocks=["192.168.2.0/24"],
        is_passive=True,
        state="NY",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": secrets.token_hex(2),
        "name": f"test-{secrets.token_hex(4)}",
        "root_domains": ["updated.com"],
        "ip_blocks": ["192.168.3.0/24"],
        "is_passive": False,
        "state": "CA",
    }

    response = client.post(
        "/organizations_upsert", json=payload, headers=_csrf_headers()
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_upsert_organization_unauthorized():
    """Standard user cannot upsert."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    payload = {
        "ip_blocks": [],
        "acronym": secrets.token_hex(2),
        "name": f"test-{secrets.token_hex(4)}",
        "is_passive": False,
        "root_domains": ["unauthorized.com"],
        "state": "CA",
    }

    response = client.post(
        "/organizations_upsert", json=payload, headers=_csrf_headers()
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access. View logs for details."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_add_user_to_org_v2_success():
    """Test adding a user to an organization via v2 endpoint."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.REGIONAL_ADMIN,
        region_id="region-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(admin)

    organization = Organization.objects.create(
        name="Test Organization",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        state="CA",
        region_id="region-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        region_id="region-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"user_id": str(user.id), "role": "member"}

    response = client.post(
        f"/v2/organizations/{organization.id}/users",
        json=payload,
        headers=_csrf_headers(),
    )

    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_add_user_to_org_v2_unauthorized():
    """Test adding a user to an organization via v2 endpoint fails for unauthorized user."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(user)

    organization = Organization.objects.create(
        name="Test Organization",
        root_domains=["test.com"],
        ip_blocks=[],
        is_passive=False,
        state="CA",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    target_user = User.objects.create(
        first_name="Target",
        last_name="User",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"user_id": str(target_user.id), "role": "member"}

    response = client.post(
        f"/v2/organizations/{organization.id}/users",
        json=payload,
        headers=_csrf_headers(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


# Search endpoints are POST -> include CSRF so you don’t get blocked before auth.
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_organizations")
def test_search_organizations_as_global_admin(mock_search):
    """Test searching organizations as global admin."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    _prime_client_auth_and_csrf(admin)

    mock_search.return_value = {
        "hits": {"hits": [{"_source": {"name": "Test Org", "region_id": "region-1"}}]}
    }

    payload = {"search_term": "Test Org", "regions": []}
    response = client.post(
        "/search/organizations", json=payload, headers=_csrf_headers()
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_organizations_v2_no_auth():
    """Test listing organizations via v2 endpoint without authentication fails."""
    response = client.post("/v2/organizations/search")
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_organizations_no_auth():
    """Test searching organizations without authentication fails."""
    payload = {"searchTerm": "Test", "regions": []}
    response = client.post("/search/organizations", json=payload)
    assert response.status_code == 401
