"""Test Queue Monitoring."""
# Standard Python Libraries
from datetime import datetime
import logging
import uuid

# Third-Party Libraries
import boto3
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)

LOGGER = logging.getLogger(__name__)


# Fake SQS client for a successful search scenario.
class FakeSQSClient:
    """Fake SQS client."""

    def list_queues(self):
        """List queues."""
        # Simulate one queue URL returned
        return {"QueueUrls": ["http://fake-sqs/queue/testQueue"]}

    def get_queue_attributes(self, QueueUrl, AttributeNames):
        """Get queue attributes."""
        # Return fixed fake attributes for testing
        return {
            "Attributes": {
                "ApproximateNumberOfMessages": "5",
                "ApproximateNumberOfMessagesNotVisible": "2",
                "ApproximateNumberOfMessagesDelayed": "1",
            }
        }


# Fake SQS client returning no queue URLs.
class FakeSQSClientNoResults:
    """Fake SQS client results."""

    def list_queues(self):
        """List queues."""
        return {"QueueUrls": []}

    def get_queue_attributes(self, QueueUrl, AttributeNames):
        """Get queue attributes."""
        return {"Attributes": {}}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_queues_success(monkeypatch):
    """Test that searching queues returns correct data when SQS provides one queue."""
    # Create a GlobalView user
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Override boto3.client to return our FakeSQSClient
    monkeypatch.setattr(boto3, "client", lambda service, **kwargs: FakeSQSClient())

    # Patch module-level variables in the endpoint code so that SQS is used in local mode
    monkeypatch.setattr("xfd_api.api_methods.queue_monitoring.is_local", True)
    monkeypatch.setattr(
        "xfd_api.api_methods.queue_monitoring.base_queue_url", "http://fake-sqs"
    )

    search_payload = {
        "page_size": 15,
        "page": 1,
        "sort": "name",
        "order": "ASC",
        "filters": {},
    }

    response = client.post(
        "/queues/search",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=search_payload,
    )

    LOGGER.info(response.json())  # Debug output if needed
    assert response.status_code == 200
    data = response.json()
    # We expect one queue to be returned
    assert data["count"] == 1
    result = data["result"][0]
    # The queue name is extracted as the last part of the URL ("testQueue")
    assert result["name"] == "testQueue"
    assert result["messages_available"] == 5
    assert result["messages_in_flight"] == 2
    assert result["messages_delayed"] == 1


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_queues_no_results(monkeypatch):
    """Test that searching queues returns an empty result when no queues are found."""
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4().hex}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    monkeypatch.setattr(
        boto3, "client", lambda service, **kwargs: FakeSQSClientNoResults()
    )
    monkeypatch.setattr("xfd_api.api_methods.queue_monitoring.is_local", True)
    monkeypatch.setattr(
        "xfd_api.api_methods.queue_monitoring.base_queue_url", "http://fake-sqs"
    )

    search_payload = {
        "page_size": 15,
        "page": 1,
        "sort": "name",
        "order": "ASC",
        "filters": {},
    }

    response = client.post(
        "/queues/search",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=search_payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["result"] == []


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_queues_unauthorized():
    """Test that the endpoint returns 401 when no valid authentication is provided."""
    search_payload = {
        "page_size": 15,
        "page": 1,
        "sort": "name",
        "order": "ASC",
        "filters": {},
    }

    response = client.post("/queues/search", json=search_payload)
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert "No valid authentication credentials provided" in detail
