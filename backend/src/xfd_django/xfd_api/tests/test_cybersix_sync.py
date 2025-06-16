"""Test DMZ Sync CyberSix API endpoint."""

# Standard Python Libraries
from datetime import datetime
import uuid

# Third-Party Libraries
from fastapi import HTTPException as FastAPIHTTPException
from fastapi.testclient import TestClient
import pytest
import xfd_api.api_methods.dmz_sync as cybersix_module  # adjust path if needed
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)


@pytest.fixture
def admin_user(db):
    """Create a global-admin user."""
    return User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_success(admin_user, monkeypatch):
    """When fetch_cybersix_data returns payload+checksum, endpoint 201+headers."""
    dummy_payload = {
        "alerts": [],
        "mentions": [],
        "breaches": [],
        "exposures": [],
        "subdomains": [],
        "topcves": [],
    }
    dummy_checksum = "deadbeef"

    async def fake_fetch():
        # Note: fetch_cybersix_data() in your code now will wrap this into
        # {"status": "ok", "payload": { **dummy_payload, current_page:1, total_pages:1 }}.
        return dummy_payload, dummy_checksum

    monkeypatch.setattr(cybersix_module, "fetch_cybersix_data", fake_fetch)

    response = client.post(
        "/dmz_sync/cybersix_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
    )

    assert response.status_code == 201

    # Because your endpoint now injects current_page=1 and total_pages=1,
    # and wraps everything under “status” + “payload”, the JSON looks like this:
    expected = {
        "status": "ok",
        "payload": {
            "alerts": [],
            "mentions": [],
            "breaches": [],
            "exposures": [],
            "subdomains": [],
            "topcves": [],
            "current_page": 1,
            "total_pages": 1,
        },
    }
    assert response.json() == expected

    assert response.headers["X-Salted-Checksum"] == dummy_checksum


def test_cybersix_sync_unauthenticated():
    """Missing Authorization header → 401."""
    response = client.post("/dmz_sync/cybersix_sync")
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_fetch_error(admin_user, monkeypatch):
    """Generic exception in fetch_cybersix_data → 500 Sync error."""

    async def fake_fetch():
        raise RuntimeError("database down")

    monkeypatch.setattr(cybersix_module, "fetch_cybersix_data", fake_fetch)

    response = client.post(
        "/dmz_sync/cybersix_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
    )

    assert response.status_code == 500
    assert "Sync error: database down" in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_cybersix_sync_http_exception(admin_user, monkeypatch):
    """A HTTPException in fetch_cybersix_data is re-raised as is."""

    async def fake_fetch():
        raise FastAPIHTTPException(status_code=418, detail="I'm a teapot")

    monkeypatch.setattr(cybersix_module, "fetch_cybersix_data", fake_fetch)

    response = client.post(
        "/dmz_sync/cybersix_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
    )

    assert response.status_code == 418
    assert response.json()["detail"] == "I'm a teapot"
