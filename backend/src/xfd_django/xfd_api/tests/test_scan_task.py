"""Test scan task."""
# Standard Python Libraries
from datetime import datetime
import logging
import secrets
from unittest.mock import patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import Organization, Role, Scan, ScanTask, User, UserType

client = TestClient(app)

LOGGER = logging.getLogger(__name__)


# Test: list by globalView should return scan tasks
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_scan_tasks_by_global_view():
    """Test scan-task."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
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
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_filtered_scan_tasks_by_global_view():
    """Test scan-task."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
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
    LOGGER.info(response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert any(task["id"] == str(scan_task.id) for task in data["result"])
    assert all(task["scan"]["name"] == "findomain" for task in data["result"])


# Test: list by regular user should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_scan_tasks_by_regular_user_fails():
    """Test scan-task."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Role.objects.create(user=user, organization=organization, role="user")

    response = client.post(
        "/scan-tasks/search",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access. View logs for details."}


# Test: kill by globalAdmin should kill the scan task
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_kill_scan_task_by_global_admin():
    """Test scan-task."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="created")
    scan_task.organizations.add(organization)

    response = client.post(
        "/scan-tasks/{}/kill".format(scan_task.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    LOGGER.info(response.json())
    assert response.status_code == 200


# Test: kill by globalAdmin should not work on a finished scan task
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_kill_finished_scan_task_by_global_admin_fails():
    """Test scan-task."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="finished")
    scan_task.organizations.add(organization)

    response = client.post(
        "/scan-tasks/{}/kill".format(scan_task.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 400
    assert "already finished" in response.text


# Test: kill by globalView should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_kill_scan_task_by_global_view_fails():
    """Test scan-task."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(scan=scan, type="fargate", status="created")
    scan_task.organizations.add(organization)

    response = client.post(
        "/scan-tasks/{}/kill".format(scan_task.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access. View logs for details."}


# Test: logs by globalView user should get logs
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.ecs_client.ECSClient.get_logs")
def test_get_logs_by_global_view(mock_get_logs):
    """Test scan-task."""
    mock_get_logs.return_value = "logs"

    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(
        scan=scan, fargate_task_arn="fargate_task_arn", type="fargate", status="started"
    )
    scan_task.organizations.add(organization)

    response = client.get(
        "/scan-tasks/{}/logs".format(scan_task.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.text == "logs"
    # Mock assertion to ensure logs fetching is called with the correct ARN
    mock_get_logs.assert_called_with("fargate_task_arn")


# Test: logs by regular user should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.ecs_client.ECSClient.get_logs")
def test_get_logs_by_regular_user_fails(mock_get_logs):
    """Test scan-task."""
    mock_get_logs.return_value = "logs"

    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="findomain", arguments={}, frequency=100)
    scan_task = ScanTask.objects.create(
        scan=scan, fargate_task_arn="fargate_task_arn", type="fargate", status="started"
    )
    scan_task.organizations.add(organization)

    response = client.get(
        "/scan-tasks/{}/logs".format(scan_task.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access. View logs for details."}
    mock_get_logs.assert_not_called()
