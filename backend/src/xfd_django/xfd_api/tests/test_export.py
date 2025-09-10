"""Test export API."""
# Standard Python Libraries
from datetime import datetime
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

client = TestClient(app)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_summary_columns_default():
    """Test default summary columns."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    response_no_cols = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={"collection": "summary", "mode": "json", "filters": {}, "columns": []},
    )
    assert response_no_cols.status_code == 200
    response_invalid_col = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {},
            "columns": ["invalid_column"],
        },
    )
    assert response_invalid_col.status_code == 422


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vulnerability_columns_default():
    """Test default vulnerability columns."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    response_no_cols = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {},
            "columns": [],
        },
    )
    assert response_no_cols.status_code == 200
    response_invalid_col = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {},
            "columns": ["invalid_column"],
        },
    )
    assert response_invalid_col.status_code == 422


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_summary_user_filters():
    """Test summary filters for user based on user type."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    response = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response.status_code == 200
    user_two = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    response_two = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user_two)},
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_two.status_code == 403
    assert response_two.json() == {"detail": "Unauthorized"}
    user_three = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    response_three = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user_three)},
        json={
            "collection": "summary",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_three.status_code == 403
    assert response_three.json() == {"detail": "Unauthorized"}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_vulnerability_user_filters():
    """Test vulnerability filters for user based on user type."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    response = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response.status_code == 200
    user_two = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    response_two = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user_two)},
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_two.status_code == 403
    assert response_two.json() == {"detail": "Unauthorized"}
    user_three = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id="3",
    )
    response_three = client.post(
        "/export",
        headers={"Authorization": "Bearer " + create_jwt_token(user_three)},
        json={
            "collection": "vulnerability",
            "mode": "json",
            "filters": {"region_id": "8"},
            "columns": [],
        },
    )
    assert response_three.status_code == 403
    assert response_three.json() == {"detail": "Unauthorized"}
