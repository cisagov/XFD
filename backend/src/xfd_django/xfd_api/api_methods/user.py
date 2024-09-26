"""
User API.

"""
# Standard Python Libraries
from typing import List, Optional

# Third-Party Libraries
from fastapi import HTTPException, Query

from ..models import User
from ..schema_models.user import User as UserSchema


def get_users(
    state: Optional[List[str]] = Query(None),
    regionId: Optional[List[str]] = Query(None),
    invitePending: Optional[List[str]] = Query(None),
    # current_user: User = Depends(is_regional_admin)
):
    """
    Retrieve a list of users based on optional filter parameters.

    Args:
        state (Optional[List[str]]): List of states to filter users by.
        regionId (Optional[List[str]]): List of region IDs to filter users by.
        invitePending (Optional[List[str]]): List of invite pending statuses to filter users by.
        current_user (User): The current authenticated user, must be a regional admin.

    Raises:
        HTTPException: If the user is not authorized or no users are found.

    Returns:
        List[User]: A list of users matching the filter criteria.
    """
    # if not current_user:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    # Prepare filter parameters
    filter_params = {}
    if state:
        filter_params["state__in"] = state
    if regionId:
        filter_params["regionId__in"] = regionId
    if invitePending:
        filter_params["invitePending__in"] = invitePending

    # Query users with filter parameters and prefetch related roles
    users = User.objects.filter(**filter_params).prefetch_related("roles")

    if not users.exists():
        raise HTTPException(status_code=404, detail="No users found")

    # Return the Pydantic models directly by calling from_orm
    return [UserSchema.from_orm(user) for user in users]
