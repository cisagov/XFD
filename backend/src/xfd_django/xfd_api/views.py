"""
This module defines the API endpoints for the FastAPI application.

It includes endpoints for:
- Healthcheck
- Retrieving all API keys
- Retrieving all organizations

Endpoints:
    - healthcheck: Returns the health status of the application.
    - get_api_keys: Retrieves all API keys.
    - read_orgs: Retrieves all organizations.

Dependencies:
    - fastapi
    - .auth
    - .models
"""
# Third-Party Libraries
from fastapi import APIRouter, Depends, HTTPException

from .auth import get_current_active_user
from .models import ApiKey, Organization, User

api_router = APIRouter()


# Healthcheck endpoint
@api_router.get("/healthcheck")
async def healthcheck():
    """
    Healthcheck endpoint.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "ok2"}


@api_router.get("/test-apikeys")
async def get_api_keys():
    """
    Get all API keys.

    Returns:
        list: A list of all API keys.
    """
    try:
        api_keys = ApiKey.objects.all()
        # return api_keys
        return [
            {
                "id": api_key.id,
                "created_at": api_key.createdAt,
                "updated_at": api_key.updatedAt,
                "last_used": api_key.lastUsed,
                "hashed_key": api_key.hashedKey,
                "last_four": api_key.lastFour,
                "user_id": api_key.userId.id if api_key.userId else None,
            }
            for api_key in api_keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post(
    "/test-orgs",
    dependencies=[Depends(get_current_active_user)],
    tags=["List of all Organizations"],
)
def read_orgs(current_user: User = Depends(get_current_active_user)):
    """Call API endpoint to get all organizations."""
    try:
        organizations = Organization.objects.all()
        return [
            {
                "id": organization.id,
                "name": organization.name,
                "acronym": organization.acronym,
                "root_domains": organization.rootDomains,
                "ip_blocks": organization.ipBlocks,
                "is_passive": organization.isPassive,
                "country": organization.country,
                "state": organization.state,
                "region_id": organization.regionId,
                "state_fips": organization.stateFips,
                "state_name": organization.stateName,
                "county": organization.county,
                "county_fips": organization.countyFips,
                "type": organization.type,
                "parent_id": organization.parentId.id
                if organization.parentId
                else None,
                "created_by_id": organization.createdById.id
                if organization.createdById
                else None,
                "created_at": organization.createdAt,
                "updated_at": organization.updatedAt,
            }
            for organization in organizations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
