"""
User API.

"""
# Standard Python Libraries
from typing import List, Optional

# Third-Party Libraries
from fastapi import HTTPException, Query

from ..models import User
from ..schemas import User as UserSchema


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
