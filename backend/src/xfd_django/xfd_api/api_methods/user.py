"""User API."""

# Standard Python Libraries
from datetime import datetime
import logging
import os

# Third-Party Libraries
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.forms import model_to_dict
from fastapi import HTTPException, status
from xfd_mini_dl.models import Organization, Role, User, UserType

from ..auth import (
    can_access_user,
    get_allowed_user_update_fields,
    is_global_view_admin,
    is_global_write_admin,
    is_org_admin,
    is_regional_admin,
    matches_user_region,
)
from ..helpers.email import (
    send_invite_email,
    send_registration_approved_email,
    send_registration_denied_email,
)
from ..helpers.regionStateMap import REGION_STATE_MAP
from ..helpers.uuid_helpers import is_valid_uuid
from ..tools.serializers import serialize_user

# Configure logging
LOGGER = logging.getLogger(__name__)


# GET: /users/me
def get_me(current_user):
    """Get current user."""
    try:
        # Fetch the user and related objects from the database
        user = User.objects.prefetch_related(
            Prefetch("roles", queryset=Role.objects.select_related("organization")),
            Prefetch("api_keys"),
        ).get(id=str(current_user.id))

        # Convert the user object to a dictionary
        user_dict = model_to_dict(user)

        # Add id: model_to_dict does not automatically include
        user_dict["id"] = str(user.id)

        # Include roles with their related organization
        user_dict["roles"] = [
            {
                "id": role.id,
                "role": role.role,
                "approved": role.approved,
                "organization": (
                    {
                        **model_to_dict(
                            role.organization,
                            fields=[
                                "acronym",
                                "name",
                                "root_domains",
                                "ip_blocks",
                                "is_passive",
                                "pending_domains",
                                "country",
                                "state",
                                "region_id",
                                "state_fips",
                                "state_name",
                                "county",
                                "county_fips",
                                "type",
                                "parent",
                                "created_by",
                            ],
                        ),
                        "id": str(role.organization.id),  # Explicitly add the ID
                    }
                    if role.organization
                    else None
                ),
            }
            for role in user.roles.all()
        ]

        # Include API keys
        user_dict["api_keys"] = list(
            user.api_keys.values(
                "id", "created_at", "updated_at", "last_used", "hashed_key", "last_four"
            )
        )

        return user_dict

    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")

    except Exception as e:
        LOGGER.exception("Unhandled error occurred: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /users/me/acceptTerms
def accept_terms(version_data, current_user):
    """Accept the latest terms of service."""
    try:
        version = version_data.version
        if not version:
            raise HTTPException(
                status_code=400, detail="Missing version in request body."
            )

        current_user.date_accepted_terms = datetime.now()
        current_user.accepted_terms_version = version
        current_user.save()

        return {
            "id": str(current_user.id),
            "cognito_id": current_user.cognito_id,
            "okta_id": current_user.okta_id,
            "login_gov_id": current_user.login_gov_id,
            "created_at": (
                current_user.created_at.isoformat() if current_user.created_at else None
            ),
            "updated_at": (
                current_user.updated_at.isoformat() if current_user.updated_at else None
            ),
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "invite_pending": current_user.invite_pending,
            "login_blocked_by_maintenance": current_user.login_blocked_by_maintenance,
            "date_accepted_terms": (
                current_user.date_accepted_terms.isoformat()
                if current_user.date_accepted_terms
                else None
            ),
            "accepted_terms_version": current_user.accepted_terms_version,
            "last_logged_in": (
                current_user.last_logged_in.isoformat()
                if current_user.last_logged_in
                else None
            ),
            "user_type": current_user.user_type,
            "region_id": current_user.region_id,
            "state": current_user.state,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# DELETE: /users/{user_id}
def delete_user(target_user_id, current_user):
    """Delete a user by ID."""
    # Validate that the user ID is a valid UUID
    if not target_user_id or not is_valid_uuid(target_user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the current user has permission to access/update this user
    if not can_access_user(current_user, target_user_id):
        raise HTTPException(status_code=403, detail="Unauthorized access.")

    try:
        # Fetch the user to be deleted
        target_user = User.objects.prefetch_related("roles").get(id=target_user_id)

        # Delete all associated roles before deleting the user
        target_user.roles.all().delete()

        # Delete the user
        target_user.delete()

        # Return success response
        return {
            "status": "success",
            "message": f"User {target_user_id} and associated roles have been deleted successfully.",
            "user_deleted": serialize_user(target_user),
        }

    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting user: {str(e)}")


# GET: /users
def get_users(current_user):
    """Retrieve a list of users, restricted by admin type."""
    try:
        if is_global_view_admin(current_user):
            users = User.objects.all().prefetch_related("roles__organization")
        elif is_regional_admin(current_user):
            users = User.objects.filter(
                region_id=current_user.region_id
            ).prefetch_related("roles__organization")
        else:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return [
            {
                "id": str(user.id),
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name,
                "email": user.email,
                "region_id": user.region_id,
                "state": user.state,
                "user_type": user.user_type,
                "last_logged_in": user.last_logged_in,
                "date_approved": user.date_approved,
                "approved_by": (
                    {
                        "id": str(user.approved_by.id),
                        "full_name": str(user.approved_by.full_name),
                        "email": str(user.approved_by.email),
                    }
                    if user.approved_by
                    else None
                ),
                "accepted_terms_version": user.accepted_terms_version,
                "date_accepted_terms": user.date_accepted_terms,
                "roles": [
                    {
                        "id": str(role.id),
                        "approved": role.approved,
                        "role": role.role,
                        "organization": (
                            {
                                "id": str(role.organization.id),
                                "name": role.organization.name,
                            }
                            if role.organization
                            else None
                        ),
                    }
                    for role in user.roles.all()
                ],
            }
            for user in users
        ]
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET: /users/region_id/{region_id}
def get_users_by_region_id(region_id, current_user):
    """List users with specific region_id."""
    try:
        if not is_regional_admin(current_user):
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not region_id:
            raise HTTPException(
                status_code=400, detail="Missing region_id in path parameters"
            )

        users = User.objects.filter(region_id=region_id).prefetch_related(
            "roles__organization"
        )
        if users:
            return [
                {
                    "id": str(user.id),
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.full_name,
                    "email": user.email,
                    "region_id": user.region_id,
                    "state": user.state,
                    "user_type": user.user_type,
                    "last_logged_in": user.last_logged_in,
                    "accepted_terms_version": user.accepted_terms_version,
                    "roles": [
                        {
                            "id": str(role.id),
                            "approved": role.approved,
                            "role": role.role,
                            "organization": (
                                {
                                    "id": str(role.organization.id),
                                    "name": role.organization.name,
                                }
                                if role.organization
                                else None
                            ),
                        }
                        for role in user.roles.all()
                    ],
                }
                for user in users
            ]
        else:
            raise HTTPException(
                status_code=404, detail="No users found for the specified region_id"
            )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception("Unhandled error occurred: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# GET: /users/state/{state}
def get_users_by_state(state, current_user):
    """List users with specific state."""
    try:
        if not is_regional_admin(current_user):
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not state:
            raise HTTPException(
                status_code=400, detail="Missing state in path parameters"
            )

        users = User.objects.filter(state=state).prefetch_related("roles__organization")
        if users:
            return [
                {
                    "id": str(user.id),
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.full_name,
                    "email": user.email,
                    "region_id": user.region_id,
                    "state": user.state,
                    "user_type": user.user_type,
                    "last_logged_in": user.last_logged_in,
                    "accepted_terms_version": user.accepted_terms_version,
                    "roles": [
                        {
                            "id": str(role.id),
                            "approved": role.approved,
                            "role": role.role,
                            "organization": (
                                {
                                    "id": str(role.organization.id),
                                    "name": role.organization.name,
                                }
                                if role.organization
                                else None
                            ),
                        }
                        for role in user.roles.all()
                    ],
                }
                for user in users
            ]
        else:
            raise HTTPException(
                status_code=404, detail="No users found for the specified state"
            )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# GET: /v2/users
def get_users_v2(state, region_id, invite_pending, current_user):
    """Retrieve a list of users based on optional filter parameters."""
    try:
        # Check if user is a regional admin or global admin
        if not (is_regional_admin(current_user) or is_global_view_admin(current_user)):
            raise HTTPException(status_code=401, detail="Unauthorized")

        filters = {}

        if state is not None:
            filters["state"] = state
        if region_id is not None:
            filters["region_id"] = region_id
        if invite_pending is not None:
            # Convert string to boolean if needed
            if isinstance(invite_pending, str):
                invite_pending = invite_pending.lower() == "true"
            filters["invite_pending"] = invite_pending

        users = User.objects.filter(**filters).prefetch_related("roles__organization")

        # Return the updated user details
        return [
            {
                "id": str(user.id),
                "cognito_use_case_description": user.cognito_use_case_description,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name,
                "email": user.email,
                "region_id": user.region_id,
                "state": user.state,
                "user_type": user.user_type,
                "last_logged_in": user.last_logged_in,
                "date_approved": user.date_approved,
                "approved_by": (
                    {
                        "id": str(user.approved_by.id),
                        "full_name": str(user.approved_by.full_name),
                        "email": str(user.approved_by.email),
                    }
                    if user.approved_by
                    else None
                ),
                "accepted_terms_version": user.accepted_terms_version,
                "roles": [
                    {
                        "id": str(role.id),
                        "approved": role.approved,
                        "role": role.role,
                        "organization": (
                            {
                                "id": str(role.organization.id),
                                "name": role.organization.name,
                            }
                            if role.organization
                            else None
                        ),
                    }
                    for role in user.roles.all()
                ],
            }
            for user in users
        ]
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# PUT: /v2/users/{user_id}
def update_user_v2(user_id, user_data, current_user):
    """Update a particular user."""
    try:
        # Validate that the user ID is a valid UUID
        if not user_id or not is_valid_uuid(user_id):
            raise HTTPException(status_code=404, detail="User not found")

        # Check if the current user has permission to access/update this user
        if not can_access_user(current_user, user_id):
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Fetch the user to be updated
        try:
            user = User.objects.prefetch_related("roles").get(id=user_id)
        except User.DoesNotExist:
            raise HTTPException(status_code=404, detail="User not found")

        # Global admins only can update the userType
        if not is_global_write_admin(current_user) and user_data.user_type:
            raise HTTPException(
                status_code=403, detail="Only global admins can update userType."
            )

        # Check if allowed fields to update then execute
        # updates = user_data.dict(exclude_unset=True)
        updates = user_data.model_dump(exclude_unset=True)
        allowed_fields = get_allowed_user_update_fields(current_user, user)

        # Check for disallowed fields before applying updates
        disallowed_fields = set(updates.keys()) - allowed_fields
        if disallowed_fields:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized to update the following fields: {}".format(
                    ", ".join(disallowed_fields)
                ),
            )

        # Apply only the allowed updates
        for field, value in updates.items():
            if field == "state":
                user.region_id = REGION_STATE_MAP.get(value)
                user.state = value
                user.can_select_own_state = False
            else:
                setattr(user, field, value)

        # Save the updated user
        user.save()

        # Fetch updated user with roles and related data
        updated_user = User.objects.prefetch_related("roles__organization").get(
            id=user_id
        )

        # Return the updated user details
        return {
            "id": str(updated_user.id),
            "created_at": updated_user.created_at.isoformat(),
            "updated_at": updated_user.updated_at.isoformat(),
            "first_name": updated_user.first_name,
            "last_name": updated_user.last_name,
            "full_name": user.full_name,
            "email": updated_user.email,
            "region_id": updated_user.region_id,
            "state": updated_user.state,
            "user_type": updated_user.user_type,
            "last_logged_in": user.last_logged_in,
            "first_login": user.first_login,
            "accepted_terms_version": user.accepted_terms_version,
            "roles": [
                {
                    "id": str(role.id),
                    "approved": role.approved,
                    "role": role.role,
                    "organization": (
                        {
                            "id": str(role.organization.id),
                            "name": role.organization.name,
                        }
                        if role.organization
                        else None
                    ),
                }
                for role in updated_user.roles.all()
            ],
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        LOGGER.exception("Error updating user: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# PUT: /users/{user_id}/register/approve
def approve_user_registration(user_id, current_user):
    """Approve a registered user."""
    if not is_valid_uuid(user_id):
        raise HTTPException(status_code=404, detail="Invalid user ID.")

    if str(current_user.id) == str(user_id):
        raise HTTPException(status_code=403, detail="Users cannot approve themselves.")

    try:
        # Retrieve the user by ID
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="User not found.")

    if current_user.invite_pending or not current_user.date_accepted_terms:
        # Return 403 if user is unapproved or has not accepted terms
        raise HTTPException(status_code=403, detail="Account not fully activated.")

    if not (
        is_global_write_admin(current_user)
        or current_user.user_type == UserType.REGIONAL_ADMIN
    ):
        # Return 403 if user is not global_write_admin or regional_admin
        raise HTTPException(
            status_code=403,
            detail="Only authorized admins can approve or deny users.",
        )

    # Ensure authorizer's region matches the user's region
    if not matches_user_region(current_user, user.region_id):
        raise HTTPException(status_code=403, detail="Unauthorized region access.")

    # Approve user
    user.date_approved = datetime.now()
    user.approved_by = current_user
    user.first_login = True
    user.save()

    # Send email notification
    try:
        send_registration_approved_email(
            user.email,
            subject="CISA CyHy Dashboard Account Approved",
            first_name=user.first_name,
            last_name=user.last_name,
            template="crossfeed_approval_notification.html",
        )

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Failed to send email: {}".format(str(e))
        )

    return {
        "status_code": 200,
        "body": "User registration approved.",
    }


# PUT: /users/{user_id}/register/deny
def deny_user_registration(user_id: str, current_user: User):
    """Deny a user's registration by user ID."""
    # Validate UUID format for the user_id
    if not is_valid_uuid(user_id):
        raise HTTPException(status_code=404, detail="User not found.")

    try:
        # Retrieve the user object
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if str(current_user.id) == str(user_id):
            raise HTTPException(
                status_code=403, detail="Users cannot approve themselves."
            )

        if current_user.invite_pending or not current_user.date_accepted_terms:
            # Return 403 if user is unapproved or has not accepted terms
            raise HTTPException(status_code=403, detail="Account not fully activated.")

        if not (
            is_global_write_admin(current_user)
            or current_user.user_type == UserType.REGIONAL_ADMIN
        ):
            # Return 403 if user is not global_write_admin or regional_admin
            raise HTTPException(
                status_code=403,
                detail="Only authorized admins can approve or deny users.",
            )

        # Ensure authorizer's region matches the user's region
        if not matches_user_region(current_user, user.region_id):
            raise HTTPException(status_code=403, detail="Unauthorized region access.")

        # Send registration denial email to the user
        send_registration_denied_email(
            user.email,
            subject="CyHy Dashboard Registration Denied",
            first_name=user.first_name,
            last_name=user.last_name,
            template="crossfeed_denial_notification.html",
        )

        return {"status_code": 200, "body": "User registration denied."}

    except HTTPException as http_exc:
        raise http_exc
    except ObjectDoesNotExist:
        raise HTTPException(status_code=404, detail="User not found.")
    except Exception as e:
        LOGGER.exception("Error denying registration: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# POST: /users
def invite(new_user_data, current_user):
    """Invite a user."""
    try:
        # Validate permissions
        if new_user_data.organization:
            if not is_org_admin(current_user, new_user_data.organization):
                raise HTTPException(status_code=403, detail="Unauthorized access.")
        else:
            if not is_global_write_admin(current_user):
                raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Non-global admins cannot set userType
        if not is_global_write_admin(current_user) and new_user_data.user_type:
            raise HTTPException(status_code=403, detail="Unauthorized access.")

        # Lowercase the email for consistency
        new_user_data.email = new_user_data.email.lower()

        # Map state to region ID if state is provided
        if new_user_data.state:
            new_user_data.region_id = REGION_STATE_MAP.get(new_user_data.state)

        # Check if the user already exists
        user = User.objects.filter(email=new_user_data.email).first()
        organization = (
            Organization.objects.filter(id=new_user_data.organization).first()
            if new_user_data.organization
            else None
        )

        if not user:
            # Create a new user if they do not exist
            user = User.objects.create(
                invite_pending=True,
                **new_user_data.dict(
                    exclude_unset=True,
                    exclude={"organization_admin", "organization", "user_type"},
                ),
            )
            if not os.getenv("IS_LOCAL"):
                send_invite_email(user.email, organization)
        elif not user.first_name and not user.last_name:
            # Update first and last name if the user exists but has no name set
            user.first_name = new_user_data.first_name
            user.last_name = new_user_data.last_name
            user.save()

        # Always update userType if specified
        if new_user_data.user_type:
            user.user_type = new_user_data.user_type.value
            user.save()

        # Assign role if an organization is specified
        if organization:
            Role.objects.update_or_create(
                user=user,
                organization=organization,
                defaults={
                    "approved": True,
                    "created_by": current_user,
                    "approved_by": current_user,
                    "role": "admin" if new_user_data.organization_admin else "user",
                },
            )
        # Return the updated user with relevant details
        return {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "user_type": user.user_type,
            "roles": [
                {
                    "id": str(role.id),
                    "role": role.role,
                    "approved": role.approved,
                    "organization": (
                        {
                            "id": str(role.organization.id),
                            "name": role.organization.name,
                        }
                        if role.organization
                        else {}
                    ),
                }
                for role in user.roles.select_related("organization").all()
            ],
            "invite_pending": user.invite_pending,
        }

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        LOGGER.exception("Error inviting user: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
