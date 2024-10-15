# Standard Python Libraries
from datetime import datetime

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.models import User
from xfd_django.asgi import app

client = TestClient(app)


@pytest.mark.django_db
def test_login_success():
    # Mock login request
    response = client.post("/auth/login")
    assert response.status_code == 200
    assert response.json()


@pytest.mark.django_db
def test_callback_success_login_gov():
    # Simulate login via login.gov
    response = client.post(
        "/auth/callback",
        json={
            "code": "CODE",
            "state": "STATE",
            "origState": "ORIGSTATE",
            "nonce": "NONCE",
        },
    )
    assert response.status_code == 200
    assert response.json()["token"]
    assert response.json()["user"]
    assert response.json()["user"]["email"] == "test@crossfeed.cisa.gov"

    # Verify user in the database
    user = User.objects.get(id=response.json()["user"]["id"])
    assert user.firstName == ""
    assert user.lastName == ""


@pytest.mark.django_db
def test_callback_success_cognito():
    # Simulate Cognito login
    response = client.post(
        "/auth/callback", json={"token": "TOKEN_test2@crossfeed.cisa.gov"}
    )
    assert response.status_code == 200
    assert response.json()["token"]
    assert response.json()["user"]
    assert response.json()["user"]["email"] == "test2@crossfeed.cisa.gov"

    # Verify user in the database
    user = User.objects.get(id=response.json()["user"]["id"])
    assert user.firstName == ""
    assert user.lastName == ""


@pytest.mark.django_db
def test_callback_cognito_overwrite_cognito_id():
    # Simulate Cognito login with two different IDs
    response = client.post(
        "/auth/callback", json={"token": "TOKEN_test3@crossfeed.cisa.gov"}
    )
    assert response.status_code == 200
    user_id = response.json()["user"]["id"]
    cognito_id = response.json()["user"]["cognitoId"]

    response = client.post(
        "/auth/callback", json={"token": "TOKEN_test3@crossfeed.cisa.gov"}
    )
    user = User.objects.get(id=response.json()["user"]["id"])
    assert user.id == user_id
    assert user.cognitoId != cognito_id


@pytest.mark.django_db
def test_login_gov_then_cognito_preserves_ids():
    # Simulate login via login.gov
    response = client.post(
        "/auth/callback",
        json={
            "code": "CODE",
            "state": "STATE",
            "origState": "ORIGSTATE",
            "nonce": "NONCE",
        },
    )
    assert response.status_code == 200
    user_id = response.json()["user"]["id"]
    login_gov_id = response.json()["user"]["loginGovId"]

    # Simulate subsequent Cognito login
    response = client.post(
        "/auth/callback", json={"token": "TOKEN_test@crossfeed.cisa.gov"}
    )
    assert response.status_code == 200

    user = User.objects.get(id=response.json()["user"]["id"])
    assert user.id == user_id
    assert user.loginGovId == login_gov_id
    assert user.cognitoId is not None


@pytest.mark.django_db
def test_last_logged_in_is_updated():
    # Simulate Cognito login and check lastLoggedIn timestamp
    time_1 = datetime.now()
    response = client.post(
        "/auth/callback", json={"token": "TOKEN_test4@crossfeed.cisa.gov"}
    )
    assert response.status_code == 200
    time_2 = datetime.now()

    assert response.json()["token"]
    assert response.json()["user"]["lastLoggedIn"]
    assert time_1 <= response.json()["user"]["lastLoggedIn"] <= time_2
