"""Test sync."""

# Standard Python Libraries
from datetime import datetime
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_api.utils.csv_utils import create_checksum
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)


dummy_org_data = {
    "data": {
        "id": "eaaa33cf-fe76-4b02-922f-18f80cdae158",
        "name": "Organization 2",
        "acronym": "ORG7",
        "retired": False,
        "created_at": "2024-08-28T11:43:35",
        "updated_at": "2024-03-07T02:43:38",
        "location": {
            "id": "b50b00a5-c854-4f8e-8725-585056513d37",
            "name": "Location 2",
        },
        "parent": None,
        "children": [
            {"id": "e44823d9-070e-44ca-95e9-1e9850e3fda4", "name": "Child Org 3"}
        ],
        "sectors": [
            {"id": "dc5f308b-b9ff-4ffa-af45-5d64ffb073f0", "name": "Sector 5"},
            {"id": "275300ed-dc0d-4e8b-88de-47844b573d55", "name": "Sector 4"},
            {"id": "5361b34e-26ed-468b-85ae-15e6487f56a3", "name": "Sector 2"},
        ],
        "cidrs": [
            {
                "id": "8499ddd8-8a35-4068-b6b1-ea2259ea106e",
                "network": "182.215.202.115/31",
                "start_ip": "182.215.202.115/32",
                "end_ip": "182.215.202.115/32",
            },
            {
                "id": "60aab3b3-b422-48ea-ac18-a6929c38ba40",
                "network": "105.48.177.68/27",
                "start_ip": "105.48.177.68/32",
                "end_ip": "105.48.177.68/32",
            },
            {
                "id": "305b6ba1-3c61-4492-96ab-67e5a2a1113a",
                "network": "159.63.84.79/26",
                "start_ip": "159.63.84.79/32",
                "end_ip": "159.63.84.79/32",
            },
        ],
    }
}


# Test: post valid data with invalid checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_sync_invalid_checksum_should_return_500():
    """Test sync with invalid checksum."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    invalid_checksum = create_checksum(dummy_org_data) + "invstr"
    response = client.post(
        "/sync",
        json=dummy_org_data,
        headers={
            "x-checksum": invalid_checksum,
            "Authorization": "Bearer {}".format(create_jwt_token(user)),
        },
    )
    assert response.status_code == 400


# Test: post valid data with missing checksum should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_sync_missing_checksum_should_return_500():
    """Test sync with missing checksum."""
    user = user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    headers = {"Authorization": "Bearer {}".format(create_jwt_token(user))}
    response = client.post("/sync", json=dummy_org_data, headers=headers)
    assert response.status_code == 400


# Test: post empty data should return 500
@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_sync_missing_data_should_return_422():
    """Test sync with missing data."""
    user = user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    headers = {
        "Authorization": "Bearer {}".format(create_jwt_token(user)),
        "x-checksum": create_checksum(dummy_org_data),
    }
    response = client.post("/sync", headers=headers)
    assert response.status_code == 422
