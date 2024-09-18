"""
This module provides various helper functions for the api endpoints.

"""
# Standard Python Libraries
from datetime import datetime
import uuid

# Third-Party Libraries
# Third Party Libraries
from django.forms.models import model_to_dict
from fastapi import HTTPException, status
from xfd_api.models import User


def user_to_dict(user):
    """Takes a user model object from django and
    sanitizes fields for output.

    Args:
        user (django model): Django User model object

    Returns:
        dict: Returns sanitized and formated dict
    """
    user_dict = model_to_dict(user)  # Convert model to dict
    # Convert any UUID fields to strings
    if isinstance(user_dict.get("id"), uuid.UUID):
        user_dict["id"] = str(user_dict["id"])
    for key, val in user_dict.items():
        if isinstance(val, datetime):
            user_dict[key] = str(val)
    return user_dict


async def update_or_create_user(user_info):
    try:
        print(f"User info from update_or_create: {user_info}")
        user, created = User.objects.get_or_create(email=user_info["email"])
        if created:
            user.oktaId = user_info["sub"]
            user.firstName = user_info["given_name"]
            user.lastName = user_info["family_name"]
            user.invitePending = True
            user.userType = "standard"
            user.save()
        else:
            if user.cognitoId != user_info["sub"]:
                user.cognitoId = user_info["sub"]
            user.lastLoggedIn = datetime.utcnow()
            user.save()
        return user
    except Exception as error:
        print(f"Error from update_or_create: {str(error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error
