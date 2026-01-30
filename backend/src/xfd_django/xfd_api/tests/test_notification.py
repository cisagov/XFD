"""Test notifications (cookie auth + CSRF)."""

# Standard Python Libraries
from datetime import datetime
from http.cookies import SimpleCookie
import secrets
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from xfd_api.auth import create_jwt_token, set_auth_and_csrf_cookies
from xfd_django.asgi import app
from xfd_mini_dl.models import Notification, User, UserType

client = TestClient(app)

CSRF_HEADER_NAME = "X-CSRF-Token"
AUTH_COOKIE_NAMES = ("crossfeed-token", "token")
CSRF_COOKIE_CANDIDATES = ("csrf", "xsrf", "csrf-token", "xsrf-token", "csrf_token")


# ---------------- Helpers ----------------


def _apply_set_cookie_headers_to_client(resp: StarletteResponse) -> None:
    """Copy Set-Cookie headers from a Starlette response into the TestClient cookie jar."""
    set_cookie_headers = resp.headers.getlist("set-cookie")
    if not set_cookie_headers:
        raise AssertionError(
            "No Set-Cookie headers were set by set_auth_and_csrf_cookies()"
        )

    for set_cookie in set_cookie_headers:
        c: SimpleCookie = SimpleCookie()
        c.load(set_cookie)
        for name, morsel in c.items():
            client.cookies.set(name, morsel.value)


def _prime_client_auth_and_csrf(user: User) -> None:
    """Prime TestClient with auth + csrf cookies using production helper."""
    token = create_jwt_token(user)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (b"host", b"testserver"),
            (b"x-forwarded-proto", b"http"),
        ],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
    }
    req = StarletteRequest(scope)

    resp = StarletteResponse()
    set_auth_and_csrf_cookies(resp, token, req)
    _apply_set_cookie_headers_to_client(resp)


def _csrf_headers() -> dict:
    """Find CSRF cookie and echo it back in the CSRF header."""
    csrf_cookie_name = None
    for k in client.cookies.keys():
        lk = k.lower()
        if any(tok in lk for tok in CSRF_COOKIE_CANDIDATES):
            csrf_cookie_name = k
            break

    if not csrf_cookie_name:
        raise AssertionError(
            f"No CSRF cookie found. Cookies present: {list(client.cookies.keys())}"
        )

    csrf_val = client.cookies.get(csrf_cookie_name)
    if not csrf_val:
        raise AssertionError(f"CSRF cookie '{csrf_cookie_name}' had no value")

    return {CSRF_HEADER_NAME: csrf_val}


@pytest.fixture(autouse=True)
def _clear_client_cookies_between_tests():
    """Prevent cookie leakage between tests (TestClient is global)."""
    client.cookies.clear()
    yield
    client.cookies.clear()


# ---------------- Tests ----------------


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_notification_as_global_view_admin():
    """Test notification creation by GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.post(
        "/notifications",
        headers=_csrf_headers(),
        json={
            "id": str(uuid.uuid4()),
            "maintenance_type": "Routine",
            "status": "Active",
            "updated_by": "AdminUser",
            "message": "Scheduled maintenance",
            "start_datetime": datetime.utcnow().isoformat(),
            "end_datetime": datetime.utcnow().isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["message"] == "Scheduled maintenance"
    assert Notification.objects.filter(id=data["id"]).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_notification_as_regular_user_fails():
    """Test notification creation should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.post(
        "/notifications",
        headers=_csrf_headers(),
        json={
            "id": str(uuid.uuid4()),
            "maintenance_type": "Routine",
            "status": "Active",
            "updated_by": "AdminUser",
            "message": "Scheduled maintenance",
            "start_datetime": datetime.utcnow().isoformat(),
            "end_datetime": datetime.utcnow().isoformat(),
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_notification_as_global_view_admin():
    """Test notification deletion by GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    notification = Notification.objects.create(
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Scheduled maintenance",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.delete(
        f"/notifications/{notification.id}",
        headers=_csrf_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Item deleted successfully",
    }
    assert not Notification.objects.filter(id=notification.id).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_notification_as_regular_user_fails():
    """Test notification deletion should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    notification = Notification.objects.create(
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Scheduled maintenance",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.delete(
        f"/notifications/{notification.id}",
        headers=_csrf_headers(),
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}
    assert Notification.objects.filter(id=notification.id).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_all_notifications():
    """Test retrieving all notifications."""
    Notification.objects.create(
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Test notification 1",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    Notification.objects.create(
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Test notification 2",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    response = client.get("/notifications")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_notification_by_id_as_global_view_admin():
    """Test retrieving a specific notification by ID as GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    notification = Notification.objects.create(
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Test notification",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.get(f"/notifications/{notification.id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Test notification"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_notification_by_id_as_regular_user_fails():
    """Test retrieving a specific notification by ID should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    notification = Notification.objects.create(
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Scheduled maintenance",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.get(f"/notifications/{notification.id}")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_notification_as_global_view_admin():
    """Test updating a notification by GlobalViewAdmin."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    notification = Notification.objects.create(
        id=uuid.uuid4(),
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Initial message",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.post(
        f"/update_notification/{notification.id}",
        headers=_csrf_headers(),
        json={
            "maintenance_type": "Routine",
            "status": "Updated",
            "updated_by": "AdminUser",
            "message": "Updated message",
            "start_datetime": datetime.utcnow().isoformat(),
            "end_datetime": datetime.utcnow().isoformat(),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Updated message"

    notification.refresh_from_db()
    assert notification.message == "Updated message"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_notification_as_regular_user_fails():
    """Test updating a notification should fail for a standard user."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email=f"{secrets.token_hex(4)}@example.com",
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    notification = Notification.objects.create(
        id=uuid.uuid4(),
        maintenance_type="Routine",
        status="Active",
        updated_by="AdminUser",
        message="Initial message",
        start_datetime=datetime.utcnow(),
        end_datetime=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    _prime_client_auth_and_csrf(user)

    response = client.post(
        f"/update_notification/{notification.id}",
        headers=_csrf_headers(),
        json={
            "maintenance_type": "Routine",
            "status": "Updated",
            "updated_by": "AdminUser",
            "message": "Updated message",
            "start_datetime": datetime.utcnow().isoformat(),
            "end_datetime": datetime.utcnow().isoformat(),
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to perform this action."
    }

    notification.refresh_from_db()
    assert notification.message == "Initial message"
