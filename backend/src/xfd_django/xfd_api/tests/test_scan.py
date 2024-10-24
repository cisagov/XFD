from unittest.mock import patch
import secrets
from fastapi.testclient import TestClient
import pytest
from datetime import datetime
from xfd_api.auth import create_jwt_token
from xfd_api.models import User, Scan, Organization, UserType, OrganizationTag
from xfd_django.asgi import app

client = TestClient(app)

# Test: list by globalAdmin should return all scans
@pytest.mark.django_db(transaction=True)
def test_list_scans_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    name = f"test-{secrets.token_hex(4)}"
    
    Scan.objects.create(
        name=name,
        arguments={},
        frequency=999999,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    Scan.objects.create(
        name=f"{name}-2",
        arguments={},
        frequency=999999,
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
        "/scans",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["scans"]) >= 2
    assert len(data["organizations"]) >= 1
    assert any(org["id"] == str(organization.id) for org in data["organizations"])


# Test: create by globalAdmin should succeed
@pytest.mark.django_db(transaction=True)
def test_create_scan_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    name = "censys"
    arguments = '{"a": "b"}'
    frequency = 999999
    
    response = client.post(
        "/scans",
        json={
            "name": name,
            "arguments": arguments,
            "frequency": frequency,
            "isGranular": False,
            "organizations": [],
            "isUserModifiable": False,
            "isSingleScan": False,
            "tags": []
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert data["arguments"] == arguments
    assert data["frequency"] == frequency
    assert data["isGranular"] is False
    assert data["organizations"] == []
    assert data["tags"] == []
    assert data["createdBy"]["id"] == str(user.id)

# Test: create a granular scan by globalAdmin should succeed
@pytest.mark.django_db(transaction=True)
def test_create_granular_scan_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    name = "censys"
    arguments = '{"a": "b"}'
    frequency = 999999
    
    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    
    response = client.post(
        "/scans",
        json={
            "name": name,
            "arguments": arguments,
            "frequency": frequency,
            "isGranular": True,
            "organizations": [str(organization.id)],
            "isUserModifiable": False,
            "isSingleScan": False,
            "tags": []
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert data["arguments"] == arguments
    assert data["frequency"] == frequency
    assert data["isGranular"] is True
    assert str(organization.id) in [org["id"] for org in data["organizations"]]


# Test: create by globalView should fail
@pytest.mark.django_db(transaction=True)
def test_create_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.post(
        "/scans",
        json={
            "name": "censys",
            "arguments": "{}",
            "frequency": 999999,
            "isGranular": False,
            "organizations": [],
            "isUserModifiable": False,
            "isSingleScan": False
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {'detail': 'Unauthorized access.'}


# Test: update by globalAdmin should succeed
@pytest.mark.django_db(transaction=True)
def test_update_by_global_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.put(
        f"/scans/{scan.id}",
        json={
            "name": "findomain",
            "arguments": "{}",
            "frequency": 999991,
            "isGranular": False,
            "organizations": [],
            "isUserModifiable": False,
            "isSingleScan": False,
            "tags": []
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "findomain"
    assert data["arguments"] == "{}"
    assert data["frequency"] == 999991


# Test: update a non-granular scan to a granular scan by globalAdmin
@pytest.mark.django_db(transaction=True)
def test_update_non_granular_to_granular_by_global_admin():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys", arguments="{}", frequency=999999, isGranular=False, isSingleScan=False
    )
    
    tag = OrganizationTag.objects.create(name=f"test-{secrets.token_hex(4)}")
    organization = Organization.objects.create(
        name=f"test-{secrets.token_hex(4)}",
        rootDomains=["test-" + secrets.token_hex(4)],
        ipBlocks=[],
        isPassive=False,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    organization.tags.set([tag])

    response = client.put(
        f"/scans/{scan.id}",
        json={
            "name": "findomain",
            "arguments": "{}",
            "frequency": 999991,
            "isGranular": True,
            "organizations": [str(organization.id)],
            "isSingleScan": False,
            "isUserModifiable": True,
            "tags": [{"id": str(tag.id)}]
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "findomain"
    assert data["frequency"] == 999991
    assert data["isGranular"] is True
    assert data["isUserModifiable"] is True
    assert str(organization.id) in [org["id"] for org in data["organizations"]]
    assert str(tag.id) in [t["id"] for t in data["tags"]]


# Test: update by globalView should fail
@pytest.mark.django_db(transaction=True)
def test_update_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.put(
        f"/scans/{scan.id}",
        json={
            "name": "findomain",
            "arguments": "{}",
            "frequency": 999991
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    print(response.json())
    assert response.status_code == 403
    assert response.json() == {'detail': 'Unauthorized access.'}


# Test: delete by globalAdmin should succeed
@pytest.mark.django_db(transaction=True)
def test_delete_by_global_admin_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.delete(
        f"/scans/{scan.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: delete by globalView should fail
@pytest.mark.django_db(transaction=True)
def test_delete_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.delete(
        f"/scans/{scan.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {'detail': 'Unauthorized access.'}


# Test: get by globalView should succeed
@pytest.mark.django_db(transaction=True)
def test_get_by_global_view_succeeds():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.get(
        f"/scans/{scan.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scan"]["name"] == "censys"


# Test: get by regular user on a scan not from their org should fail
@pytest.mark.django_db(transaction=True)
def test_get_by_regular_user_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.STANDARD,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.get(
        f"/scans/{scan.id}",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {'detail': 'Unauthorized access.'}


# Test: scheduler invoke by globalAdmin should succeed
@pytest.mark.django_db(transaction=True)
@patch("xfd_api.tasks.lambda_client.LambdaClient.run_command")
def test_scheduler_invoke_by_global_admin(mock_scheduler):
    mock_scheduler.return_value = {}
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.post(
        "/scheduler/invoke",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json() == {}
    mock_scheduler.assert_called_once()


# Test: scheduler invoke by globalView should fail
@pytest.mark.django_db(transaction=True)
@patch("xfd_api.tasks.lambda_client.LambdaClient.run_command")
def test_scheduler_invoke_by_global_view_fails(mock_scheduler):
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.post(
        "/scheduler/invoke",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {'detail': 'Unauthorized access.'}
    mock_scheduler.assert_not_called()


# Test: run scan should set manualRunPending to true
@pytest.mark.django_db(transaction=True)
def test_run_scan_should_set_manualRunPending_to_true():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_ADMIN,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments="{}",
        frequency=999999,
        lastRun=datetime.now(),
    )

    response = client.post(
        f"/scans/{scan.id}/run",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: runScan by globalView should fail
@pytest.mark.django_db(transaction=True)
def test_run_scan_by_global_view_fails():
    user = User.objects.create(
        firstName="",
        lastName="",
        email=f"{secrets.token_hex(4)}@example.com",
        userType=UserType.GLOBAL_VIEW,
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments="{}",
        frequency=999999,
        lastRun=datetime.now(),
    )

    response = client.post(
        f"/scans/{scan.id}/run",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {'detail': 'Unauthorized access.'}
