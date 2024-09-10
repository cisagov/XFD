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
# Standard Python Libraries
from typing import Any, List, Optional, Union

# Third-Party Libraries
from django.shortcuts import render
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

# from .schemas import Cpe
from . import schemas
from .auth import get_current_active_user
from .models import ApiKey, Cpe, Cve, Domain, Organization, Role, User, Vulnerability
from .schemas import Role as RoleSchema
from .schemas import User as UserSchema

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
                "createdAt": api_key.createdAt,
                "updatedAt": api_key.updatedAt,
                "lastUsed": api_key.lastUsed,
                "hashedKey": api_key.hashedKey,
                "lastFour": api_key.lastFour,
                "userId": api_key.userId.id if api_key.userId else None,
            }
            for api_key in api_keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post(
    "/test-orgs",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[schemas.Organization],
    tags=["List of all Organizations"],
)
def read_orgs(current_user: User = Depends(get_current_active_user)):
    """Call API endpoint to get all organizations.
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
                "rootDomains": organization.rootDomains,
                "ipBlocks": organization.ipBlocks,
                "isPassive": organization.isPassive,
                "country": organization.country,
                "state": organization.state,
                "regionId": organization.regionId,
                "stateFips": organization.stateFips,
                "stateName": organization.stateName,
                "county": organization.county,
                "countyFips": organization.countyFips,
                "type": organization.type,
                "parentId": organization.parentId.id if organization.parentId else None,
                "createdById": organization.createdById.id
                if organization.createdById
                else None,
                "createdAt": organization.createdAt,
                "updatedAt": organization.updatedAt,
            }
            for organization in organizations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/search")
async def search():
    pass


@api_router.post("/search/export")
async def export_search():
    pass


@api_router.get(
    "/cpes/{cpe_id}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=schemas.Cpe,
    tags=["Get cpe by id"],
)
async def get_cpes_by_id(cpe_id):
    """
    Get Cpe by id.
    Returns:
        object: a single Cpe object.
    """
    try:
        cpe = Cpe.objects.get(id=cpe_id)
        return cpe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get(
    "/cves/{cve_id}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=schemas.Cve,
    tags=["Get cve by id"],
)
async def get_cves_by_id(cve_id):
    """
    Get Cve by id.
    Returns:
        object: a single Cve object.
    """
    try:
        cve = Cve.objects.get(id=cve_id)
        return cve
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get(
    "/cves/name/{cve_name}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=schemas.Cve,
    tags=["Get cve by name"],
)
async def get_cves_by_name(cve_name):
    """
    Get Cve by name.
    Returns:
        object: a single Cpe object.
    """
    try:
        cve = Cve.objects.get(name=cve_name)
        return cve
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/domain/search")
async def search_domains(domain_search: schemas.DomainSearch):
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/domain/export")
async def export_domains():
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get(
    "/domain/{domain_id}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=List[schemas.Domain],
    tags=["Get domain by id"],
)
async def get_domain_by_id(domain_id: str):
    """
    Get domain by id.
    Returns:
        object: a single Domain object.
    """
    try:
        domains = list(Domain.objects.filter(id=domain_id))

        return domains
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/vulnerabilities/search")
async def search_vulnerabilities():
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/vulnerabilities/export")
async def export_vulnerabilities():
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get(
    "/vulnerabilities/{vulnerabilityId}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=schemas.Vulnerability,
    tags="Get vulnerability by id",
)
async def get_vulnerability_by_id(vuln_id):
    """
    Get vulnerability by id.
    Returns:
        object: a single Vulnerability object.
    """
    try:
        vulnerability = Vulnerability.objects.get(id=vuln_id)
        return vulnerability
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.put(
    "/vulnerabilities/{vulnerabilityId}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=schemas.Vulnerability,
    tags="Update vulnerability",
)
async def update_vulnerability(vuln_id, data: schemas.Vulnerability):
    """
    Update vulnerability by id.

    Returns:
        object: a single vulnerability object that has been modified.
    """
    try:
        vulnerability = Vulnerability.objects.get(id=vuln_id)
        vulnerability = data
        vulnerability.save()
        return vulnerability
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get(
    "/v2/users",
    response_model=List[UserSchema],
    # dependencies=[Depends(get_current_active_user)],
)
async def get_users(
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
