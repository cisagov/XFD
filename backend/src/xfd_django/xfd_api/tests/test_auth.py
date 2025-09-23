"""Test auth API."""
# Standard Python Libraries
import secrets
from unittest.mock import AsyncMock, patch

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import sign_oauth_data
from xfd_django.asgi import app
from xfd_mini_dl.models import User

client = TestClient(app)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_success(mock_get_jwt_from_code):
    """Successful login with valid signed token."""
    email = "{}@example.com".format(secrets.token_hex(4))
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

    signed_token = sign_oauth_data("state-123", "code-verifier-xyz")
    response = client.post(
        "/auth/okta-callback",
        json={
            "code": "auth-code-abc",
            "state": "state-123",
            "signedToken": signed_token,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["data"]["user"]["email"] == email
    assert User.objects.filter(email=email).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_okta_callback_invalid_signed_token():
    """Reject callback with tampered signed token."""
    response = client.post(
        "/auth/okta-callback",
        json={
            "code": "auth-code",
            "state": "test-state",
            "signedToken": "invalid-token",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired token"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_okta_callback_state_mismatch():
    """Reject if signed token state does not match request state."""
    signed_token = sign_oauth_data("real-state", "verifier")
    response = client.post(
        "/auth/okta-callback",
        json={"code": "auth-code", "state": "wrong-state", "signedToken": signed_token},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "State mismatch"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_okta_callback_missing_signed_token():
    """Reject if signedToken is missing from request."""
    response = client.post(
        "/auth/okta-callback",
        json={"code": "auth-code", "state": "test-state"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required OAuth parameters"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_okta_callback_missing_code_or_state():
    """Reject request with missing code or state."""
    signed_token = sign_oauth_data("test_state", "verifier")

    # Missing 'code'
    response = client.post(
        "/auth/okta-callback", json={"state": "test-state", "signedToken": signed_token}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required OAuth parameters"

    # Missing 'state'
    response = client.post(
        "/auth/okta-callback", json={"code": "auth-code", "signedToken": signed_token}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing required OAuth parameters"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_json_serializable(mock_get_jwt_from_code):
    """Ensure /auth/okta-callback response is JSON serializable even with related fields."""
    approver_email = f"{secrets.token_hex(4)}@example.com"
    user_email = f"{secrets.token_hex(4)}@example.com"

    approver = User.objects.create(
        email=approver_email,
        okta_id="approver-xyz",
        user_type="global_admin",
        invite_pending=False,
    )

    User.objects.create(
        email=user_email,
        okta_id="user-abc",
        user_type="standard",
        approved_by=approver,
        invite_pending=False,
    )

    mock_get_jwt_from_code.return_value = {
        "decoded_token": {
            "email": user_email,
            "sub": "user-abc",
            "given_name": "Json",
            "family_name": "Safe",
        }
    }

    signed_token = sign_oauth_data("state-123", "verifier")
    response = client.post(
        "/auth/okta-callback",
        json={"code": "auth-code", "state": "state-123", "signedToken": signed_token},
    )

    assert response.status_code == 200
    assert "data" in response.json()
    assert "user" in response.json()["data"]


@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_token_exchange_failure(mock_get_jwt_from_code):
    """Simulate failure to exchange code for tokens."""
    mock_get_jwt_from_code.return_value = None

    signed_token = sign_oauth_data("state-123", "verifier")

    response = client.post(
        "/auth/okta-callback",
        json={"code": "bad-code", "state": "state-123", "signedToken": signed_token},
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Invalid authorization code or failed to retrieve tokens"
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_legacy_user_email_match_okta_id_added(mock_get_jwt):
    """Verify legacy user is upgraded by matching email."""
    email = "legacy@example.com"
    User.objects.create(
        email=email,
        okta_id=None,
        first_name="Old",
        last_name="User",
        user_type="standard",
        invite_pending=True,
    )

    mock_get_jwt.return_value = {
        "decoded_token": {
            "email": email,
            "sub": "new-okta-id",
            "given_name": "Old",
            "family_name": "User",
        }
    }

    signed_token = sign_oauth_data("legacy-state", "verifier")

    response = client.post(
        "/auth/okta-callback",
        json={
            "code": "legacy-code",
            "state": "legacy-state",
            "signedToken": signed_token,
        },
    )

    assert response.status_code == 200
    updated = User.objects.get(email=email)
    assert updated.okta_id == "new-okta-id"
    assert updated.invite_pending is False


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.JWT_SECRET", None)
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_jwt_secret_missing(mock_get_jwt):
    """Test case where JWT_SECRET is not defined."""
    email = f"{secrets.token_hex(4)}@example.com"
    mock_get_jwt.return_value = {
        "decoded_token": {
            "email": email,
            "sub": "okta-123",
            "given_name": "Token",
            "family_name": "Fail",
        }
    }

    signed_token = sign_oauth_data("state-zzz", "verifier")

    response = client.post(
        "/auth/okta-callback",
        json={"code": "code", "state": "state-zzz", "signedToken": signed_token},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal Server Error"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.auth.get_jwt_from_code", new_callable=AsyncMock)
def test_okta_callback_sets_crossfeed_cookie(mock_get_jwt):
    """Ensure crossfeed-token cookie is correctly set."""
    email = "cookie@example.com"
    User.objects.create(email=email, okta_id="cookie-id", user_type="standard")

    mock_get_jwt.return_value = {
        "decoded_token": {
            "email": email,
            "sub": "cookie-id",
            "given_name": "Cookie",
            "family_name": "Monster",
        }
    }

    signed_token = sign_oauth_data("cookie-state", "verifier")

    response = client.post(
        "/auth/okta-callback",
        json={"code": "code", "state": "cookie-state", "signedToken": signed_token},
    )

    assert response.status_code == 200
    assert "crossfeed-token" in response.cookies
    assert response.cookies["crossfeed-token"]


def test_get_oauth_meta_success():
    """Test /auth/get-oauth-meta with valid state and code_verifier."""
    payload = {"state": "abc123", "code_verifier": "verifierXYZ"}
    response = client.post("/auth/get-oauth-meta", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "signedToken" in data
    assert isinstance(data["signedToken"], str)
