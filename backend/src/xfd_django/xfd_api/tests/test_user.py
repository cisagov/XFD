"""Test user."""
# Standard Python Libraries
from datetime import datetime
import logging
import secrets
from unittest.mock import patch
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import ApiKey, Organization, Role, User, UserType

client = TestClient(app)

LOGGER = logging.getLogger(__name__)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_by_regular_user_should_not_work():
    """Invite by a regular user should not work."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign standard user role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="user",
    )

    response = client.post(
        "/users",
        json={
            "first_name": "first name",
            "last_name": "last name",
            "email": "{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_by_global_admin_should_work():
    """Invite by a global admin should work."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    response = client.post(
        "/users",
        json={"first_name": "first name", "last_name": "last name", "email": email},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["invite_pending"] is True
    assert data["first_name"] == "first name"
    assert data["last_name"] == "last name"
    assert data["roles"] == []
    assert data["user_type"] == UserType.STANDARD


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_by_global_admin_with_user_type_setting():
    """Invite by a global admin should work if setting user type."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    response = client.post(
        "/users",
        json={
            "first_name": "first name",
            "last_name": "last name",
            "email": email,
            "user_type": UserType.GLOBAL_ADMIN,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["invite_pending"] is True
    assert data["first_name"] == "first name"
    assert data["last_name"] == "last name"
    assert data["roles"] == []
    assert data["user_type"] == UserType.GLOBAL_ADMIN


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_by_global_view_should_not_work():
    """Invite by a global view should not work."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    response = client.post(
        "/users",
        json={
            "first_name": "first name",
            "last_name": "last name",
            "email": "{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    LOGGER.info(response.json())
    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_by_organization_admin_should_work():
    """Invite by an organization admin should work."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    LOGGER.info("here")
    response = client.post(
        "/users",
        json={
            "first_name": "first name",
            "last_name": "last name",
            "email": email,
            "organization": "{}".format(organization.id),
            "organization_admin": False,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["invite_pending"] is True
    assert data["first_name"] == "first name"
    assert data["last_name"] == "last name"
    assert data["roles"][0]["approved"] is True
    assert data["roles"][0]["role"] == "user"
    assert data["roles"][0]["organization"]["id"] == str(organization.id)


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_by_organization_admin_should_not_work_if_setting_user_type():
    """Invite by an organization admin should not work if setting user type."""
    user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
    )

    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    response = client.post(
        "/users",
        json={
            "first_name": "first name",
            "last_name": "last name",
            "email": email,
            "organization": "{}".format(organization.id),
            "organization_admin": False,
            "user_type": UserType.GLOBAL_ADMIN,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_existing_user_by_different_org_admin_should_not_modify_other_user_details():
    """Invite existing user by a different organization admin should work, and should not modify other user details."""
    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    organization2 = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    user = User.objects.create(
        first_name="first name", last_name="last name", email=email
    )
    Role.objects.create(
        role="user", approved=False, organization=organization, user=user
    )

    user2 = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user2,
        organization=organization2,
        role="admin",
    )

    response = client.post(
        "/users",
        json={
            "first_name": "new first name",
            "last_name": "new last name",
            "email": email,
            "organization": "{}".format(organization2.id),
            "organization_admin": False,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user2))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == email
    assert data["invite_pending"] is False
    assert data["first_name"] == "first name"
    assert data["last_name"] == "last name"
    role_for_org2 = [
        role
        for role in data["roles"]
        if role["organization"]["id"] == str(organization2.id)
    ]
    assert role_for_org2, "No role found for organization {}".format(organization2.id)
    assert role_for_org2[0]["approved"] is True
    assert role_for_org2[0]["role"] == "user"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_existing_user_by_different_org_admin_should_modify_user_name_if_initially_blank():
    """Invite existing user by a different organization admin should modify user name if user name is initially blank."""
    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    organization2 = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    user = User.objects.create(first_name="", last_name="", email=email)
    Role.objects.create(
        role="user", approved=False, organization=organization, user=user
    )

    user2 = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user2,
        organization=organization2,
        role="admin",
    )

    response = client.post(
        "/users",
        json={
            "first_name": "new first name",
            "last_name": "new last name",
            "email": email,
            "organization": "{}".format(organization2.id),
            "organization_admin": False,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user2))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == email
    assert data["invite_pending"] is False
    assert data["first_name"] == "new first name"
    assert data["last_name"] == "new last name"
    role_for_org2 = [
        role
        for role in data["roles"]
        if role["organization"]["id"] == str(organization2.id)
    ]
    assert role_for_org2, "No role found for organization {}".format(organization2.id)
    assert role_for_org2[0]["approved"] is True
    assert role_for_org2[0]["role"] == "user"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_existing_user_by_same_org_admin_should_update_user_org_role():
    """Invite existing user by same organization admin should work, and should update the user organization role."""
    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    admin_user = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
    )
    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    user = User.objects.create(first_name="first", last_name="last", email=email)
    Role.objects.create(
        role="user",
        approved=False,
        organization=organization,
        user=user,
        created_by=admin_user,
        approved_by=admin_user,
    )

    user2 = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Assign admin role to the user for the organization
    Role.objects.create(
        user=user2,
        organization=organization,
        role="admin",
    )

    response = client.post(
        "/users",
        json={
            "first_name": "first",
            "last_name": "last",
            "email": email,
            "organization": "{}".format(organization.id),
            "organization_admin": True,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user2))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == email
    assert data["invite_pending"] is False
    assert data["first_name"] == "first"
    assert data["last_name"] == "last"
    assert data["roles"][0]["approved"] is True
    assert data["roles"][0]["role"] == "admin"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_existing_user_by_global_admin_should_update_user_type():
    """Invite existing user by global admin that updates user type should work."""
    User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
    )
    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    user = User.objects.create(first_name="first", last_name="last", email=email)

    user2 = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/users",
        json={
            "first_name": "first",
            "last_name": "last",
            "email": email,
            "user_type": UserType.GLOBAL_ADMIN,
        },
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user2))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == email
    assert data["invite_pending"] is False
    assert data["first_name"] == "first"
    assert data["last_name"] == "last"
    assert data["roles"] == []
    assert data["user_type"] == UserType.GLOBAL_ADMIN


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_invite_existing_user_by_global_view_should_not_work():
    """Invite existing user by global view should not work."""
    User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
    )
    email = "{}@crossfeed.cisa.gov".format(secrets.token_hex(4))
    User.objects.create(first_name="first", last_name="last", email=email)

    user2 = User.objects.create(
        first_name="first",
        last_name="last",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/users",
        json={"first_name": "first", "last_name": "last", "email": email},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user2))},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Unauthorized access."}


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.api_methods.user.send_registration_approved_email")
def test_register_approve_success(mock_email):
    """Test successful user registration approval."""
    mock_email.return_value = "test"
    current_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        region_id="region-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=False,
        date_accepted_terms=datetime.now(),
    )
    user_to_approve = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        region_id="region-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    # Mock email sending
    response = client.put(
        "/users/{}/register/approve".format(user_to_approve.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(current_user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["body"] == "User registration approved."
    mock_email.assert_called_once_with(
        user_to_approve.email,
        subject="CISA CyHy Dashboard Account Approved",
        first_name=user_to_approve.first_name,
        last_name=user_to_approve.last_name,
        template="crossfeed_approval_notification.html",
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_register_approve_unauthorized_region():
    """Test approval with unauthorized region access."""
    current_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=False,
        date_accepted_terms=datetime.now(),
    )
    user_to_approve = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        region_id="2",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.put(
        "/users/{}/register/approve".format(user_to_approve.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(current_user))},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized region access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.api_methods.user.send_registration_denied_email")
def test_register_deny_success(mock_denied_email):
    """Test successful user registration denial."""
    mock_denied_email.return_value = "test"
    current_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=False,
        date_accepted_terms=datetime.now(),
    )
    user_to_deny = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    response = client.put(
        "/users/{}/register/deny".format(user_to_deny.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(current_user))},
    )

    assert response.status_code == 200
    assert response.json()["body"] == "User registration denied."
    mock_denied_email.assert_called_once_with(
        user_to_deny.email,
        subject="CyHy Dashboard Registration Denied",
        first_name=user_to_deny.first_name,
        last_name=user_to_deny.last_name,
        template="crossfeed_denial_notification.html",
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_register_deny_unauthorized_region():
    """Test registration denial with unauthorized region access."""
    current_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@crossfeed.cisa.gov".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=False,
        date_accepted_terms=datetime.now(),
    )
    user_to_deny = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        region_id="2",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.put(
        "/users/{}/register/deny".format(user_to_deny.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(current_user))},
    )

    LOGGER.info(response.json())
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized region access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_accept_terms_success():
    """Test that a user can successfully accept the latest terms of service."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=True,
    )

    version = "1.0"

    response = client.post(
        "/users/me/acceptTerms",
        json={"version": version},
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(user.id)
    assert data["accepted_terms_version"] == version
    assert data["date_accepted_terms"] is not None


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_accept_terms_missing_version():
    """Test that missing version in request body returns a 400 error."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.post(
        "/users/me/acceptTerms",
        json={},  # No version provided
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 422


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_accept_terms_no_auth():
    """Test that an unauthenticated request returns 401."""
    response = client.post(
        "/users/me/acceptTerms",
        json={"version": "1.0"},
    )

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_user_as_admin():
    """Test that a global admin can successfully delete a user."""
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    target_user = User.objects.create(
        first_name="Target",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.delete(
        "/users/{}".format(target_user.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()[
        "message"
    ] == "User {} and associated roles have been deleted successfully.".format(
        target_user.id
    )

    # Ensure the user is deleted from the database
    assert not User.objects.filter(id=target_user.id).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_user_as_standard_user_fails():
    """Test that a standard user cannot delete another user."""
    user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    target_user = User.objects.create(
        first_name="Target",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.delete(
        "/users/{}".format(target_user.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."

    # Ensure the user still exists
    assert User.objects.filter(id=target_user.id).exists()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_nonexistent_user():
    """Test that deleting a nonexistent user returns 404."""
    admin_user = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    fake_user_id = uuid.uuid4()

    response = client.delete(
        "/users/{}".format(fake_user_id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin_user))},
    )

    assert response.status_code == 404


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_user_no_auth():
    """Test that an unauthenticated request returns 401."""
    target_user = User.objects.create(
        first_name="Target",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.delete("/users/{}".format(target_user.id))

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_as_global_admin():
    """Test that a global admin can retrieve all users."""
    global_admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user1 = User.objects.create(
        first_name="Test",
        last_name="User1",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user2 = User.objects.create(
        first_name="Test",
        last_name="User2",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(global_admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # Should at least return the created users
    returned_user_ids = {user["id"] for user in data}
    assert str(user1.id) in returned_user_ids
    assert str(user2.id) in returned_user_ids


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_as_standard_user_fails():
    """Test that a standard user cannot retrieve all users."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_no_auth():
    """Test that an unauthenticated request returns 401."""
    response = client.get("/users")

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_with_roles():
    """Test that users and their roles are correctly returned."""
    global_admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="member",
        approved=True,
    )

    response = client.get(
        "/users",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(global_admin))},
    )

    assert response.status_code == 200
    data = response.json()
    found_user = next((u for u in data if u["id"] == str(user.id)), None)
    assert found_user is not None
    assert len(found_user["roles"]) == 1
    assert found_user["roles"][0]["organization"]["id"] == str(organization.id)
    assert found_user["roles"][0]["role"] == "member"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_region_id_as_regional_admin():
    """Test that a regional admin can retrieve users by region ID."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user1 = User.objects.create(
        first_name="Test",
        last_name="User1",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user2 = User.objects.create(
        first_name="Test",
        last_name="User2",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/region_id/1",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )
    LOGGER.info(response.json())

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    returned_user_ids = {user["id"] for user in data}
    assert str(user1.id) in returned_user_ids
    assert str(user2.id) in returned_user_ids


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_region_id_as_standard_user_fails():
    """Test that a standard user cannot retrieve users by region ID."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="R1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/region_id/R1",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_region_id_no_auth():
    """Test that an unauthenticated request returns 401."""
    response = client.get("/users/region_id/R1")

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_region_id_not_found():
    """Test that retrieving users for a non-existent region returns 404."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="R1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/region_id/R999",  # Non-existent region
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No users found for the specified region_id"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_state_as_regional_admin():
    """Test that a regional admin can retrieve users by state."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        state="CA",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user1 = User.objects.create(
        first_name="Test",
        last_name="User1",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user2 = User.objects.create(
        first_name="Test",
        last_name="User2",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/state/CA",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    returned_user_ids = {user["id"] for user in data}
    assert str(user1.id) in returned_user_ids
    assert str(user2.id) in returned_user_ids


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_state_as_standard_user_fails():
    """Test that a standard user cannot retrieve users by state."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/state/CA",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_state_no_auth():
    """Test that an unauthenticated request returns 401."""
    response = client.get("/users/state/CA")

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_by_state_not_found():
    """Test that retrieving users for a non-existent state returns 404."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        state="CA",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/state/ZZ",  # Non-existent state
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "No users found for the specified state"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_v2_as_regional_admin():
    """Test that a regional admin can retrieve users with filters."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        state="CA",
        region_id="R1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user1 = User.objects.create(
        first_name="User1",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        region_id="R1",
        invite_pending=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    User.objects.create(
        first_name="User2",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        region_id="R1",
        invite_pending=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/v2/users?state=CA&region_id=R1&invite_pending=False",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[1]["id"] == str(user1.id)
    assert data[0]["state"] == "CA"
    assert data[0]["region_id"] == "R1"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_v2_as_standard_user_fails():
    """Test that a standard user cannot retrieve users with filters."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        region_id="R1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/v2/users?state=CA",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_v2_no_auth():
    """Test that an unauthenticated request returns 401."""
    response = client.get("/v2/users?state=CA")

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_v2_no_filters():
    """Test that a regional admin can retrieve users without filters."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    User.objects.create(
        first_name="User1",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        region_id="R1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    User.objects.create(
        first_name="User2",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="TX",
        region_id="R2",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/v2/users",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_users_v2_empty_results():
    """Test that a valid request with no matching users returns an empty list."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/v2/users?state=ZZ",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_as_global_admin():
    """Test that a global admin can update user details."""
    global_admin = User.objects.create(
        first_name="Admin",
        last_name="Global",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user = User.objects.create(
        first_name="User",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        state="CA",
        region_id="R1",
        invite_pending=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"first_name": "Updated", "last_name": "User"}

    response = client.put(
        "/v2/users/{}".format(user.id),
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(global_admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "User"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_as_standard_user_fails():
    """Test that a standard user cannot update another user's details."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    target_user = User.objects.create(
        first_name="Target",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"first_name": "Hacked", "last_name": "User"}

    response = client.put(
        "/v2/users/{}".format(target_user.id),
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_no_auth():
    """Test that an unauthenticated request returns 401."""
    user = User.objects.create(
        first_name="User",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"first_name": "Anonymous"}

    response = client.put("/v2/users/{}".format(user.id), json=payload)

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_non_existent_user():
    """Test that updating a non-existent user returns a 404."""
    global_admin = User.objects.create(
        first_name="Admin",
        last_name="Global",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    fake_user_id = "00000000-0000-0000-0000-000000000000"

    payload = {"first_name": "DoesNotExist"}

    response = client.put(
        "/v2/users/{}".format(fake_user_id),
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(global_admin))},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_update_userType_by_non_admin_fails():
    """Test that only a global admin can update userType."""
    regional_admin = User.objects.create(
        first_name="Admin",
        last_name="Regional",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user = User.objects.create(
        first_name="User",
        last_name="Test",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    payload = {"user_type": UserType.GLOBAL_ADMIN}

    response = client.put(
        "/v2/users/{}".format(user.id),
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(regional_admin))},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only global admins can update userType."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_standard_user_cannot_update_own_email():
    """Test update user v2 standard user."""
    user = User.objects.create(
        first_name="Self",
        last_name="User",
        email="original@example.com",
        user_type=UserType.STANDARD,
    )

    payload = {"email": "hacked@example.com"}

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )

    assert response.status_code == 403
    assert "email" in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_standard_user_cannot_approve_themselves():
    """Test update user v2 standard user."""
    user = User.objects.create(
        first_name="Self",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
    )

    payload = {
        "date_approved": datetime.now().isoformat(),
        "approved_by": None,
    }

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )

    assert response.status_code == 403
    assert "date_approved" in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_regional_admin_cannot_update_user_type():
    """Test update user v2 standard user."""
    regional_admin = User.objects.create(
        first_name="RA",
        last_name="Admin",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="X1",
    )
    user = User.objects.create(
        first_name="Target",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="X1",
    )

    payload = {"user_type": UserType.GLOBAL_ADMIN}

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(regional_admin)}"},
    )

    assert response.status_code == 403
    assert "Only global admins can update userType." in response.json()["detail"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_regional_admin_cannot_update_in_region_state():
    """Test update user v2 standard user."""
    regional_admin = User.objects.create(
        first_name="RA",
        last_name="Admin",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="X1",
    )
    user = User.objects.create(
        first_name="Target",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="X1",
    )

    payload = {"state": "NY"}

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(regional_admin)}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_user_v2_standard_user_cannot_update_name():
    """Test update user v2 standard user."""
    user = User.objects.create(
        first_name="Old",
        last_name="Name",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
    )

    payload = {"first_name": "New", "last_name": "Name"}

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )

    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_cannot_clear_invite_pending():
    """Standard user should not be able to set invite_pending to false on themselves."""
    user = User.objects.create(
        first_name="Self",
        last_name="Invitee",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        invite_pending=True,
    )

    payload = {"invite_pending": False}

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Unauthorized to update the following fields: invite_pending"
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_cannot_self_approve():
    """Standard user should not be able to set 'approved' field via API."""
    user = User.objects.create(
        first_name="Self",
        last_name="Approver",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        invite_pending=True,
    )

    # 'approved' isn't a direct field, but we simulate by trying to set date_approved
    payload = {"date_approved": datetime.now().isoformat()}

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": f"Bearer {create_jwt_token(user)}"},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Unauthorized to update the following fields: date_approved"
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_me_success():
    """Test that an authenticated user can retrieve their own user data."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["user_type"] == user.user_type


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_me_with_roles():
    """Test that a user with roles retrieves their associated organizations."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    organization = Organization.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        root_domains=["test-" + secrets.token_hex(4)],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    Role.objects.create(
        user=user,
        organization=organization,
        role="admin",
        approved=True,
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["roles"]) == 1
    assert data["roles"][0]["role"] == "admin"
    assert data["roles"][0]["organization"]["id"] == str(organization.id)
    assert data["roles"][0]["organization"]["name"] == organization.name


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_me_with_api_keys():
    """Test that a user retrieves their associated API keys."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    api_key = ApiKey.objects.create(
        user=user,
        hashed_key="fakehashedkey",
        last_four="1234",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["api_keys"]) == 1
    assert data["api_keys"][0]["id"] == str(api_key.id)
    assert data["api_keys"][0]["last_four"] == "1234"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_me_unauthenticated():
    """Test that an unauthenticated request returns a 401 error."""
    response = client.get("/users/me")

    assert response.status_code == 401


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_updates_self_user_type_unauthenticated():
    """Test that a standard user cannot update their own userType."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    payload = {
        "user_type": UserType.STANDARD,
    }
    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Only global admins can update userType."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_updates_self_unauthenticated():
    """Test that a standard user cannot update their own details."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    payload = {
        "first_name": "Updated",
        "last_name": "User",
        "email": "adasdasdadsss@example.com",
        "approved": True,
        "invite_pending": False,
        "region_id": "11",
        "state": "CA",
    }
    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )
    assert response.status_code == 403


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_standard_user_updates_other_unauthenticated():
    """Test that a standard user cannot update another user's details."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        first_login=True,
    )
    user_to_update = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        first_login=True,
    )
    payload = {}
    response = client.put(
        f"/v2/users/{user_to_update.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized access."


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_regional_user_updates_self_confirm_authorized_fields():
    """Test that a regional admin can update their own user details."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=False,
    )

    payload = {
        "first_name": "Updated",
        "last_name": "New",
        "invite_pending": False,
        "date_approved": datetime.now().isoformat(),
        "approved_by": None,
        "first_login": False,
    }

    response = client.put(
        f"/v2/users/{user.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )
    LOGGER.info(response.json())
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert response.json()["last_name"] == "New"
    assert response.json()["approved_by"] is None
    assert response.json()["first_login"] is False


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_regional_user_updates_other_confirm_authorized_fields():
    """Test that a regional admin can update another user's details."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.REGIONAL_ADMIN,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=False,
    )

    user_to_update = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        invite_pending=True,
    )
    payload = {
        "first_name": "Updated",
        "last_name": "New",
        "invite_pending": False,
        "date_approved": datetime.now().isoformat(),
        "approved_by": None,
    }
    response = client.put(
        f"/v2/users/{user_to_update.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert response.json()["last_name"] == "New"
    assert response.json()["date_approved"] is None


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_global_user_updates_confirm_authorized_fields():
    """Test that a global admin can update another user's details."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user_to_update = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        login_blocked_by_maintenance=True,
    )
    payload = {
        "region_id": "2",
        "state": "NY",
        "first_name": "Updated",
        "last_name": "New",
        "user_type": UserType.REGIONAL_ADMIN,
        "date_approved": datetime.now().isoformat(),
        "accepted_terms_version": "1.0",
        "login_blocked_by_maintenance": False,
    }
    response = client.put(
        f"/v2/users/{user_to_update.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_global_user_updates_confirm_unauthorized_fields():
    """Test that a global admin cannot update unauthorized fields."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    user_to_update = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        region_id="1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        login_blocked_by_maintenance=True,
    )
    payload = {"email": "{}@example.com".format(secrets.token_hex(4))}
    response = client.put(
        f"/v2/users/{user_to_update.id}",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )
    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Unauthorized to update the following fields: email"
    )
