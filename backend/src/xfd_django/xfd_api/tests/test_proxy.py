"""Test proxy."""
# Standard Python Libraries
from datetime import datetime
import logging
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import User, UserType

# Initialize the test client with the FastAPI app
client = TestClient(app)

LOGGER = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_not_authorized_to_access_pe_proxy():
    """Test that a standard user is not authorized to access P&E proxy."""
    # Create a standard user
    user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Generate a JWT token for the user
    token = create_jwt_token(user)

    # Make a GET request to the P&E proxy endpoint with the user's token
    response = client.get("/pe", headers={"Authorization": "Bearer {}".format(token)})

    # Assert that the user receives a 403 Unauthorized response
    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_global_admin_authorized_to_access_pe_proxy():
    """Test that a global admin is authorized to access P&E proxy."""
    # Create a global admin user
    user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Generate a JWT token for the global admin
    token = create_jwt_token(user)

    # Make a GET request to the P&E proxy endpoint with the global admin's token
    response = client.get("/pe", headers={"Authorization": "Bearer {}".format(token)})

    # Assert that the global admin is authorized and receives either a 200 or 504 response
    assert response.status_code in [200, 504]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_global_view_user_authorized_to_access_pe_proxy():
    """Test that a global view user is authorized to access P&E proxy."""
    # Create a global view user
    user = User.objects.create(
        first_name="View",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Make a GET request to the P&E proxy endpoint with the global view user's token
    response = client.get(
        "/pe", headers={"Authorization": "Bearer " + create_jwt_token(user)}
    )
    LOGGER.info(response.json())
    # Assert that the global view user is authorized and receives either a 200 or 504 response
    assert response.status_code in [200, 504]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_not_authorized_to_access_matomo_proxy():
    """Test that a standard user is not authorized to access Matomo proxy."""
    # Create a standard user
    user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Generate a JWT token for the user
    token = create_jwt_token(user)

    # Make a GET request to the Matomo proxy endpoint with the user's token
    response = client.get(
        "/matomo", headers={"Authorization": "Bearer {}".format(token)}
    )

    # Assert that the user receives a 403 Unauthorized response
    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized"}

    @pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
    def test_global_admin_user_authorized_to_access_matomo_proxy():
        """Test that a global admin user is authorized to access Matomo proxy."""
        # Create a global admin user
        user = User.objects.create(
            first_name="Admin",
            last_name="User",
            email="{}@example.com".format(secrets.token_hex(4)),
            user_type=UserType.GLOBAL_VIEW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Generate a JWT token for the user
        token = create_jwt_token(user)

        # Make a GET request to the Matomo proxy endpoint with the user's token
        response = client.get(
            "/matomo", headers={"Authorization": "Bearer {}".format(token)}
        )

        LOGGER.info(response.json())
        # Assert that the global admin user is authorized and receives either a 200 or 504 response
        assert response.status_code in [200, 302, 308]
