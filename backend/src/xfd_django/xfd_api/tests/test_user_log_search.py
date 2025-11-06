"""User event log search tests."""
# Standard Python Libraries
from datetime import datetime, timezone
import json
import logging
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import Log, User, UserType

client = TestClient(app)

LOGGER = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_logs_success():
    """Test searching logs with filters as a GlobalViewAdmin."""
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    log = Log.objects.create(
        payload=json.dumps({"user": {"id": "12345", "action": "login"}}),
        created_at=datetime.now(),
        event_type="UserLogin",
        result="Success",
    )

    search_payload = {
        "event_type": {"value": "UserLogin"},
        "result": {"value": "Success"},
    }

    response = client.post(
        "/logs/search",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
        json=search_payload,
    )

    LOGGER.info(response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["result"][0]["id"] == str(log.id)
    assert data["result"][0]["event_type"] == "UserLogin"
    assert data["result"][0]["result"] == "Success"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_logs_unauthorized():
    """Test searching logs without authorization."""
    search_payload = {"event_type": {"value": "UserLogin"}}

    response = client.post("/logs/search", json=search_payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "No valid authentication credentials provided"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_logs_no_results():
    """Test searching logs when no logs match the filters."""
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    search_payload = {
        "eventType": {"value": "NonExistentEvent"},
    }

    response = client.post(
        "/logs/search",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
        json=search_payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert len(data["result"]) == 0


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_logs_by_date():
    """Test searching logs by timestamp filter."""
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    log = Log.objects.create(
        payload=json.dumps({"user": {"id": "67890", "action": "logout"}}),
        created_at=datetime(2023, 5, 10, 12, 0, 0),
        event_type="UserLogout",
        result="Success",
    )

    search_payload = {
        "timestamp": {"operator": "on_or_after", "value": "2023-05-10T00:00:00"},
    }

    response = client.post(
        "/logs/search",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
        json=search_payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert any(log_entry["id"] == str(log.id) for log_entry in data["result"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_logs_invalid_date_format():
    """Test searching logs with an invalid date format."""
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    search_payload = {
        "timestamp": {"operator": "on_or_after", "value": "invalid-date"},
    }

    response = client.post(
        "/logs/search",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
        json=search_payload,
    )

    assert response.status_code == 500
    assert "Invalid date format" in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_logs_filtered_success():
    """Test the new filtered log search endpoint."""
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(uuid.uuid4().hex),
        user_type=UserType.GLOBAL_VIEW,
    )
    Log.objects.create(
        payload=json.dumps({"info": "Log to be filtered out"}),
        created_at=datetime.now(tz=timezone.utc),
        event_type="UserLogout",
        result="success",
    )
    matching_log = Log.objects.create(
        payload=json.dumps({"info": "This should be found"}),
        created_at=datetime.now(tz=timezone.utc),
        event_type="UserLogin",
        result="success",
    )
    search_payload = {
        "page": 1,
        "page_size": 10,
        "filters": {"event_type": {"value": "UserLogin", "operator": "equals"}},
    }
    response = client.post(
        "/logs/filtered-search",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
        json=search_payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["result"]) == 1
    assert data["result"][0]["id"] == str(matching_log.id)
    assert data["result"][0]["event_type"] == "UserLogin"
