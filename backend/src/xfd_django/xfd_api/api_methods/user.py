"""
User API.

"""
# Standard Python Libraries
from datetime import datetime
from typing import List, Optional

# Third-Party Libraries
from fastapi import HTTPException, Query

from ..models import User
from ..schema_models.user import User as UserSchema


async def accept_terms(current_user: User, version: str):
    """
    Accept the latest terms of service.

    Args:
        current_user (User): The current authenticated user.
        version (str): The version of the terms of service.

    Returns:
        User: The updated user.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="User not authenticated.")

    current_user.dateAcceptedTerms = datetime.now()
    current_user.acceptedTermsVersion = version
    current_user.save()

    return UserSchema.from_orm(current_user)


def get_users(regionId):
    """
    Retrieve a list of users based on optional filter parameters.

    Args:
        regionId : Region ID to filter users by.
    Raises:
        HTTPException: If the user is not authorized or no users are found.

    Returns:
        List[User]: A list of users matching the filter criteria.
    """

    try:
        users = User.objects.filter(regionId=regionId).prefetch_related("roles")
        return [UserSchema.from_orm(user) for user in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def delete_user(user_id: str):
    """
    Delete a user by ID.

    Args:
        user_id : The ID of the user to delete.
    Raises:
        HTTPException: If the user is not authorized or the user is not found.

    Returns:
        User: The user that was deleted.
    """

    try:
        user = User.objects.get(id=user_id)
        user.delete()
        return UserSchema.from_orm(user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
