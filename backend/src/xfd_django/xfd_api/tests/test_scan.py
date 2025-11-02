"""Test scan."""
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
from xfd_mini_dl.models import Organization, OrganizationTag, Scan, User, UserType

client = TestClient(app)

LOGGER = logging.getLogger(__name__)


# Test: list by globalAdmin should return all scans
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_scans_by_global_admin():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    name = "test-{}".format(secrets.token_hex(4))

    Scan.objects.create(
        name=name,
        arguments={},
        frequency=999999,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    Scan.objects.create(
        name="{}-2".format(name),
        arguments={},
        frequency=999999,
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
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_scan_by_global_admin():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
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
            "is_granular": False,
            "organizations": [],
            "is_user_modifiable": False,
            "is_single_scan": False,
            "tags": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert data["arguments"] == arguments
    assert data["frequency"] == frequency
    assert data["is_granular"] is False
    assert data["organizations"] == []
    assert data["tags"] == []
    assert data["created_by"]["id"] == str(user.id)


# Test: create a granular scan by globalAdmin should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_granular_scan_by_global_admin():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    name = "censys"
    arguments = '{"a": "b"}'
    frequency = 999999

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/scans",
        json={
            "name": name,
            "arguments": arguments,
            "frequency": frequency,
            "is_granular": True,
            "organizations": [str(organization.id)],
            "is_user_modifiable": False,
            "is_single_scan": False,
            "tags": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert data["arguments"] == arguments
    assert data["frequency"] == frequency
    assert data["is_granular"] is True
    assert str(organization.id) in [org["id"] for org in data["organizations"]]


# Test: create by globalView should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_by_global_view_fails():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/scans",
        json={
            "name": "censys",
            "arguments": "{}",
            "frequency": 999999,
            "is_granular": False,
            "organizations": [],
            "is_user_modifiable": False,
            "is_single_scan": False,
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: update by globalAdmin should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_by_global_admin_succeeds():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.post(
        "/update_scan/{}".format(scan.id),
        json={
            "name": "findomain",
            "arguments": "{}",
            "frequency": 999991,
            "is_granular": False,
            "organizations": [],
            "is_user_modifiable": False,
            "is_single_scan": False,
            "tags": [],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "findomain"
    assert data["arguments"] == "{}"
    assert data["frequency"] == 999991


# Test: update a non-granular scan to a granular scan by globalAdmin
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_non_granular_to_granular_by_global_admin():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments="{}",
        frequency=999999,
        is_granular=False,
        is_single_scan=False,
    )

    tag = OrganizationTag.objects.create(name="test-{}".format(secrets.token_hex(4)))
    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    organization.tags.set([tag])

    response = client.post(
        "/update_scan/{}".format(scan.id),
        json={
            "name": "findomain",
            "arguments": "{}",
            "frequency": 999991,
            "is_granular": True,
            "organizations": [str(organization.id)],
            "is_single_scan": False,
            "is_user_modifiable": True,
            "tags": [{"id": str(tag.id)}],
        },
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    LOGGER.info(response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "findomain"
    assert data["frequency"] == 999991
    assert data["is_granular"] is True
    assert data["is_user_modifiable"] is True
    assert str(organization.id) in [org["id"] for org in data["organizations"]]
    assert str(tag.id) in [t["id"] for t in data["tags"]]


# Test: update by globalView should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_by_global_view_fails():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.post(
        "/update_scan/{}".format(scan.id),
        json={"name": "findomain", "arguments": "{}", "frequency": 999991},
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    LOGGER.info(response.json())
    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: delete by globalAdmin should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_by_global_admin_succeeds():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.delete(
        "/scans/{}".format(scan.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: delete by globalView should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_by_global_view_fails():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.delete(
        "/scans/{}".format(scan.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: get by globalView should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_by_global_view_succeeds():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.get(
        "/scans/{}".format(scan.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["scan"]["name"] == "censys"


# Test: get by regular user on a scan not from their org should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_by_regular_user_fails():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(name="censys", arguments="{}", frequency=999999)

    response = client.get(
        "/scans/{}".format(scan.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


# Test: scheduler invoke by globalAdmin should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.lambda_client.LambdaClient.run_command")
def test_scheduler_invoke_by_global_admin(mock_scheduler):
    """Test scan."""
    mock_scheduler.return_value = {}
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/scheduler/invoke",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    LOGGER.info(response.json())
    assert response.status_code == 200
    assert response.json() == {}
    mock_scheduler.assert_called_once()


# Test: scheduler invoke by globalView should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.lambda_client.LambdaClient.run_command")
def test_scheduler_invoke_by_global_view_fails(mock_scheduler):
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/scheduler/invoke",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}
    mock_scheduler.assert_not_called()


# Test: run scan should set manualRunPending to true
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_run_scan_should_set_manualRunPending_to_true():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments="{}",
        frequency=999999,
        last_run=datetime.now(),
    )

    response = client.post(
        "/scans/{}/run".format(scan.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200


# Test: runScan by globalView should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_run_scan_by_global_view_fails():
    """Test scan."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    scan = Scan.objects.create(
        name="censys",
        arguments="{}",
        frequency=999999,
        last_run=datetime.now(),
    )

    response = client.post(
        "/scans/{}/run".format(scan.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_granular_scans_as_global_admin():
    """Test that a GlobalViewAdmin can retrieve granular scans."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Scan.objects.create(
        name="Granular Scan 1",
        is_granular=True,
        is_user_modifiable=True,
        is_single_scan=False,
        frequency=999999,
    )
    Scan.objects.create(
        name="Granular Scan 2",
        is_granular=True,
        is_user_modifiable=True,
        is_single_scan=False,
        frequency=999999,
    )
    Scan.objects.create(
        name="Non Granular Scan",
        is_granular=False,
        is_user_modifiable=True,
        is_single_scan=False,
        frequency=999999,
    )

    response = client.get(
        "/granularScans",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "scans" in data
    assert isinstance(data["scans"], list)
    assert len(data["scans"]) == 2  # Only the granular scans should be returned
    assert data["scans"][0]["name"] in ["Granular Scan 1", "Granular Scan 2"]
    assert "schema" in data  # Check that SCAN_SCHEMA is included in response


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_granular_scans_as_standard_user_fails():
    """Test that a standard user cannot retrieve granular scans."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/granularScans",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_granular_scans_no_auth():
    """Test that an unauthenticated request returns 401."""
    response = client.get("/granularScans")
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_granular_scans_empty():
    """Test that an empty result is returned if no granular scans exist."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/granularScans",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "scans" in data
    assert isinstance(data["scans"], list)
    assert len(data["scans"]) == 0  # No scans exist
    assert "schema" in data  # Ensure schema is still returned
