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
from . import schema_models
from .api_methods.api_keys import get_api_keys
from .api_methods.cpe import get_cpes_by_id
from .api_methods.cve import get_cves_by_id, get_cves_by_name
from .api_methods.domain import get_domain_by_id
from .api_methods.organization import get_organizations, read_orgs
from .api_methods.user import get_users
from .api_methods.vulnerability import get_vulnerability_by_id, update_vulnerability
from .auth import get_current_active_user
from .models import ApiKey, Cpe, Cve, Domain, Organization, Role, User, Vulnerability
from .schemas import Cpe as CpeSchema
from .schemas import Cve as CveSchema
from .schemas import Domain as DomainSchema
from .schemas import DomainFilters, DomainSearch
from .schemas import Organization as OrganizationSchema
from .schemas import Role as RoleSchema
from .schemas import User as UserSchema
from .schemas import Vulnerability as VulnerabilitySchema

api_router = APIRouter()


# Healthcheck endpoint
@api_router.get("/healthcheck", tags=["Testing"])
async def healthcheck():
    """
    Healthcheck endpoint.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "ok2"}


@api_router.get("/test-apikeys", tags=["Testing"])
async def call_get_api_keys():
    """
    Get all API keys.

    Returns:
        list: A list of all API keys.
    """
    return get_api_keys()


@api_router.post(
    "/test-orgs",
    # dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema],
    tags=["Organizations", "Testing"],
)
async def call_read_orgs():
    """
    List all organizations with query parameters.
    Args:
        state (Optional[List[str]]): List of states to filter organizations by.
        regionId (Optional[List[str]]): List of region IDs to filter organizations by.

    Raises:
        HTTPException: If the user is not authorized or no organizations are found.

    Returns:
        List[Organizations]: A list of organizations matching the filter criteria.
    """
    return read_orgs()


@api_router.post("/search")
async def search():
    pass


@api_router.post("/search/export")
async def export_search():
    pass


@api_router.get(
    "/cpes/{cpe_id}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=CpeSchema,
    tags=["Cpe"],
)
async def call_get_cpes_by_id(cpe_id):
    """
    Get Cpe by id.
    Returns:
        object: a single Cpe object.
    """
    return get_cpes_by_id(cpe_id)


@api_router.get(
    "/cves/{cve_id}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=CveSchema,
    tags=["Cve"],
)
async def call_get_cves_by_id(cve_id):
    """
    Get Cve by id.
    Returns:
        object: a single Cve object.
    """
    return get_cves_by_id(cve_id)


@api_router.get(
    "/cves/name/{cve_name}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=CveSchema,
    tags=["Get cve by name"],
)
async def call_get_cves_by_name(cve_name):
    """
    Get Cve by name.
    Returns:
        object: a single Cpe object.
    """
    return get_cves_by_name(cve_name)


@api_router.post("/domain/search")
async def search_domains(domain_search: DomainSearch):
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
    response_model=DomainSchema,
    tags=["Get domain by id"],
)
async def call_get_domain_by_id(domain_id: str):
    """
    Get domain by id.
    Returns:
        object: a single Domain object.
    """
    return get_domain_by_id(domain_id)


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
    response_model=VulnerabilitySchema,
    tags="Get vulnerability by id",
)
async def call_get_vulnerability_by_id(vuln_id):
    """
    Get vulnerability by id.
    Returns:
        object: a single Vulnerability object.
    """
    return get_vulnerability_by_id(vuln_id)


@api_router.put(
    "/vulnerabilities/{vulnerabilityId}",
    # dependencies=[Depends(get_current_active_user)],
    response_model=VulnerabilitySchema,
    tags="Update vulnerability",
)
async def call_update_vulnerability(vuln_id, data: VulnerabilitySchema):
    """
    Update vulnerability by id.

    Returns:
        object: a single vulnerability object that has been modified.
    """
    return update_vulnerability(vuln_id, data)


@api_router.get(
    "/v2/users",
    response_model=List[UserSchema],
    # dependencies=[Depends(get_current_active_user)],
    tags=["User"],
)
async def call_get_users(
    state: Optional[List[str]] = Query(None),
    regionId: Optional[List[str]] = Query(None),
    invitePending: Optional[List[str]] = Query(None),
    # current_user: User = Depends(is_regional_admin)
):
    """
    Call get_users()

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
    return get_users(state, regionId, invitePending)


@api_router.get(
    "/organizations",
    # response_model=List[OrganizationSchema],
    # dependencies=[Depends(get_current_active_user)],
    tags=["Organizations"],
)
async def call_get_organizations(
    state: Optional[List[str]] = Query(None),
    regionId: Optional[List[str]] = Query(None),
):
    """
    List all organizations with query parameters.
    Args:
        state (Optional[List[str]]): List of states to filter organizations by.
        regionId (Optional[List[str]]): List of region IDs to filter organizations by.

    Raises:
        HTTPException: If the user is not authorized or no organizations are found.

    Returns:
        List[Organizations]: A list of organizations matching the filter criteria.
    """
    return get_organizations(state, regionId)
