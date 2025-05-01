"""Test DMZ Sync API endpoints."""

# Standard Python Libraries
from datetime import datetime, timedelta
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import (
    DataSource,
    Organization,
    ShodanAssets,
    ShodanVulns,
    User,
    UserType,
)

client = TestClient(app)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_success():
    """Test shodan sync success."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="SyncOrg",
        acronym="SYNC_ORG",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    data_source = DataSource.objects.create(
        name="Shodan",
        description="Shodan data source",
        last_run=datetime.now().date(),
    )

    ShodanAssets.objects.create(
        organization=organization,
        organization_name="SyncOrg",
        ip_string="8.8.8.8",
        port=443,
        protocol="https",
        timestamp=datetime.now(),
        data_source=data_source,
    )

    ShodanVulns.objects.create(
        organization=organization,
        organization_name="SyncOrg",
        ip_string="8.8.8.8",
        port="443",
        protocol="https",
        timestamp=datetime.now(),
        data_source=data_source,
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "shodan_assets" in body["payload"]["data"]
    assert "shodan_vulns" in body["payload"]["data"]
    assert "X-Salted-Checksum" in response.headers


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_missing_date():
    """Test shodan sync missing date."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
    }

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "since_date is required."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_unauthorized_user():
    """Test shodan sync unauthorized header."""
    user = User.objects.create(
        first_name="Test",
        last_name="Viewer",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "SYNC_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_shodan_sync_org_not_found():
    """Test shodan sync not found."""
    user = User.objects.create(
        first_name="Test",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {
        "acronym": "NON_EXISTENT_ORG",
        "page": 1,
        "page_size": 10,
        "since_date": (datetime.now() - timedelta(days=1)).isoformat(),
    }

    response = client.post(
        "/dmz_sync/shodan_sync",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
        json=payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Parent organization not found"
