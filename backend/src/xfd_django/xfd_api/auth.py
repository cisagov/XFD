"""Authentication utilities for the FastAPI application."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import logging
import re
from typing import Optional
import uuid

# Third-Party Libraries
from django.conf import settings
from django.forms.models import model_to_dict
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
import jwt
from xfd_mini_dl.models import (
    ApiKey,
    Notification,
    Organization,
    OrganizationTag,
    Role,
    User,
)

JWT_SECRET = settings.JWT_SECRET
SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_TIMEOUT_HOURS = settings.JWT_TIMEOUT_HOURS


LOGGER = logging.getLogger(__name__)

# User Types excluded from maintenance login blockers.
LOGIN_BLOCKED_EXCLUSIONS = ["globalAdmin", "regionalAdmin"]

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


def validate_json_serialization(user_object, label="user_object"):
    """Try to serialize an object to JSON. If it fails, identify which field caused it."""
    if user_object is None:
        raise ValueError("{} is None, cannot serialize".format(label))
    try:
        json.dumps(user_object)
    except TypeError as e:

        def traverse_data(user_data, path):
            if isinstance(user_data, dict):
                for key, value in user_data.items():
                    traverse_data(value, path + [str(key)])
            elif isinstance(user_data, list):
                for index, item in enumerate(user_data):
                    traverse_data(item, path + ["[{}]".format(index)])
            else:
                try:
                    json.dumps(user_data)
                except TypeError:
                    path_str = ".".join(path)
                    raise TypeError(
                        "{} contains unserializable value at `{}`".format(
                            label, path_str
                        )
                    )

        traverse_data(user_object, [])
        raise TypeError("{} failed JSON serialization: {}".format(label, e))


def user_to_dict(user):
    """Take a user model object from django and sanitize fields for output."""
    user_dict = model_to_dict(user)
    # Convert any UUID fields to strings
    for key, val in user_dict.items():
        if isinstance(val, uuid.UUID):
            user_dict[key] = str(val)
        elif isinstance(val, datetime):
            user_dict[key] = str(val)
    # Make sure maintenance checks are included in user response
    user_dict["login_blocked_by_maintenance"] = user.login_blocked_by_maintenance
    return user_dict


def create_jwt_token(user):
    """Create a JWT token for a given user."""
    payload = {
        "id": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=int(JWT_TIMEOUT_HOURS)),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_token_from_header(request: Request) -> Optional[str]:
    """Extract token from the Authorization header, allowing 'Bearer' or raw tokens."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        return auth_header  # Return the token directly if no 'Bearer ' prefix
    for name in ("token", "crossfeed-token"):
        request_token = request.cookies.get(name)
        if request_token and request_token not in ("null", "undefined", "None", ""):
            return request_token
    return None


def get_user_by_api_key(api_key: str):
    """Get a user by their API key."""
    hashed_key = sha256(api_key.encode()).hexdigest()
    try:
        api_key_instance = ApiKey.objects.get(hashed_key=hashed_key)
        api_key_instance.lastUsed = datetime.now(timezone.utc)
        api_key_instance.save(update_fields=["last_used"])
        return api_key_instance.user
    except ApiKey.DoesNotExist:
        LOGGER.warning("API Key not found")
        return None


