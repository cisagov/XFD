# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import (  # Adjust import based on your auth implementation
    create_jwt_token,
)
from xfd_api.models import (  # Adjust import based on your project structure
    Notification,
    User,
)
from xfd_django.asgi import app  # Import your FastAPI app

client = TestClient(app)


@pytest.mark.django_db
def test_create_notification():
    # Create a test user
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email="testuser@example.com",
        userType="STANDARD",
    )

    # Define the notification data
    notification_data = {"message": "Test notification", "status": "unread"}

    # Send the POST request
    response = client.post(
        "/notifications",
        json=notification_data,
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )

    # Assert the response status code
    assert response.status_code == 200

    # Assert the notification was created correctly
    response_data = response.json()
    assert response_data["message"] == "Test notification"
    assert response_data["status"] == "unread"
    assert "id" in response_data  # Ensure that ID was assigned


@pytest.mark.django_db
def test_delete_notification():
    # Create a test user
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email="testuser@example.com",
        userType="STANDARD",
    )

    # Create a test notification
    notification = Notification.objects.create(
        message="Test notification", status="unread", userId=user
    )

    # Send the DELETE request
    response = client.delete(
        f"/notifications/{notification.id}",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )

    # Assert the response status code
    assert response.status_code == 200

    # Assert the response content
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["message"] == "Item deleted successfully"

    # Assert the notification no longer exists
    with pytest.raises(Notification.DoesNotExist):
        Notification.objects.get(id=notification.id)


@pytest.mark.django_db
def test_get_all_notifications():
    # Create a test user
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email="testuser@example.com",
        userType="STANDARD",
    )

    # Create two test notifications
    Notification.objects.create(message="Notification 1", status="unread", userId=user)
    Notification.objects.create(message="Notification 2", status="read", userId=user)

    # Send the GET request
    response = client.get(
        "/notifications",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )

    # Assert the response status code
    assert response.status_code == 200

    # Assert that two notifications are returned
    notifications = response.json()
    assert len(notifications) == 2
    assert notifications[0]["message"] == "Notification 1"
    assert notifications[1]["message"] == "Notification 2"


@pytest.mark.django_db
def test_get_notification_by_id():
    # Create a test user
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email="testuser@example.com",
        userType="STANDARD",
    )

    # Create a test notification
    notification = Notification.objects.create(
        message="Test notification", status="unread", userId=user
    )

    # Send the GET request
    response = client.get(
        f"/notifications/{notification.id}",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )

    # Assert the response status code
    assert response.status_code == 200

    # Assert the correct notification is returned
    response_data = response.json()
    assert response_data["message"] == "Test notification"
    assert response_data["status"] == "unread"
    assert response_data["id"] == str(notification.id)
