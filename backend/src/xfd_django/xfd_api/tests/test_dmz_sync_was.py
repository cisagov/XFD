"""Tests for the /dmz_sync/was_findings endpoint."""
# Standard Python Libraries
from datetime import date, datetime, timezone
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, WasFindings

client = TestClient(app)


def is_hex_sha256(candidate: str) -> bool:
    """Return True if the provided string appears to be a 64-char lowercase hex sha256."""
    if not candidate or len(candidate) != 64:
        return False
    for ch in candidate:
        if ch not in "0123456789abcdef":
            return False
    return True


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_empty_db():
    """Endpoint should return ok, empty payload, and checksum when DB has no findings."""
    now = datetime.now(timezone.utc)
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="globalAdmin",  # must match string check in is_global_write_admin
        created_at=now,
        updated_at=now,
    )

    response = client.post(
        "/dmz_sync/was_findings",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
        params={"page": 1, "per_page": 100},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert body["payload"] == []
    assert "X-Salted-Checksum" in response.headers
    assert is_hex_sha256(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_with_data():
    """Endpoint returns seeded WAS findings and valid checksum."""
    today = date.today()
    finding_1 = WasFindings.objects.create(
        name="Example Finding 1",
        last_detected=today,
    )
    finding_2 = WasFindings.objects.create(
        name="Example Finding 2",
        last_detected=today,
    )

    now = datetime.now(timezone.utc)
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="globalAdmin",  # must match string check
        created_at=now,
        updated_at=now,
    )

    response = client.post(
        "/dmz_sync/was_findings",
        headers={"Authorization": f"Bearer {create_jwt_token(admin_user)}"},
        params={"page": 1, "per_page": 100},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    ids = {item["finding_uid"] for item in body["payload"]}
    assert str(finding_1.finding_uid) in ids
    assert str(finding_2.finding_uid) in ids
    assert "X-Salted-Checksum" in response.headers
    assert is_hex_sha256(response.headers["X-Salted-Checksum"])


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_forbidden_non_admin():
    """Non-admin requests must be forbidden."""
    now = datetime.now(timezone.utc)
    non_admin = User.objects.create(
        first_name="Regular",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="standard",  # anything != "globalAdmin"
        created_at=now,
        updated_at=now,
    )
    response = client.post(
        "/dmz_sync/was_findings",
        headers={"Authorization": f"Bearer {create_jwt_token(non_admin)}"},
        params={"page": 1, "per_page": 100},
    )
    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_call_all_was_findings_forbidden_no_user_type():
    """Requests with no role should be forbidden by the write-admin gate."""
    now = datetime.now(timezone.utc)
    no_type_user = User.objects.create(
        first_name="NoType",
        last_name="User",
        email=f"{uuid.uuid4()}@example.com",
        user_type="",  # explicitly no role
        invite_pending=False,  # <-- ensure user is active so auth passes
        created_at=now,
        updated_at=now,
    )
    response = client.post(
        "/dmz_sync/was_findings",
        headers={"Authorization": f"Bearer {create_jwt_token(no_type_user)}"},
        params={"page": 1, "per_page": 100},
    )
    assert response.status_code == 403
    # Optional: confirm it's the role gate, not auth
    body = response.json()
    assert body.get("detail") in {
        "Unauthorized access.",
        "Unauthorized",
        "Insufficient permissions.",
    }
