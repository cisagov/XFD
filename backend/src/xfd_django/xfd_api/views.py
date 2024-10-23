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
from typing import List, Optional

# Third-Party Libraries
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4

from .api_methods import organization, scan, scan_tasks
from .api_methods.api_keys import get_api_keys
from .api_methods.cpe import get_cpes_by_id
from .api_methods.cve import get_cves_by_id, get_cves_by_name
from .api_methods.domain import get_domain_by_id
from .api_methods.user import get_users
from .api_methods.vulnerability import get_vulnerability_by_id, update_vulnerability
from .auth import get_current_active_user
from .models import Assessment, User
from .schema_models import organization as OrganizationSchema
from .schema_models import scan as scanSchema
from .schema_models import scan_tasks as scanTaskSchema
from .schema_models.assessment import Assessment as AssessmentSchema
from .schema_models.cpe import Cpe as CpeSchema
from .schema_models.cve import Cve as CveSchema
from .schema_models.domain import Domain as DomainSchema
from .schema_models.domain import DomainSearch
from .schema_models.user import User as UserSchema
from .schema_models.vulnerability import Vulnerability as VulnerabilitySchema

# Define API router
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


# TODO: Uncomment checks for current_user once authentication is implemented
@api_router.get(
    "/assessments",
    #  current_user: User = Depends(get_current_active_user),
    tags=["ReadySetCyber"],
)
async def list_assessments():
    """
    Lists all assessments for the logged-in user.

    Args:
        current_user (User): The current authenticated user.

    Raises:
        HTTPException: If the user is not authorized or assessments are not found.

    Returns:
        List[Assessment]: A list of assessments for the logged-in user.
    """
    # Ensure the user is authenticated
    # if not current_user:
    #     raise HTTPException(status_code=401, detail="Unauthorized")

    # Query the database for assessments belonging to the current user
    # assessments = Assessment.objects.filter(user=current_user)
    assessments = (
        Assessment.objects.all()
    )  # TODO: Remove this line once filtering by user is implemented

    # Return assessments if found, or raise a 404 error if none exist
    if not assessments.exists():
        raise HTTPException(status_code=404, detail="No assessments found")

    return list(assessments)


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


# ========================================
#   Scan Endpoints
# ========================================


