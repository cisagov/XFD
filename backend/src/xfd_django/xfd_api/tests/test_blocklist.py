"""Test Blocklist Check."""

# Standard Library
# Standard Python Libraries
from datetime import datetime, timezone
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import Blocklist, User, UserType

client = TestClient(app)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_blocklist_check_blocked():
    """Test blocklist check (blocked IP)."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
    )
    blocked_ip = "111.111.111.111"

    Blocklist.objects.create(
        ip=blocked_ip,
        created_at=datetime.now(timezone.utc),
        reports=1,
        attacks=1,
    )

    response = client.post(
        "/blocklist/check/",
        json={"ip_addresses": [blocked_ip]},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    assert response.json() == {
        "111.111.111.111": {
            "attacks": 1,
            "reports": 1,
        }
    }


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_blocklist_check_unblocked():
    """Test blocklist check (unblocked IP)."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
    )
    unblocked_ip = "222.222.222.222"

    response = client.post(
        "/blocklist/check/",
        json={"ip_addresses": [unblocked_ip]},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    assert response.json() == {
        unblocked_ip: {
            "attacks": 0,
            "reports": 0,
        }
    }
