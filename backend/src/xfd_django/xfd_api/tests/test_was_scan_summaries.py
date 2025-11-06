"""Tests for the /was_scan_summaries endpoint."""
# Standard Python Libraries
from datetime import datetime, timezone
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User  # and WasScanSummary if you seed data

client = TestClient(app)


def _mk_admin():
    now = datetime.now(timezone.utc)
    return User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="globalAdmin",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_was_scan_summaries_requires_auth():
    """Ensure authentication is required to access the endpoint."""
    # meta-test also checks unauthenticated paths return 401 or 405
    resp = client.post("/was_scan_summaries")
    assert resp.status_code in (401, 405)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_was_scan_summaries_empty_ok():
    """Endpoint should return ok, empty payload, and checksum when DB has no summaries."""
    admin = _mk_admin()
    resp = client.post(
        "/was_scan_summaries",
        headers={"Authorization": f"Bearer {create_jwt_token(admin)}"},
        params={"page": 1, "per_page": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["payload"], list)
    assert "X-Salted-Checksum" in resp.headers
    assert len(resp.headers["X-Salted-Checksum"]) == 64  # quick sanity
