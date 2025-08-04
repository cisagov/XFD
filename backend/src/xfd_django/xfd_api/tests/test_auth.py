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

    response = client.post(
        "/auth/okta-callback",
        json={"code": "test-auth-code", "state": "test-state"},
        cookies={
            "oauth_state": "test-state",
            "pkce_code_verifier": "test-code-verifier",
        },
    )

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

    response = client.post(
        "/auth/okta-callback",
        json={"code": "test-auth-code", "state": "test-state"},
        cookies={
            "oauth_state": "test-state",
            "pkce_code_verifier": "test-code-verifier",
        },
    )

    assert response.status_code == 200

    # Ensure user still exists and was NOT duplicated
    assert User.objects.filter(email=email).count() == 1

    # Ensure last login timestamp was updated
    updated_user = User.objects.get(email=email)
    assert updated_user.last_logged_in != "2000-01-01T00:00:00Z"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_okta_callback_missing_code():
    """Test Okta callback with missing auth code (should fail)."""
    response = client.post(
        "/auth/okta-callback",
        json={"state": "test-state"},
        cookies={
            "oauth_state": "test-state",
            "pkce_code_verifier": "test-code-verifier",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required OAuth parameters"


# Test that the response is JSON serializable
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_user_approved_by_admin(mock_get_jwt_from_code):
    """Ensure /auth/okta-callback user object is fully JSON serializable."""
    approver_user_email = "{}@example.com".format(secrets.token_hex(4))
    approved_user_email = "{}@example.com".format(secrets.token_hex(4))

    approver = User.objects.create(
        email=approver_user_email,
        okta_id="okta-approver-id",
        first_name="Approver",
        last_name="User",
        user_type="global_admin",
        invite_pending=False,
    )

    User.objects.create(
        email=approved_user_email,
        okta_id="okta-user-id-456",
        first_name="Test",
        last_name="User",
        user_type="standard",
        approved_by=approver,
        invite_pending=False,
    )

    mock_get_jwt_from_code.return_value = {
        "decoded_token": {
            "email": approved_user_email,
            "sub": "okta-user-id-456",
            "given_name": "Test",
            "family_name": "User",
        }
    }

    response = client.post(
        "/auth/okta-callback",
        json={"code": "test-auth-code", "state": "test-state"},
        cookies={
            "oauth_state": "test-state",
            "pkce_code_verifier": "test-code-verifier",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["user"]


def test_set_oauth_cookies_success():
    """Test setting PKCE code_verifier and state cookies successfully."""
    payload = {"code_verifier": "test-code-verifier-123", "state": "test-state-456"}

    response = client.post("/auth/set-oauth-cookies", json=payload)

    assert response.status_code == 200
    cookies = response.cookies

    # Ensure cookies are properly set
    assert cookies["oauth_state"] == "test-state-456"
    assert cookies["pkce_code_verifier"] == "test-code-verifier-123"


def test_set_oauth_cookies_missing_state():
    """Test missing state results in 400 error."""
    payload = {"code_verifier": "test-code-verifier-123"}

    response = client.post("/auth/set-oauth-cookies", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing PKCE code_verifier or state"


def test_set_oauth_cookies_missing_code_verifier():
    """Test missing code_verifier results in 400 error."""
    payload = {"state": "test-state-456"}

    response = client.post("/auth/set-oauth-cookies", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing PKCE code_verifier or state"


def test_set_oauth_cookies_missing_both():
    """Test missing both state and code_verifier results in 400 error."""
    payload = {}

    response = client.post("/auth/set-oauth-cookies", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing PKCE code_verifier or state"
