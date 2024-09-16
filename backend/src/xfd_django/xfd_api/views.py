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
from . import scans

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
    # response_model=List[schemas.Organization],
    tags=["List of all Organizations"],
)
def read_orgs(current_user: User = Depends(get_current_active_user)):
    """Call API endpoint to get all organizations.
    Returns:
        list: A list of all organizations.
    """
    try:
        organizations = Organization.objects.all()
        print(organizations)
        return organizations
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


##############################################################################
@api_router.get(
    "/scans",
    dependencies=[Depends(get_current_active_user)],
    response_model=schemas.GetScansResponseModel,
    tags=["Scans"],
)
async def list_scans(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of all scans."""
    return scans.list_scans()


@api_router.get(
    "/granularScans",
    dependencies=[Depends(get_current_active_user)],
    # response_model=schemas.GetGranularScansResponseModel,
    tags=["Scans"],
)
async def list_granular_scans(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of granular scans. User must be authenticated."""
    return scans.list_granular_scans()


@api_router.post(
    "/scans",
    dependencies=[Depends(get_current_active_user)],
    # response_model=schemas.CreateScanResponseModel,
    tags=["Scans"],
)
async def create_scan(
    scan_data: schemas.CreateScan, current_user: User = Depends(get_current_active_user)
):
    """ Create a new scan."""
    return scans.create_scan(scan_data, current_user)


@api_router.get("/scans/{scan_id}", response_model=schemas.Scan)
async def get_scan(scan_id: str, current_user: User = Depends(get_current_active_user)):
    """
    Endpoint to retrieve a scan by its ID. User must be authenticated.

    Args:
        scan_id (str): The ID of the scan to retrieve.
        current_user (User): The authenticated user, injected via Depends.

    Returns:
        The scan object.
    """
    return scans.get_scan(scan_id)


@api_router.put("/scans/{scan_id}", response_model=schemas.Scan)
async def update_scan(
    scan_id: str,
    scan_data: schemas.Scan,
    current_user: User = Depends(get_current_active_user),
):
    """
    Endpoint to update a scan by its ID. User must be authenticated.

    Args:
        scan_id (str): The ID of the scan to update.
        scan_data (ScanUpdate): The updated scan data.
        current_user (User): The authenticated user, injected via Depends.

    Returns:
        The updated scan object.
    """
    return scans.update_scan(scan_id, scan_data)


@api_router.delete("/scans/{scan_id}")
async def delete_scan(
    scan_id: str, current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint to delete a scan by its ID. User must be authenticated.

    Args:
        scan_id (str): The ID of the scan to delete.
        current_user (User): The authenticated user, injected via Depends.

    Returns:
        A confirmation message.
    """
    return scans.delete_scan(scan_id)


@api_router.post("/scans/{scan_id}/run")
async def run_scan(scan_id: str, current_user: User = Depends(get_current_active_user)):
    """
    Endpoint to manually run a scan by its ID. User must be authenticated.

    Args:
        scan_id (str): The ID of the scan to run.
        current_user (User): The authenticated user, injected via Depends.

    Returns:
        A confirmation message that the scan has been triggered.
    """
    return scans.run_scan(scan_id)


@api_router.post("/scheduler/invoke")
async def invoke_scheduler(current_user: User = Depends(get_current_active_user)):
    """
    Endpoint to manually invoke the scan scheduler. User must be authenticated.

    Args:
        current_user (User): The authenticated user, injected via Depends.

    Returns:
        A confirmation message that the scheduler was invoked.
    """
    return scans.invoke_scheduler()
