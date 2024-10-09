# Standard Python Libraries
from datetime import datetime
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import (  # Assuming this function generates a user token
    create_jwt_token,
)
from xfd_api.models import (  # Adjust the import based on your project structure
    ApiKey,
    User,
)
from xfd_django.asgi import app  # Import the FastAPI app

client = TestClient(app)


@pytest.mark.django_db
def test_generate_api_key():
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="STANDARD",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    response = client.post(
        "/api-keys",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response.status_code == 200

    response2 = client.get(
        "/users/me",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response2.status_code == 200

    assert response.json()["hashedKey"] == response2.json()["apiKeys"][0]["hashedKey"]
    assert response.json()["key"][-4:] == response2.json()["apiKeys"][0]["lastFour"]
    assert len(response2.json()["apiKeys"]) == 1
    assert "key" not in response2.json()["apiKeys"][0]


@pytest.mark.django_db
def test_delete_own_api_key():
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="STANDARD",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    api_key = ApiKey.objects.create(
        hashedKey="1234",
        lastFour="1234",
        userId=user,
    )
    response = client.delete(
        f"/api-keys/{api_key.id}",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response.status_code == 200

    response2 = client.get(
        "/users/me",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response2.status_code == 200
    assert len(response2.json()["apiKeys"]) == 0


@pytest.mark.django_db
def test_delete_other_users_api_key_fails():
    user1 = User.objects.create(
        firstName="Test1",
        lastName="User1",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="STANDARD",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    user2 = User.objects.create(
        firstName="Test2",
        lastName="User2",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="GLOBAL_ADMIN",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    api_key = ApiKey.objects.create(
        hashedKey="1234",
        lastFour="1234",
        userId=user1,
    )

    # Try to delete user1's API key as user2
    response = client.delete(
        f"/api-keys/{api_key.id}",
        headers={
            "Authorization": create_jwt_token(
                {"id": user2.id, "userType": "GLOBAL_ADMIN"}
            )
        },
    )
    assert response.status_code == 404

    # Verify user1's API key still exists
    response2 = client.get(
        "/users/me",
        headers={
            "Authorization": create_jwt_token({"id": user1.id, "userType": "STANDARD"})
        },
    )
    assert response2.status_code == 200
    assert len(response2.json()["apiKeys"]) == 1


@pytest.mark.django_db
def test_using_valid_api_key():
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="STANDARD",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )
    response = client.post(
        "/api-keys",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response.status_code == 200
    api_key = response.json()["key"]

    # Verify user info with API key
    response_with_api_key = client.get("/users/me", headers={"Authorization": api_key})
    assert response_with_api_key.status_code == 200


@pytest.mark.django_db
def test_using_invalid_api_key():
    User.objects.create(
        firstName="Test",
        lastName="User",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="STANDARD",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.get("/users/me", headers={"Authorization": "invalid_key"})
    assert response.status_code == 401


@pytest.mark.django_db
def test_using_revoked_api_key():
    user = User.objects.create(
        firstName="Test",
        lastName="User",
        email=f"{secrets.token_hex(4)}@example.com",
        userType="STANDARD",
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
    )

    response = client.post(
        "/api-keys",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response.status_code == 200
    api_key_id = response.json()["id"]

    # Revoke the API key
    response = client.delete(
        f"/api-keys/{api_key_id}",
        headers={
            "Authorization": create_jwt_token({"id": user.id, "userType": "STANDARD"})
        },
    )
    assert response.status_code == 200

    # Verify revoked API key fails
    response_with_revoked_key = client.get(
        "/users/me", headers={"Authorization": response.json()["key"]}
    )
    assert response_with_revoked_key.status_code == 401
