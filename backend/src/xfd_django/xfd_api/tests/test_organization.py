# Standard Python Libraries
from datetime import datetime
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.models import (
    Organization,
    OrganizationTag,
    Role,
    Scan,
    ScanTask,
    User,
    UserType,
)
from xfd_django.asgi import app

client = TestClient(app)


# Test: Creating an organization by global admin should succeed
@pytest.mark.django_db(transaction=True)
def test_create_org_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)

    response = client.post(
        "/organizations/",
        json={
            "ipBlocks": [],
            "acronym": acronym,
            "name": name,
            "rootDomains": ["cisa.gov"],
            "isPassive": False,
            "tags": [{"name": "test"}],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["createdBy"]["id"] == str(user.id)
    assert data["name"] == name
    assert data["tags"][0]["name"] == "test"


# Test: Cannot add organization with the same acronym
@pytest.mark.django_db(transaction=True)
def test_create_duplicate_org_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)

    client.post(
        "/organizations/",
        json={
            "ipBlocks": [],
            "acronym": acronym,
            "name": name,
            "rootDomains": ["cisa.gov"],
            "isPassive": False,
            "tags": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    # Attempt to create another organization with the same acronym
    response = client.post(
        "/organizations/",
        json={
            "ipBlocks": [],
            "acronym": acronym,
            "name": name,
            "rootDomains": ["cisa.gov"],
            "isPassive": False,
            "tags": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 500


# Test: Creating an organization by global view user should fail
@pytest.mark.django_db(transaction=True)
def test_create_org_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    print(user)

    name = f"test-{secrets.token_hex(4)}"
    acronym = secrets.token_hex(2)

    response = client.post(
        "/organizations/",
        json={
            "ipBlocks": [],
            "acronym": acronym,
            "name": name,
            "rootDomains": ["cisa.gov"],
            "isPassive": False,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: Update organization by global admin
@pytest.mark.django_db(transaction=True)
def test_update_org_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        acronym=secrets.token_hex(2),
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test.com"],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    new_name = f"test-{secrets.token_hex(4)}"
    new_acronym = secrets.token_hex(2)
    new_root_domains = ["newdomain.com"]
    new_ip_blocks = ["1.1.1.1"]
    is_passive = True
    tags = [{"name": "updated"}]

    response = client.put(
        f"/organizations/{organization.id}",
        json={
            "name": new_name,
            "acronym": new_acronym,
            "rootDomains": new_root_domains,
            "ipBlocks": new_ip_blocks,
            "isPassive": is_passive,
            "tags": tags,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == new_name
    assert data["rootDomains"] == new_root_domains
    assert data["ipBlocks"] == new_ip_blocks
    assert data["isPassive"] == is_passive
    assert data["tags"][0]["name"] == tags[0]["name"]


# Test: Update organization by global view should fail
@pytest.mark.django_db(transaction=True)
def test_update_org_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        acronym=secrets.token_hex(2),
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test.com"],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    new_name = f"test-{secrets.token_hex(4)}"
    new_acronym = secrets.token_hex(2)
    new_root_domains = ["newdomain.com"]
    new_ip_blocks = ["1.1.1.1"]
    is_passive = True
    tags = [{"name": "updated"}]

    response = client.put(
        f"/organizations/{organization.id}",
        json={
            "name": new_name,
            "acronym": new_acronym,
            "rootDomains": new_root_domains,
            "ipBlocks": new_ip_blocks,
            "isPassive": is_passive,
            "tags": tags,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: Deleting an organization by global admin should succeed
@pytest.mark.django_db(transaction=True)
def test_delete_org_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test.com"],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.delete(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: Deleting an organization by org admin should fail
@pytest.mark.django_db(transaction=True)
def test_delete_org_by_org_admin_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test.com"],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    response = client.delete(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: Deleting an organization by global view should fail
@pytest.mark.django_db(transaction=True)
def test_delete_org_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        acronym=secrets.token_hex(2),
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test.com"],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.delete(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: List organizations by global view should succeed
@pytest.mark.django_db(transaction=True)
def test_list_orgs_by_global_view_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Create an organization
    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.get(
        "/organizations",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


# Test: List organizations by org member should only return their org
@pytest.mark.django_db(transaction=True)
def test_list_orgs_by_org_member_only_gets_their_org():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Create organizations
    organization1 = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization2 = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Assign user a role in organization1
    Role.objects.create(
        user=user,
        organization=organization1,
        role="user",
    )

    # Fetch organizations
    response = client.get(
        "/organizations",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(organization1.id)


# Test: Get organization by global view should fail
@pytest.mark.django_db(transaction=True)
def test_get_org_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.get(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}


# Test: Get organization by org admin user should pass
@pytest.mark.django_db(transaction=True)
def test_get_org_by_org_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    response = client.get(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == organization.name


# Test: Get organization by org admin of different org should fail
@pytest.mark.django_db(transaction=True)
def test_get_org_by_org_admin_of_different_org_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization1 = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization2 = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Assign admin role to the user for organization1
    Role.objects.create(
        user=user,
        organization=organization1,
        role="admin",
    )

    response = client.get(
        f"/organizations/{organization2.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}


# Test: Get organization by org regular user should fail
@pytest.mark.django_db(transaction=True)
def test_get_org_by_org_regular_user_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Assign regular user role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="user",
    )

    response = client.get(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}


# Test: Get organization by org admin should return associated scantasks
@pytest.mark.django_db(transaction=True)
def test_get_org_with_scan_tasks_by_org_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    # Create a scan and scantask associated with the organization
    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
    )

    scan_task = ScanTask.objects.create(scan=scan, status="created", type="fargate")

    scan_task.organizations.add(organization)

    response = client.get(
        f"/organizations/{organization.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == organization.name
    assert len(data["scanTasks"]) == 1
    assert data["scanTasks"][0]["id"] == str(scan_task.id)
    assert data["scanTasks"][0]["scan"]["id"] == str(scan.id)


# Test: Enabling a user-modifiable scan by org admin should succeed
@pytest.mark.django_db(transaction=True)
def test_enable_user_modifiable_scan_by_org_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        isGranular=True,
        isUserModifiable=True,
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["granularScans"]) == 1
    assert data["granularScans"][0]["id"] == str(scan.id)


# Test: Disabling a user-modifiable scan by org admin should succeed
@pytest.mark.django_db(transaction=True)
def test_disable_user_modifiable_scan_by_org_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        isGranular=True,
        isUserModifiable=True,
    )

    scan_task = ScanTask.objects.create(
        scan=scan,
        status="created",
        type="fargate",
    )
    scan_task.organizations.add(organization)

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": False},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["granularScans"]) == 0


# Test: Enabling a user-modifiable scan by org user should fail
@pytest.mark.django_db(transaction=True)
def test_enable_user_modifiable_scan_by_org_user_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="user",
    )

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        isGranular=True,
        isUserModifiable=True,
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403


# Test: Enabling a user-modifiable scan by global admin should succeed
@pytest.mark.django_db(transaction=True)
def test_enable_user_modifiable_scan_by_global_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        isGranular=True,
        isUserModifiable=True,
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["granularScans"]) == 1
    assert data["granularScans"][0]["id"] == str(scan.id)


# Test: Enabling a non-user-modifiable scan by org admin should fail
@pytest.mark.django_db(transaction=True)
def test_enable_non_user_modifiable_scan_by_org_admin_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    scan = Scan.objects.create(
        name="censys",
        arguments={},
        frequency=999999,
        isGranular=True,
        isUserModifiable=False,  # Not user-modifiable
    )

    response = client.post(
        f"/organizations/{organization.id}/granularScans/{scan.id}/update",
        json={"enabled": True},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 404


# Test: Approving a role by global admin should succeed
@pytest.mark.django_db(transaction=True)
def test_approve_role_by_global_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/approve",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    role.refresh_from_db()
    assert role.approved is True


# Test: Approving a role by global view should fail
@pytest.mark.django_db(transaction=True)
def test_approve_role_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/approve",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    role.refresh_from_db()
    assert role.approved is False


# Test: Approving a role by org admin should succeed
@pytest.mark.django_db(transaction=True)
def test_approve_role_by_org_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/approve",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    role.refresh_from_db()
    assert role.approved is True


# Test: Approving a role by org user should fail
@pytest.mark.django_db(transaction=True)
def test_approve_role_by_org_user_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="user",
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/approve",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    role.refresh_from_db()
    assert role.approved is False


# Test: removeRole by globalAdmin should work
@pytest.mark.django_db(transaction=True)
def test_remove_role_by_global_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/remove",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: removeRole by globalView should fail
@pytest.mark.django_db(transaction=True)
def test_remove_role_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/remove",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: removeRole by org admin should succeed
@pytest.mark.django_db(transaction=True)
def test_remove_role_by_org_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/remove",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: removeRole by org user should fail
@pytest.mark.django_db(transaction=True)
def test_remove_role_by_org_user_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="user",
    )

    role = Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
    )

    response = client.post(
        f"/organizations/{organization.id}/roles/{role.id}/remove",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: getTags by globalAdmin should work
@pytest.mark.django_db(transaction=True)
def test_get_tags_by_global_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    OrganizationTag.objects.create(
        name=f"test-{secrets.token_hex(4)}",
    )

    response = client.get(
        "/organizations/tags",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


# Test: getTags by standard user should return no tags
@pytest.mark.django_db(transaction=True)
def test_get_tags_by_standard_user_returns_no_tags():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    OrganizationTag.objects.create(
        name=f"test-{secrets.token_hex(4)}",
    )

    response = client.get(
        "/organizations/tags",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert len(response.json()) == 0
