

from django.shortcuts import render
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Security,
    UploadFile,
    status,
)
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


@api_router.get("/apikeys")
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
                "created_at": api_key.createdat,
                "updated_at": api_key.updatedat,
                "last_used": api_key.lastused,
                "hashed_key": api_key.hashedkey,
                "last_four": api_key.lastfour,
                "user_id": api_key.userid.id if api_key.userid else None,
            }
            for api_key in api_keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@api_router.get("/organizations")
async def get_organizations(current_user: User = Depends(get_current_active_user)):
    """
    Get all organizations.
    Returns:
        list: A list of all organizations.
    """
    try:
        organizations = Organization.objects.all()
        return [
            {
                "id": organization.id,
                "name": organization.name,
                "acronym": organization.acronym,
                "root_domains": organization.rootdomains,
                "ip_blocks": organization.ipblocks,
                "is_passive": organization.ispassive,
                "country": organization.country,
                "state": organization.state,
                "region_id": organization.regionid,
                "state_fips": organization.statefips,
                "state_name": organization.statename,
                "county": organization.county,
                "county_fips": organization.countyfips,
                "type": organization.type,
                "parent_id": organization.parentid.id if organization.parentid else None,
                "created_by_id": organization.createdbyid.id if organization.createdbyid else None,
                "created_at": organization.createdat,
                "updated_at": organization.updatedat,
            }
            for organization in organizations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))