# Endpoint Authorization Function
def get_current_active_user(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(get_token_from_header),
):
    """Ensure the current user is authenticated and active, supporting either API key or token."""
    user = None
    if api_key:
        user = get_user_by_api_key(api_key)
    elif token:
        # Check if token is an API key
        if re.match(r"^[A-Fa-f0-9]{32}$", token):
            user = get_user_by_api_key(token)
        else:
            try:
                # Decode token in Authorization header to get user
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("id")

                if user_id is None:
                    LOGGER.warning("No user ID found in token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                # Fetch the user by ID from the database
                user = User.objects.get(id=user_id)
            except jwt.ExpiredSignatureError:
                LOGGER.warning("Token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.InvalidTokenError:
                LOGGER.warning("Invalid token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication credentials provided",
        )

    if user is None:
        LOGGER.warning("User not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    if user.invite_pending:
        LOGGER.warning("User is not active or approved")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized",
        )
    # Attach the user info
    request.state.user = user
    # Attach email to request state for logging
    request.state.user_email = user.email
    return user


def get_current_active_user_unsafe(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(get_token_from_header),
):
    """
    Ensure the current user is authenticated and active, does not perform invite_pending check.

    This function is UNSAFE and should not be used for sensitive operations.

    It is intended for scenarios where the user is known to be unapproved and where the endpoints are not sensitive.
    """
    user = None
    if api_key:
        user = get_user_by_api_key(api_key)
    elif token:
        # Check if token is an API key
        if re.match(r"^[A-Fa-f0-9]{32}$", token):
            user = get_user_by_api_key(token)
        else:
            try:
                # Decode token in Authorization header to get user
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("id")

                if user_id is None:
                    LOGGER.warning("No user ID found in token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                # Fetch the user by ID from the database
                user = User.objects.get(id=user_id)
            except jwt.ExpiredSignatureError:
                LOGGER.warning("Token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.InvalidTokenError:
                LOGGER.warning("Invalid token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication credentials provided",
        )

    if user is None:
        LOGGER.warning("User not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Attach email to request state for logging
    request.state.user_email = user.email
    return user


def update_login_block_status(user: User) -> None:
    """Set user's login_blocked_by_maintenance based on active maintenance window."""
    # Get current time (UTC) TODO: Check notifications TZ and confirm UTC on save.
    now = datetime.now(timezone.utc)

    # Check for active notifications using current time.
    active_maintenance = Notification.objects.filter(
        start_datetime__lte=now,
        end_datetime__gte=now,
        maintenance_type="major",
        status="active",
        # message="waiting_room"  # uncomment if filtering by message later
    ).exists()

    # Only block users who are NOT in LOGIN_BLOCKED_EXCLUSIONS
    user.login_blocked_by_maintenance = (
        active_maintenance and user.user_type not in LOGIN_BLOCKED_EXCLUSIONS
    )
    user.save()


def is_global_write_admin(current_user) -> bool:
    """Check if the user has global write admin permissions."""
    return current_user and current_user.user_type == "globalAdmin"


def is_global_view_admin(current_user) -> bool:
    """Check if the user has global view permissions."""
    return current_user and current_user.user_type in ["globalView", "globalAdmin"]


def is_regional_admin(current_user) -> bool:
    """Check if the user has regional admin permissions."""
    return current_user and current_user.user_type in ["regionalAdmin", "globalAdmin"]


def is_org_admin(current_user, organization_id) -> bool:
    """Check if the user is an admin of the given organization."""
    if not organization_id:
        return False

    # Check if the user has an admin role in the given organization
    for role in current_user.roles.all():
        if str(role.organization.id) == str(organization_id) and role.role == "admin":
            return True

    # If the user is a global write admin, they are considered an org admin
    return is_global_write_admin(current_user)


def is_regional_admin_for_organization(current_user, organization_id) -> bool:
    """Check if user is a regional admin and if a selected organization belongs to their region."""
    if not organization_id:
        return False

    # Check if the user is a regional admin
    if is_regional_admin(current_user):
        # Check if the organization belongs to the user's region
        user_region_id = (
            current_user.region_id
        )  # Assuming this is available in the user object
        organization_region_id = get_organization_region(
            organization_id
        )  # Function to fetch the organization's region
        return user_region_id == organization_region_id

    return False


def can_access_user(current_user, target_user_id) -> bool:
    """Check if current user is allowed to modify.the target user."""
    if not target_user_id:
        return False

    # Check if the current user is the target user or a global write admin
    if (
        str(current_user.id) == str(target_user_id)
        or is_global_write_admin(current_user)
        or is_regional_admin(current_user)
    ):
        return True

    return False


def get_allowed_user_update_fields(current_user, target_user):
    """Get allowed user update fields."""
    if is_global_write_admin(current_user):
        return {
            "first_name",
            "last_name",
            "state",
            "region_id",
            "user_type",
            "invite_pending",
            "date_approved",
            "approved_by",
            "accepted_terms_version",
            "login_blocked_by_maintenance",
            "first_login",
        }

    if is_regional_admin(current_user):
        return {
            "first_name",
            "last_name",
            "state",
            "region_id",
            "invite_pending",
            "first_login",
            "date_approved",
            "approved_by",
        }

    # Self-updates:
    if current_user.id == target_user.id:
        allowed = {"first_login"}  # allow the user to dismiss their own first_login
        if (
            (
                current_user.can_select_own_state is True
                and current_user.invite_pending is True
            )
            or current_user.state is None
            or current_user.state == ""
        ):
            allowed.add("state")
        return allowed

    return set()


def get_org_memberships(current_user) -> list[str]:
    """Return the organization IDs that a user is a member of."""
    # Check if the user has a 'roles' attribute and it's not None

    roles = Role.objects.filter(user=current_user)
    return [role.organization.id for role in roles if role.organization]


def get_organization_region(organization_id: str) -> str:
    """Fetch the region ID for the given organization."""
    organization = Organization.objects.get(id=organization_id)
    return organization.region_id


def get_tag_organizations(current_user, tag_id) -> list[str]:
    """Return the organizations belonging to a tag, if the user can access the tag."""
    # Check if the user is a global view admin
    if not is_global_view_admin(current_user):
        return []

    # Fetch the OrganizationTag and its related organizations
    tag = (
        OrganizationTag.objects.prefetch_related("organizations")
        .filter(id=tag_id)
        .first()
    )
    if tag:
        # Return a list of organization IDs
        return [org.id for org in tag.organizations.all()]

    # Return an empty list if tag is not found
    return []


def matches_user_region(current_user, user_region_id: str) -> bool:
    """Check if the current user's region matches the user's region being modified."""
    # Check if the current user is a global admin (can match any region)
    if is_global_write_admin(current_user):
        return True

    # Ensure the user has a region associated with them
    if not current_user.region_id or not user_region_id:
        return False

    # Compare the region IDs
    return user_region_id == current_user.region_id


def get_stats_org_ids(current_user, filters):
    """Get organization ids that a user has access to for the stats."""
    # Extract filters from the Pydantic model
    regions_filter = filters.filters.regions if filters and filters.filters else []
    organizations_filter = (
        filters.filters.organizations if filters and filters.filters else []
    )
    if organizations_filter == [""]:
        organizations_filter = []
    tags_filter = filters.filters.tags if filters and filters.filters else []

    # Final list of organization IDs
    organization_ids = set()

    # Case 1: Explicit organization IDs in filters
    if organizations_filter:
        # Check user type restrictions for provided organization IDs
        for org_id in organizations_filter:
            if (
                is_global_view_admin(current_user)
                or (is_regional_admin_for_organization(current_user, org_id))
                or (is_org_admin(current_user, org_id))
                or (get_org_memberships(current_user))
            ):
                organization_ids.add(org_id)

        if not organization_ids:
            raise HTTPException(
                status_code=403,
                detail="User does not have access to the specified organizations.",
            )

    # Case 2: Global view admin (if no explicit organization filter)
    elif is_global_view_admin(current_user):
        # Get organizations by region
        if regions_filter:
            organizations_by_region = Organization.objects.filter(
                region_id__in=regions_filter
            ).values_list("id", flat=True)
            organization_ids.update(organizations_by_region)

        # Get organizations by tag
        for tag_id in tags_filter:
            organizations_by_tag = get_tag_organizations(current_user, tag_id)
            organization_ids.update(organizations_by_tag)

    # Case 3: Regional admin
    elif current_user.user_type in ["regionalAdmin"]:
        user_region_id = current_user.region_id

        # Allow only organizations in the user's region
        organizations_in_region = Organization.objects.filter(
            region_id=user_region_id
        ).values_list("id", flat=True)
        organization_ids.update(organizations_in_region)

        # Apply filters within the user's region
        if regions_filter and user_region_id in regions_filter:
            organization_ids.update(organizations_in_region)

        # Include organizations by tag within the same region
        for tag_id in tags_filter:
            tag_organizations = get_tag_organizations(current_user, tag_id)
            regional_tag_organizations = [
                org_id
                for org_id in tag_organizations
                if get_organization_region(org_id) == user_region_id
            ]
            organization_ids.update(regional_tag_organizations)

    # Case 4: Standard user
    else:
        # Allow only organizations where the user is a member
        user_organization_ids = current_user.roles.values_list(
            "organization_id", flat=True
        )
        organization_ids.update(user_organization_ids)

    return organization_ids
