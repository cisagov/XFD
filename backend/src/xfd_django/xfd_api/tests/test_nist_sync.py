"""Tests for the NIST CVE sync API endpoint."""

# Standard Python Libraries
from datetime import datetime, timezone
import re
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import Cve as CveModel
from xfd_mini_dl.models import User, UserType

client = TestClient(app)


SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_cves_empty_db():
    """Test the /cves endpoint with an empty database."""
    # 1) create an admin user for auth with UTC-aware now
    now = datetime.now(timezone.utc)
    user = User.objects.create(
        first_name="T",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=now,
        updated_at=now,
    )

    # 2) call the endpoint
    response = client.post(
        "/dmz_sync/cves",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )

    # 3) assertions
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert body["payload"] == []

    # checksum header is present and looks like sha256 hex
    assert "X-Salted-Checksum" in response.headers
    assert SHA256_HEX_RE.fullmatch(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_cves_with_data():
    """Test the /cves endpoint with existing CVE data."""
    # use UTC-aware now for seeding CVEs
    now = datetime.now(timezone.utc)
    cve1 = CveModel.objects.create(
        id=uuid.uuid4(),
        name="CVE-2025-0001",
        published_at=now,
        modified_at=now,
        status="PUBLISHED",
    )
    cve2 = CveModel.objects.create(
        id=uuid.uuid4(),
        name="CVE-2025-0002",
        published_at=now,
        modified_at=now,
        status="PUBLISHED",
    )

    # create user & token
    user_now = datetime.now(timezone.utc)
    user = User.objects.create(
        first_name="T",
        last_name="Admin",
        email=f"{uuid.uuid4()}@example.com",
        user_type=UserType.GLOBAL_ADMIN,
        created_at=user_now,
        updated_at=user_now,
    )

    # call endpoint
    response = client.post(
        "/dmz_sync/cves",
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "ok"
    ids = {item["id"] for item in body["payload"]}
    assert ids == {str(cve1.id), str(cve2.id)}
    for item in body["payload"]:
        assert item["status"] == "PUBLISHED"

    # checksum header is present and looks like sha256 hex
    assert "X-Salted-Checksum" in response.headers
    assert SHA256_HEX_RE.fullmatch(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_cves_unauthorized():
    """Test the /cves endpoint without authorization."""
    # no Authorization header → 401 Unauthorized
    response = client.post("/dmz_sync/cves")
    assert response.status_code == 401
    assert "detail" in response.json()