@api_router.get(
    "/scans",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.GetScansResponseModel,
    tags=["Scans"],
)
async def list_scans(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of all scans."""
    return scan.list_scans(current_user)


@api_router.get(
    "/granularScans",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.GetGranularScansResponseModel,
    tags=["Scans"],
)
async def list_granular_scans(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of granular scans. User must be authenticated."""
    return scan.list_granular_scans(current_user)


@api_router.post(
    "/scans",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.CreateScanResponseModel,
    tags=["Scans"],
)
async def create_scan(
    scan_data: scanSchema.NewScan, current_user: User = Depends(get_current_active_user)
):
    """Create a new scan."""
    return scan.create_scan(scan_data, current_user)


@api_router.get(
    "/scans/{scan_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.GetScanResponseModel,
    tags=["Scans"],
)
async def get_scan(scan_id: str, current_user: User = Depends(get_current_active_user)):
    """Get a scan by its ID. User must be authenticated."""
    return scan.get_scan(scan_id, current_user)


@api_router.put(
    "/scans/{scan_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.CreateScanResponseModel,
    tags=["Scans"],
)
async def update_scan(
    scan_id: str,
    scan_data: scanSchema.NewScan,
    current_user: User = Depends(get_current_active_user),
):
    """Update a scan by its ID."""
    return scan.update_scan(scan_id, scan_data, current_user)


@api_router.delete(
    "/scans/{scan_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.GenericMessageResponseModel,
    tags=["Scans"],
)
async def delete_scan(
    scan_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete a scan by its ID."""
    return scan.delete_scan(scan_id, current_user)


@api_router.post(
    "/scans/{scan_id}/run",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanSchema.GenericMessageResponseModel,
    tags=["Scans"],
)
async def run_scan(scan_id: str, current_user: User = Depends(get_current_active_user)):
    """Manually run a scan by its ID"""
    return scan.run_scan(scan_id, current_user)


@api_router.post(
    "/scheduler/invoke", dependencies=[Depends(get_current_active_user)], tags=["Scans"]
)
async def invoke_scheduler(current_user: User = Depends(get_current_active_user)):
    """Manually invoke the scan scheduler."""
    response = await scan.invoke_scheduler(current_user)
    return response


# ========================================
#   Scan Task Endpoints
# ========================================


@api_router.post(
    "/scan-tasks/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=scanTaskSchema.ScanTaskListResponse,
    tags=["Scan Tasks"],
)
async def list_scan_tasks(
    search_data: scanTaskSchema.ScanTaskSearch,
    current_user: User = Depends(get_current_active_user),
):
    """List scan tasks based on filters."""
    return scan_tasks.list_scan_tasks(search_data, current_user)


@api_router.post(
    "/scan-tasks/{scan_task_id}/kill",
    dependencies=[Depends(get_current_active_user)],
    tags=["Scan Tasks"],
)
async def kill_scan_tasks(
    scan_task_id: UUID4, current_user: User = Depends(get_current_active_user)
):
    """Kill a scan task."""
    return scan_tasks.kill_scan_task(scan_task_id, current_user)


@api_router.get(
    "/scan-tasks/{scan_task_id}/logs",
    dependencies=[Depends(get_current_active_user)],
    # response_model=scanTaskSchema.GenericResponse,
    tags=["Scan Tasks"],
)
async def get_scan_task_logs(
    scan_task_id: UUID4, current_user: User = Depends(get_current_active_user)
):
    """Get logs from a particular scan task."""
    return scan_tasks.get_scan_task_logs(scan_task_id, current_user)


# ========================================
#   Organization Endpoints
# ========================================


@api_router.get(
    "/organizations",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.GetOrganizationSchema],
    tags=["Organizations"],
)
async def list_organizations(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of all organizations."""
    return organization.list_organizations(current_user)


@api_router.get(
    "/organizations/tags",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.GetTagSchema],
    tags=["Organizations"],
)
async def get_organization_tags(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of organization tags."""
    return organization.get_tags(current_user)


@api_router.get(
    "/organizations/{organization_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GetSingleOrganizationSchema,
    tags=["Organizations"],
)
async def get_organization(
    organization_id: str, current_user: User = Depends(get_current_active_user)
):
    """Retrieve an organization by its ID."""
    return organization.get_organization(organization_id, current_user)


@api_router.get(
    "/organizations/state/{state}",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.GetOrganizationSchema],
    tags=["Organizations"],
)
async def get_organizations_by_state(
    state: str, current_user: User = Depends(get_current_active_user)
):
    """Retrieve organizations by state."""
    return organization.get_by_state(state, current_user)


@api_router.get(
    "/organizations/regionId/{region_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.GetOrganizationSchema],
    tags=["Organizations"],
)
async def get_organizations_by_region(
    region_id: str, current_user: User = Depends(get_current_active_user)
):
    """Retrieve organizations by region ID."""
    return organization.get_by_region(region_id, current_user)


@api_router.get(
    "/regions",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.RegionSchema],
    tags=["Regions"],
)
async def list_regions(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of all regions."""
    return organization.get_all_regions(current_user)


@api_router.post(
    "/organizations",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GetSingleOrganizationSchema,
    tags=["Organizations"],
)
async def create_organization(
    organization_data: OrganizationSchema.NewOrganization,
    current_user: User = Depends(get_current_active_user),
):
    """Create a new organization."""
    return organization.create_organization(organization_data, current_user)


@api_router.post(
    "/organizations_upsert",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GetSingleOrganizationSchema,
    tags=["Organizations"],
)
async def upsert_organization(
    organization_data: OrganizationSchema.NewOrganization,
    current_user: User = Depends(get_current_active_user),
):
    """Upsert an organization."""
    return organization.upsert_organization(organization_data, current_user)


@api_router.put(
    "/organizations/{organization_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GetSingleOrganizationSchema,
    tags=["Organizations"],
)
async def update_organization(
    organization_id: str,
    org_data: OrganizationSchema.NewOrganization,
    current_user: User = Depends(get_current_active_user),
):
    """Update an organization by its ID."""
    return organization.update_organization(organization_id, org_data, current_user)


@api_router.delete(
    "/organizations/{organization_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GenericMessageResponseModel,
    tags=["Organizations"],
)
async def delete_organization(
    organization_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete an organization by its ID."""
    return organization.delete_organization(organization_id, current_user)


@api_router.post(
    "/v2/organizations/{organization_id}/users",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GenericPostResponseModel,
    tags=["Organizations"],
)
async def add_user_to_organization_v2(
    organization_id: str,
    user_data: OrganizationSchema.NewOrgUser,
    current_user: User = Depends(get_current_active_user),
):
    """Add a user to an organization."""
    return organization.add_user_to_org_v2(organization_id, user_data, current_user)


@api_router.post(
    "/organizations/{organization_id}/roles/{role_id}/approve",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GenericMessageResponseModel,
    tags=["Organizations"],
)
async def approve_role(
    organization_id: str,
    role_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Approve a role within an organization."""
    return organization.approve_role(organization_id, role_id, current_user)


@api_router.post(
    "/organizations/{organization_id}/roles/{role_id}/remove",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.GenericMessageResponseModel,
    tags=["Organizations"],
)
async def remove_role(
    organization_id: str,
    role_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Remove a role from an organization."""
    return organization.remove_role(organization_id, role_id, current_user)


@api_router.post(
    "/organizations/{organization_id}/granularScans/{scan_id}/update",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.UpdateOrgScanSchema,
    tags=["Organizations"],
)
async def update_granular_scan(
    organization_id: str,
    scan_id: str,
    scan_data: OrganizationSchema.NewOrgScan,
    current_user: User = Depends(get_current_active_user),
):
    """Update a granular scan for an organization."""
    return organization.update_org_scan(
        organization_id, scan_id, scan_data, current_user
    )


@api_router.get(
    "/v2/organizations",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.GetOrganizationSchema],
    tags=["Organizations"],
)
async def list_organizations_v2(
    state: Optional[List[str]] = Query(None),
    regionId: Optional[List[str]] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve a list of all organizations (version 2)."""
    return organization.list_organizations_v2(state, regionId, current_user)
