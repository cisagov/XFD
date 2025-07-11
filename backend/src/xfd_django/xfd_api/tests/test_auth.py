"""Test auth API."""
# Standard Python Libraries
import secrets
from unittest.mock import AsyncMock, patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_django.asgi import app
from xfd_mini_dl.models import User

client = TestClient(app)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_success(mock_get_jwt_from_code):
    """Test successful Okta callback authentication with real process_user."""
    email = "{}@example.com".format(secrets.token_hex(4))

    # Pre-create the user since creation is disabled in prod logic
    User.objects.create(
        email=email,
        okta_id="okta-user-id-123",
        first_name="Test",
        last_name="User",
        user_type="standard",
        invite_pending=True,
        last_logged_in="2000-01-01T00:00:00Z",
    )

    mock_get_jwt_from_code.return_value = {
        "decoded_token": {
            "email": email,
            "sub": "okta-user-id-123",
            "given_name": "Test",
            "family_name": "User",
        }
    }

    payload = {"code": "test-auth-code"}
    response = client.post("/auth/okta-callback", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["data"]["user"]["email"] == email
    assert response.cookies["crossfeed-token"] == data["token"]
    assert User.objects.filter(email=email).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_existing_user(mock_get_jwt_from_code):
    """Test Okta callback when the user already exists (should update last login)."""
    email = "{}@example.com".format(secrets.token_hex(4))
    User.objects.create(
        email=email,
        okta_id="okta-user-id-123",
        first_name="Existing",
        last_name="User",
        user_type="standard",
        invite_pending=True,
        last_logged_in="2000-01-01T00:00:00Z",  # Old login timestamp
    )

    # Mock the response from Okta token exchange
    mock_get_jwt_from_code.return_value = {
        "decoded_token": {
            "email": email,
            "sub": "okta-user-id-123",
            "given_name": "Existing",
            "family_name": "User",
        }
    }

    payload = {"code": "test-auth-code"}

    response = client.post("/auth/okta-callback", json=payload)

    assert response.status_code == 200

    # Ensure user still exists and was NOT duplicated
    assert User.objects.filter(email=email).count() == 1

    # Ensure last login timestamp was updated
    updated_user = User.objects.get(email=email)
    assert updated_user.last_logged_in != "2000-01-01T00:00:00Z"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_okta_callback_missing_code():
    """Test Okta callback with missing auth code (should fail)."""
    payload = {}  # No code provided

    response = client.post("/auth/okta-callback", json=payload)

    assert response.json()["status_code"] == 400
    assert response.json()["detail"] == "Code not found in request body"
