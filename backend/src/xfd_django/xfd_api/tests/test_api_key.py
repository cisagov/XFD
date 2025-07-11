"""Test API key endpoints."""
# Standard Python Libraries
from datetime import datetime
import hashlib
import secrets
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import ApiKey, User, UserType

client = TestClient(app)


# Test: Creating an API key as a GlobalViewAdmin user should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_api_key_as_global_view_admin():
    """Test API key creation by GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/api-keys",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert len(data["api_key"]) == 32  # 16-byte hex string

    # Ensure the API key was stored in the database
    assert ApiKey.objects.filter(user=user).exists()
    api_key_instance = ApiKey.objects.get(user=user)
    assert api_key_instance.last_four == data["api_key"][-4:]
    assert (
        hashlib.sha256(data["api_key"].encode()).hexdigest()
        == api_key_instance.hashed_key
    )


# Test: Creating an API key as a regular user should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_api_key_as_regular_user_fails():
    """Test API key creation should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/api-keys",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}

    # Ensure no API key was created
    assert not ApiKey.objects.filter(user=user).exists()


# Test: Deleting an API key as a GlobalViewAdmin user should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_api_key_as_global_view_admin():
    """Test API key deletion by GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = client.delete(
        "/api-keys/{}".format(api_key.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "API Key deleted successfully",
    }

    # Ensure the API key was removed from the database
    assert not ApiKey.objects.filter(id=api_key.id).exists()


# Test: Deleting an API key as a regular user should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_api_key_as_regular_user_fails():
    """Test API key deletion should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = client.delete(
        "/api-keys/{}".format(api_key.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}

    # Ensure the API key was not removed from the database
    assert ApiKey.objects.filter(id=api_key.id).exists()


# Test: Getting all API keys as a regular user should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_all_api_keys_as_regular_user_fails():
    """Test retrieving all API keys should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/api-keys",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}


# Test: Getting all API keys as a GlobalViewAdmin user should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_all_api_keys_as_global_view_admin():
    """Test retrieving all API keys by GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = client.get(
        "/api-keys",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


# Test: Getting an API key by ID as a regular user should fail
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_api_key_by_id_as_regular_user_fails():
    """Test retrieving a specific API key by ID should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = client.get(
        "/api-keys/{}".format(api_key.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}


# Test: Getting an API key by ID as a GlobalViewAdmin user should succeed
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_api_key_by_id_as_global_view_admin():
    """Test retrieving a specific API key by ID as GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashlib.sha256(b"testkey").hexdigest(),
        last_four="test",
        user=user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = client.get(
        "/api-keys/{}".format(api_key.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200
    assert response.json()["last_four"] == "test"
