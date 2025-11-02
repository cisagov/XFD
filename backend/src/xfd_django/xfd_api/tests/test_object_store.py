"""Tests for the object-store API endpoint."""

# Standard Python Libraries
from datetime import datetime
import secrets
from unittest.mock import patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.api_methods.object_store.S3Client")
@patch("xfd_api.api_methods.object_store.ALLOWED_BUCKETS", new=["ignored-bucket"])
def test_get_presigned_url_basic(mock_s3_client):
    """Basic test for /v1/object-store/presigned-url that skips bucket checks."""
    # Create a test user
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock the S3 client's get_presigned_url method
    mock_s3_client_instance = mock_s3_client.return_value
    mock_s3_client_instance.get_presigned_url.return_value = (
        "https://mocked-url.com/object"
    )

    # Auth header
    token = create_jwt_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    # Request payload
    payload = {"bucket_name": "ignored-bucket", "object_key": "some/file.txt"}

    # Make request
    response = client.post(
        "/v1/object-store/presigned-url", json=payload, headers=headers
    )

    # Assertions
    assert response.status_code == 200
    assert response.json() == {"url": "https://mocked-url.com/object"}


@pytest.mark.django_db
def test_get_object_not_found():
    """Test retrieving a nonexistent object."""
    response = client.get("v1/object-store/nonexistent-key")
    assert response.status_code == 404
