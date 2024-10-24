# Standard Python Libraries
from datetime import datetime
import secrets
from unittest.mock import patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.models import Organization, Role, Scan, ScanTask, User, UserType
from xfd_django.asgi import app

client = TestClient(app)


# Test: list by globalView should return scan tasks
@pytest.mark.django_db(transaction=True)
def test_list_scan_tasks_by_global_view():
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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="failed")
    scan_task.organizations.add(organization)

    response = client.post(
        "/scan-tasks/search",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert any(task["id"] == str(scan_task.id) for task in data["result"])


# Test: list by globalView with filter should return filtered scan tasks
@pytest.mark.django_db(transaction=True)
def test_list_filtered_scan_tasks_by_global_view():
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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="failed")
    scan_task.organizations.add(organization)

    scan2 = Scan.objects.create(name="censys", arguments={}, frequency=100)
    scan_task2 = ScanTask.objects.create(scan=scan2, type="fargate", status="failed")
    scan_task2.organizations.add(organization)

    response = client.post(
        "/scan-tasks/search",
        json={"filters": {"name": "findomain"}},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    print(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert any(task["id"] == str(scan_task.id) for task in data["result"])
    assert all(task["scan"]["name"] == "findomain" for task in data["result"])


# Test: list by regular user should fail
@pytest.mark.django_db(transaction=True)
def test_list_scan_tasks_by_regular_user_fails():
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

    Role.objects.create(user=user, organization=organization, role="user")

    response = client.post(
        "/scan-tasks/search",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access. View logs for details."}


# Test: kill by globalAdmin should kill the scan task
@pytest.mark.django_db(transaction=True)
def test_kill_scan_task_by_global_admin():
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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="created")
    scan_task.organizations.add(organization)

    response = client.post(
        f"/scan-tasks/{scan_task.id}/kill",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    print(response.json)
    assert response.status_code == 200


# Test: kill by globalAdmin should not work on a finished scan task
@pytest.mark.django_db(transaction=True)
def test_kill_finished_scan_task_by_global_admin_fails():
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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="finished")
    scan_task.organizations.add(organization)

    response = client.post(
        f"/scan-tasks/{scan_task.id}/kill",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 400
    assert "already finished" in response.text


# Test: kill by globalView should fail
@pytest.mark.django_db(transaction=True)
def test_kill_scan_task_by_global_view_fails():
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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="created")
    scan_task.organizations.add(organization)

    response = client.post(
        f"/scan-tasks/{scan_task.id}/kill",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access. View logs for details."}


# Test: logs by globalView user should get logs
@pytest.mark.django_db(transaction=True)
@patch("xfd_api.tasks.ecs_client.ECSClient.get_logs")
def test_get_logs_by_global_view(mock_get_logs):
    mock_get_logs.return_value = "logs"

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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(
        scan=scan, fargateTaskArn="fargateTaskArn", type="fargate", status="started"
    )
    scan_task.organizations.add(organization)

    response = client.get(
        f"/scan-tasks/{scan_task.id}/logs",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.text == "logs"
    # Mock assertion to ensure logs fetching is called with the correct ARN
    mock_get_logs.assert_called_with("fargateTaskArn")


# Test: logs by regular user should fail
@pytest.mark.django_db(transaction=True)
@patch("xfd_api.tasks.ecs_client.ECSClient.get_logs")
def test_get_logs_by_regular_user_fails(mock_get_logs):
    mock_get_logs.return_value = "logs"

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

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(
        scan=scan, fargateTaskArn="fargateTaskArn", type="fargate", status="started"
    )
    scan_task.organizations.add(organization)

    response = client.get(
        f"/scan-tasks/{scan_task.id}/logs",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access. View logs for details."}
    mock_get_logs.assert_not_called()
