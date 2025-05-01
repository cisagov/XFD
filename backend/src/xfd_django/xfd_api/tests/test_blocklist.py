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
    """Test blocklist check."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
    )
    random_ip_address = "111.111.111.111"
    Blocklist.objects.create(
        ip=random_ip_address, created_at=datetime.now(timezone.utc)
    )

    response = client.get(
        "/blocklist/check/",
        params={"ip_address": random_ip_address},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "BLOCKED"}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_blocklist_check_unblocked():
    """Test blocklist check."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
    )
    random_ip_address = "222.222.222.222"
    response = client.get(
        "/blocklist/check/",
        params={"ip_address": random_ip_address},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.json() == {"status": "UNBLOCKED"}
