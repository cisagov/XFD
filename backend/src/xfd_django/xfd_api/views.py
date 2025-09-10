"""This module defines the API endpoints for the FastAPI application."""
# Standard Python Libraries
from datetime import date, datetime, timezone
import hashlib
import json
import logging
import os
from typing import List, Optional, Union
from uuid import UUID

# Third-Party Libraries
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from redis import asyncio as aioredis
import xfd_api.api_methods.dmz_sync as cybersix_module
from xfd_api.auth import is_global_write_admin

# xfd_api helpers
from xfd_api.helpers.checksum_response import build_checksum_response
from xfd_mini_dl.models import User

# from .schemas import Cpe
from .api_methods import api_key as api_key_methods
from .api_methods import dmz_sync as dmz_sync_methods
from .api_methods import notification as notification_methods
from .api_methods import organization, proxy, scan, scan_tasks, user
from .api_methods.blocklist import handle_check_ip
from .api_methods.cpe import get_cpes_by_id
from .api_methods.cve import get_all_cves, get_cves_by_id, get_cves_by_name
from .api_methods.dmz_sync import CybersixSyncParams
from .api_methods.dns_twist_sync import dns_twist_sync_post
from .api_methods.domain import export_domains, get_domain_by_id, search_domains
from .api_methods.export import export
from .api_methods.metrics import (
    default_metrics_window,
    get_scan_daily_status_counts,
    list_scans_org_count_by_status,
)
from .api_methods.object_store import get_object_store_presigned_url
from .api_methods.pshtt_sync import pshtt_sync_post
from .api_methods.queue_monitoring import list_queues
from .api_methods.saved_search import (
    create_saved_search,
    delete_saved_search,
    get_saved_search,
    list_saved_searches,
    update_saved_search,
)
from .api_methods.search import search_export, search_post
from .api_methods.stats import (
    get_by_org_stats,
    get_num_vulns,
    get_severity_stats,
    get_stats,
    get_stats_comparison_data,
    get_user_ports_count,
    get_user_services_count,
    get_v2_trending_data,
    get_vs_condensed_trending_data,
    get_vs_trending_data,
    stats_latest_vulns,
    stats_most_common_vulns,
)
from .api_methods.sync import sync_post
from .api_methods.user import (
    accept_terms,
    delete_user,
    get_me,
    get_users,
    get_users_by_region_id,
    get_users_by_state,
    get_users_v2,
    update_user_v2,
)
from .api_methods.user_log_search import search_logs, search_logs_filtered
from .api_methods.vulnerability import (
    enrich_kev_fields,
    export_vulnerabilities,
    get_vulnerability_by_id,
    get_vulnerability_by_scan_source_and_id,
    search_vulnerabilities,
    v2_get_vulnerability_by_id,
)
from .api_methods.was_sync import (
    get_all_was_scan_summaries,
    get_was_findings_queryset,
    paginate_queryset,
)
from .api_methods.xpanse_sync import xpanse_sync_post
from .auth import (
    get_current_active_user,
    get_current_active_user_unsafe,
    handle_okta_callback,
    sign_oauth_data,
)
from .login_gov import callback
from .schema_models import organization_schema as OrganizationSchema
from .schema_models import scan as scanSchema
from .schema_models import scan_tasks as scanTaskSchema
from .schema_models import stat_schema
from .schema_models.api_key import ApiKey as ApiKeySchema
from .schema_models.blocklist import BlocklistCheckResponse
from .schema_models.cpe import Cpe as CpeSchema
from .schema_models.cve import Cve as CveSchema
from .schema_models.cve import GetAllCvesResponse
from .schema_models.dmz_sync import (
    AsmSyncResponse,
    CensysSyncResponse,
    CredSyncResponse,
    CybersixSyncResponse,
    DataSource,
    ShodanSyncResponse,
    SyncRequest,
)
from .schema_models.dns_twist_sync import DnsTwistSyncBody, DnsTwistSyncResponse
from .schema_models.domain import DomainSearch, DomainSearchResponse, GetDomainResponse
from .schema_models.export import ExportPayload, ExportResponse
from .schema_models.metrics import (
    GetScanDailyStatusCountsResponse,
    ListScansOrgCountByStatusResponse,
)
from .schema_models.notification import CreateNotificationSchema
from .schema_models.notification import Notification as NotificationSchema
from .schema_models.object_store import (
    ObjectStorePresignedUrlRequest,
    ObjectStorePresignedUrlResponse,
)
from .schema_models.queue_monitoring import QueueListResponse, QueueSearch
from .schema_models.saved_search import (
    SavedSearchCreate,
    SavedSearchList,
    SavedSearchUpdate,
)
from .schema_models.saved_search import SavedSearch as SavedSearchSchema
from .schema_models.search import DomainSearchBody, SearchResponse
from .schema_models.sync import SyncBody, SyncResponse, XpanseSyncResponse
from .schema_models.user import (
    NewUser,
    NewUserResponseModel,
    RegisterUserResponse,
    UpdateUserV2,
)
from .schema_models.user import User as UserSchema
from .schema_models.user import UserResponseV2, VersionModel
from .schema_models.user_log_schema import (
    GetLogResponse,
    LogSearch,
    LogSearchFilter,
    LogSearchResponse,
    LogSearchResponseFilters,
)
from .schema_models.vulnerability import (
    CredBreachVulnerabilityResponse,
    GetV2VulnerabilityResponse,
    GetVulnerabilityByIdRequest,
    GetVulnerabilityResponse,
    ShodanVulnerabiltyResponse,
    VsVulnerabilityResponse,
    VulnByIdRequest,
    VulnerabilitySearch,
    VulnerabilitySearchResponse,
)
from .schema_models.was_sync import (
    GetAllWasFindingsResponse,
    GetWasScanSummariesResponse,
    WasFinding,
    WasScanSummarySchema,
)
from .tools.serializers import serialize_organization, serialize_user
from .tools.user_logger_decorator import (
    get_organization_sync,
    get_user_sync,
    log_action,
)

LOGGER = logging.getLogger(__name__)

# Define API router
api_router = APIRouter()

SALT = os.getenv("CHECKSUM_SALT", "default_salt")


async def get_redis_client(request: Request):
    """Get the Redis client from the application state."""
    return request.app.state.redis


# ========================================
#   Analytic Endpoints
# ========================================


# Matomo Proxy
@api_router.api_route(
    "/matomo/{path:path}",
    dependencies=[Depends(get_current_active_user)],
    tags=["Analytics"],
)
async def matomo_proxy(
    path: str, request: Request, current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to the Matomo analytics instance."""
    # Public paths -- directly allowed
    allowed_paths = ["/matomo.php", "/matomo.js"]
    if any(
        [request.url.path.startswith(allowed_path) for allowed_path in allowed_paths]
    ):
        return await proxy.proxy_request(path, request, os.getenv("MATOMO_URL"))

    # Redirects for specific font files
    if request.url.path in [
        "/plugins/Morpheus/fonts/matomo.woff2",
        "/plugins/Morpheus/fonts/matomo.woff",
        "/plugins/Morpheus/fonts/matomo.ttf",
    ]:
        return RedirectResponse(
            url="https://cdn.jsdelivr.net/gh/matomo-org/matomo@5.2.1{}".format(
                request.url.path
            )
        )

    # Ensure only global admin can access other paths
    if current_user.user_type != "globalAdmin":
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Handle the proxy request to Matomo
    return await proxy.proxy_request(
        request, os.getenv("MATOMO_URL", ""), path, cookie_name="MATOMO_SESSID"
    )


# P&E Proxy
@api_router.api_route(
    "/pe/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    dependencies=[Depends(get_current_active_user)],
    tags=["Analytics"],
)
async def pe_proxy(
    path: str, request: Request, current_user: User = Depends(get_current_active_user)
):
    """Proxy requests to the P&E Django application."""
    # Ensure only Global Admin and Global View users can access
    if current_user.user_type not in ["globalView", "globalAdmin"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Handle the proxy request to the P&E Django application
    return await proxy.proxy_request(request, os.getenv("PE_API_URL", ""), path)


# ========================================
#   API Key Endpoints
# ========================================


# POST
@api_router.post("/api-keys", response_model=ApiKeySchema, tags=["API Keys"])
async def create_api_key(current_user: User = Depends(get_current_active_user)):
    """Create api key."""
    return api_key_methods.post(current_user)


# DELETE
@api_router.delete("/api-keys/{api_key_id}", tags=["API Keys"])
async def delete_api_key(
    api_key_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete api key by id."""
    return api_key_methods.delete(api_key_id, current_user)


# GET ALL
@api_router.get("/api-keys", response_model=List[ApiKeySchema], tags=["API Keys"])
async def get_all_api_keys(current_user: User = Depends(get_current_active_user)):
    """Get all api keys."""
    return api_key_methods.get_all(current_user)


# GET BY ID
@api_router.get(
    "/api-keys/{api_key_id}", response_model=ApiKeySchema, tags=["API Keys"]
)
async def get_api_key(
    api_key_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get api key by id."""
    return api_key_methods.get_by_id(api_key_id, current_user)


# ========================================
#   Auth Endpoints
# ========================================


# Okta Callback
@api_router.post("/auth/okta-callback", tags=["Auth"])
async def okta_callback(request: Request):
    """Handle Okta Callback."""
    return await handle_okta_callback(request)


# V1 Callback
@api_router.post("/auth/callback", tags=["Auth"])
async def callback_route(request: Request):
    """Handle V1 Callback."""
    body = await request.json()
    try:
        user_info = callback(body)
        return user_info
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


# Return signed OAuth metadata
@api_router.post("/auth/get-oauth-meta", tags=["Auth"])
async def get_oauth_meta(payload: dict):
    """Return signed OAuth metadata."""
    state = payload.get("state")
    code_verifier = payload.get("code_verifier")
    if not state or not code_verifier:
        raise HTTPException(status_code=400, detail="Missing parameters")
    signed_token = sign_oauth_data(state, code_verifier)
    return {"signedToken": signed_token}


# ========================================
#   CPE Endpoints
# ========================================


@api_router.get(
    "/cpes/{cpe_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=CpeSchema,
    tags=["CPEs"],
)
async def call_get_cpes_by_id(cpe_id):
    """Get Cpe by id."""
    return get_cpes_by_id(cpe_id)


# ========================================
#   CVE Endpoints
# ========================================


@api_router.get(
    "/cves/{cve_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=CveSchema,
    tags=["CVEs"],
)
async def call_get_cves_by_id(cve_id):
    """Get Cve by id."""
    return get_cves_by_id(cve_id)


@api_router.get(
    "/cves/name/{cve_name}",
    dependencies=[Depends(get_current_active_user)],
    response_model=CveSchema,
    tags=["CVEs"],
)
async def call_get_cves_by_name(cve_name):
    """Get Cve by name."""
    return get_cves_by_name(cve_name)


# --- NIST CVE endpoint, CRASM-2431 ---
@api_router.post(
    "/dmz_sync/cves",
    dependencies=[Depends(get_current_active_user)],
    response_model=GetAllCvesResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["CVEs to sync to LZ db"],
)
async def get_call_all_cves(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Which page to fetch (1-indexed)."),
    per_page: int = Query(100, ge=1, description="How many items per page."),
):
    """
    Return paginated CVEs plus an X-Salted-Checksum header for integrity.

    - `page` & `per_page` control pagination.
    - Only global write-admins may call this.
    """
    # fetch & paginate
    try:
        total_pages, records = await get_all_cves(
            current_user,
            page=page,
            per_page=per_page,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error: {}".format(e),
        )

    # serialize
    raw = [CveSchema.from_orm(r).model_dump() for r in records]
    # …and then convert any UUID/datetime in there into plain strings
    payload = jsonable_encoder(raw)

    response_obj = {
        "status": "ok",
        "payload": payload,
    }

    # checksum
    json_str = json.dumps(response_obj, default=str, sort_keys=True)
    checksum = hashlib.sha256((SALT + json_str).encode()).hexdigest()
    response.headers["X-Salted-Checksum"] = checksum

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=response_obj,
        headers={"X-Salted-Checksum": checksum},
    )


# ========================================
#   New Export Endpoint
# ========================================


@api_router.post(
    "/export",
    dependencies=[Depends(get_current_active_user)],
    response_model=ExportResponse,
    tags=["Export"],
)
async def export_post(
    request_body: ExportPayload, current_user: User = Depends(get_current_active_user)
):
    """Call export."""
    return export(request_body, current_user)


# ========================================
#   Domain Endpoints
# ========================================


@api_router.post(
    "/domain/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=DomainSearchResponse,
    tags=["Domains"],
)
async def call_search_domains(
    domain_search: DomainSearch, current_user: User = Depends(get_current_active_user)
):
    """Call search domains."""
    domains, count = search_domains(domain_search, current_user)
    return DomainSearchResponse(result=domains, count=count)


@api_router.post(
    "/domain/export",
    dependencies=[Depends(get_current_active_user)],
    tags=["Domains"],
)
async def call_export_domains(
    domain_search: DomainSearch, current_user: User = Depends(get_current_active_user)
):
    """Call export domains."""
    try:
        return export_domains(domain_search, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get(
    "/domain/{domain_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=GetDomainResponse,
    tags=["Domains"],
)
async def call_get_domain_by_id(domain_id: str):
    """Get domain by id."""
    return get_domain_by_id(domain_id)


# ========================================
#   Log Endpoints
# ========================================


@api_router.post(
    "/logs/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=LogSearchResponse,
    tags=["Logs"],
)
async def call_search_logs(
    log_search: LogSearch, current_user: User = Depends(get_current_active_user)
):
    """Search log table."""
    log_data, count = search_logs(log_search, current_user)
    return LogSearchResponse(result=log_data, count=count)


@api_router.post(
    "/logs/filtered-search",
    dependencies=[Depends(get_current_active_user)],
    response_model=LogSearchResponseFilters,
    tags=["Logs"],
)
async def call_search_logs_filtered(
    log_search: LogSearchFilter,
    current_user: dict = Depends(get_current_active_user),
):
    """Search logs with filtering capabilities."""
    logs, count = search_logs_filtered(log_search, current_user)
    try:
        result = [GetLogResponse.model_validate(log) for log in logs]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Serialization error: {}".format(str(e))
        )
    return LogSearchResponseFilters(result=result, count=count)


# ========================================
#   Metrics Dashboard Endpoints
# ========================================


@api_router.get(
    "/metrics/scans",
    dependencies=[Depends(get_current_active_user)],
    response_model=ListScansOrgCountByStatusResponse,
    tags=["metrics"],
)
async def call_list_scans_org_count_by_status(
    window_days: int = default_metrics_window,
    current_user: User = Depends(get_current_active_user),
):
    """List scans and annotate with metrics."""
    try:
        return list_scans_org_count_by_status(window_days, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching scan metrics: {}".format(e),
        )


@api_router.get(
    "/metrics/scans/{scan_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=GetScanDailyStatusCountsResponse,
    tags=["metrics"],
)
async def call_get_scan_daily_status_counts(
    scan_id: str,
    window_days: int = default_metrics_window,
    current_user: User = Depends(get_current_active_user),
):
    """Get daily http status counts for a specific scan."""
    try:
        return get_scan_daily_status_counts(scan_id, window_days, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching daily status counts for scan {}: {}".format(
                scan_id, e
            ),
        )


# ========================================
#   Notification Endpoints
# ========================================


# POST
@api_router.post(
    "/notifications",
    dependencies=[Depends(get_current_active_user)],
    response_model=NotificationSchema,
    tags=["Notifications"],
)
async def create_notification(
    notification_data: CreateNotificationSchema,
    current_user: User = Depends(get_current_active_user),
):
    """Create notification key."""
    return notification_methods.post(notification_data, current_user)


# DELETE
@api_router.delete(
    "/notifications/{notification_id}",
    dependencies=[Depends(get_current_active_user)],
    tags=["Notifications"],
)
async def delete_notification(
    notification_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete notification by id."""
    return notification_methods.delete(notification_id, current_user)


# GET ALL: Doesn't require authentication
@api_router.get(
    "/notifications", response_model=List[NotificationSchema], tags=["Notifications"]
)
async def get_all_notifications():
    """Get all notifications."""
    return notification_methods.get_all()


# GET BY ID
@api_router.get(
    "/notifications/{notification_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=NotificationSchema,
    tags=["Notifications"],
)
async def get_notification(
    notification_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get notification by id."""
    return notification_methods.get_by_id(notification_id, current_user)


# UPDATE BY ID
@api_router.put(
    "/notifications/{notification_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=NotificationSchema,
    tags=["Notifications"],
)
async def update_notification(
    notification_id: str,
    notification_data: CreateNotificationSchema,
    current_user: User = Depends(get_current_active_user),
):
    """Update notification key by id."""
    return notification_methods.put(notification_id, notification_data, current_user)


# TODO: Adding placeholder until we determine if we still need this.
# GET 508 Banner: Doesn't require authentication
# @api_router.get("/notifications/508-banner", tags=["Notifications"])
# async def get_508_banner():
#     """Get notification by id."""
#     return notification_methods.get_508_banner()


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
    "/organizations/region_id/{region_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.GetOrganizationSchema],
    tags=["Organizations"],
)
async def get_organizations_by_region(
    region_id: str, current_user: User = Depends(get_current_active_user)
):
    """Retrieve organizations by region ID."""
    return organization.get_by_region(region_id, current_user)


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
    tags=["Organizations"],
)
@log_action(
    action="USER ASSIGNED",
    message_or_cb=lambda current_user, response, organization_id, user_data, **kwargs: {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "user_performed_assignment": serialize_user(current_user),
        "organization": serialize_organization(get_organization_sync(organization_id)),
        "role": user_data.role,
        "user": serialize_user(get_user_sync(user_data.user_id))
        if user_data.user_id
        else None,
    },
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
    response_model=OrganizationSchema.RemoveRoleResponseModel,
    tags=["Organizations"],
)
@log_action(
    action="USER ROLE REMOVED",
    message_or_cb=lambda current_user, response, organization_id, role_id, **kwargs: {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "user_performed_removal": serialize_user(current_user),
        "from_organization": serialize_organization(
            get_organization_sync(organization_id)
        ),
        "role_id": role_id,
        "removal_result": response,
    },
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
    response_model=OrganizationSchema.GetSingleOrganizationSchema,
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


@api_router.post(
    "/v2/organizations/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=OrganizationSchema.PaginatedOrganizationsResponse,
    tags=["Organizations"],
)
async def search_organizations_v2(
    payload: OrganizationSchema.OrganizationSearch,
    current_user: User = Depends(get_current_active_user),
):
    """Search organizations data grid."""
    return organization.search_organizations_v2(payload, current_user)


@api_router.post(
    "/search/organizations",
    dependencies=[Depends(get_current_active_user)],
    tags=["Organizations"],
)
async def search_organizations(
    search_body: OrganizationSchema.OrganizationSearchBody,
    current_user: User = Depends(get_current_active_user),
):
    """Search for organizations in Elasticsearch."""
    return organization.search_organizations_task(search_body, current_user)


# ========================================
#   Queue Monitoring Endpoints
# ========================================


@api_router.post(
    "/queues/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=QueueListResponse,
    tags=["Queues"],
)
async def search_queues(
    search_data: Optional[QueueSearch] = Body(None),
    current_user=Depends(get_current_active_user),
):
    """List SQS queues with metadata (message count, in-flight, delayed)."""
    return list_queues(search_data, current_user)


# ========================================
#   Region Endpoints
# ========================================


@api_router.get(
    "/regions",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema.RegionSchema],
    tags=["Regions"],
)
async def list_regions(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of all regions."""
    return organization.get_all_regions(current_user)


# ========================================
#   Saved Search  Endpoints
# ========================================


# Create a new saved search
@api_router.post(
    "/saved-searches",
    dependencies=[Depends(get_current_active_user)],
    response_model=SavedSearchSchema,
    tags=["Saved Searches"],
)
async def call_create_saved_search(
    saved_search: SavedSearchCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Create a new saved search."""
    request = {
        "name": saved_search.name,
        "count": saved_search.count,
        "sort_direction": saved_search.sort_direction,
        "sort_field": saved_search.sort_field,
        "search_term": saved_search.search_term,
        "search_path": saved_search.search_path,
        "filters": saved_search.filters,
        "created_by_id": current_user,
    }

    return create_saved_search(request)


# Get all existing saved searches
@api_router.get(
    "/saved-searches",
    dependencies=[Depends(get_current_active_user)],
    response_model=SavedSearchList,
    tags=["Saved Searches"],
)
async def call_list_saved_searches(user: User = Depends(get_current_active_user)):
    """Retrieve a list of all saved searches."""
    return list_saved_searches(user)


# Get individual saved search by ID
@api_router.get(
    "/saved-searches/{saved_search_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=SavedSearchSchema,
    tags=["Saved Searches"],
)
async def call_get_saved_search(
    saved_search_id: str, current_user: User = Depends(get_current_active_user)
):
    """Retrieve a saved search by its ID."""
    return get_saved_search(saved_search_id, current_user)


# Update saved search by ID
@api_router.put(
    "/saved-searches/{saved_search_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=SavedSearchUpdate,
    tags=["Saved Searches"],
)
async def call_update_saved_search(
    saved_search: SavedSearchUpdate,
    saved_search_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Update a saved search by its ID."""
    request = {
        "saved_search_id": saved_search_id,
        "name": saved_search.name,
        "count": saved_search.count,
        "search_term": saved_search.search_term,
        "sort_direction": saved_search.sort_direction,
        "sort_field": saved_search.sort_field,
        "search_path": saved_search.search_path,
        "filters": saved_search.filters,
    }

    return update_saved_search(request, current_user)


# Delete saved search by ID
@api_router.delete(
    "/saved-searches/{saved_search_id}",
    dependencies=[Depends(get_current_active_user)],
    tags=["Saved Searches"],
)
async def call_delete_saved_search(
    saved_search_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete a saved search by its ID."""
    return delete_saved_search(saved_search_id, current_user)


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
    """Manually run a scan by its ID."""
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
    search_data: Optional[scanTaskSchema.ScanTaskSearch] = Body(None),
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
    scan_task_id: UUID, current_user: User = Depends(get_current_active_user)
):
    """Kill a scan task."""
    return scan_tasks.kill_scan_task(scan_task_id, current_user)


@api_router.get(
    "/scan-tasks/{scan_task_id}/logs",
    dependencies=[Depends(get_current_active_user)],
    tags=["Scan Tasks"],
)
async def get_scan_task_logs(
    scan_task_id: UUID, current_user: User = Depends(get_current_active_user)
):
    """Get logs from a particular scan task."""
    return scan_tasks.get_scan_task_logs(scan_task_id, current_user)


@api_router.post(
    "/xpanse-sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=XpanseSyncResponse,
    tags=["Sync"],
)
async def xpanse_sync(
    sync_body: SyncBody,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Post organizations for datalake sync."""
    try:
        return await xpanse_sync_post(sync_body, request, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@api_router.post(
    "/sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=SyncResponse,
    tags=["Sync"],
)
async def sync(
    sync_body: SyncBody,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Post organizations for datalake sync."""
    await sync_post(sync_body, request, current_user)
    return SyncResponse(status="OK")


# ========================================
#   Search Endpoints
# ========================================


@api_router.post(
    "/pshtt_sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=SyncResponse,
    tags=["PshttSync"],
)
async def pshtt_sync(
    sync_body: SyncBody,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Post Pshtt results for datalake sync."""
    try:
        return await pshtt_sync_post(sync_body, request, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@api_router.post(
    "/dns_twist_sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=DnsTwistSyncResponse,
    tags=["Sync", "DnsTwist"],
)
async def dns_twist_sync(
    sync_body: DnsTwistSyncBody,
    request: Request,
    current_user: User = Depends(get_current_active_user),
):
    """Post domain permnutations for DNSTwist sync."""
    try:
        return await dns_twist_sync_post(sync_body, request, current_user)
    except Exception as e:
        LOGGER.error("Error occurred during DNSTwist sync: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@api_router.post(
    "/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=SearchResponse,
    tags=["Search"],
)
async def search(
    search_body: DomainSearchBody, current_user: User = Depends(get_current_active_user)
):
    """Get domains index from elastic search."""
    try:
        return await search_post(search_body, current_user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@api_router.post(
    "/search/export", dependencies=[Depends(get_current_active_user)], tags=["Search"]
)
async def export_endpoint(
    search_body: DomainSearchBody, current_user: User = Depends(get_current_active_user)
):
    """Search export endpoint."""
    try:
        result = await search_export(search_body, current_user)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
#   Stat Endpoints
# ========================================
@api_router.post(
    "/stats/trends",
    dependencies=[Depends(get_current_active_user)],
    response_model=stat_schema.VsTrendResponse,
    tags=["Stats"],
)
async def get_vs_trending_stats(
    filter_data: stat_schema.TrendStatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve VS Summary data filtered by the user."""
    return get_vs_trending_data(filter_data.filters, current_user)


@api_router.post(
    "/v2/stats/trends",
    dependencies=[Depends(get_current_active_user)],
    response_model=stat_schema.V2TrendResponse,
    response_model_exclude_none=True,
    tags=["Stats"],
)
async def get_v2_trending_stats(
    filter_data: stat_schema.V2TrendStatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve Summary data filtered by the user - V2."""
    result = get_v2_trending_data(filter_data, current_user)
    return result


@api_router.post(
    "/stats/condensed_trends",
    dependencies=[Depends(get_current_active_user)],
    response_model=stat_schema.VsTrendCondensedResponse,
    tags=["Stats"],
)
async def get_vs_condensed_trending_stats(
    filter_data: stat_schema.TrendStatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve VS Summary data filtered by the user."""
    return get_vs_condensed_trending_data(filter_data.filters, current_user)


@api_router.post(
    "/stats/compare",
    dependencies=[Depends(get_current_active_user)],
    response_model=stat_schema.StatsComparisonResponse,
    tags=["Stats"],
)
async def get_stats_comparison(
    filter_data: stat_schema.StatsComparisonPayloadSchema,
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve Summary Comparison between two dates provided by the user."""
    return get_stats_comparison_data(filter_data, current_user)


@api_router.post(
    "/stats",
    dependencies=[Depends(get_current_active_user)],
    response_model=stat_schema.StatsResponse,
    tags=["Stats"],
)
async def get_stats_combined(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    redis_client=Depends(get_redis_client),
):
    """Retrieve all stats from Elasticache filtered by user."""
    return await get_stats(filter_data, current_user, redis_client, request)


@api_router.post(
    "/services",
    response_model=List[stat_schema.ServiceStat],
    dependencies=[Depends(get_current_active_user)],
    tags=["Stats"],
)
async def post(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
    redis_client=Depends(get_redis_client),
):
    """Retrieve services from Elasticache filtered by user."""
    return await get_user_services_count(filter_data, current_user, redis_client)


@api_router.post(
    "/ports",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[stat_schema.PortStat],
    tags=["Stats"],
)
async def get_ports_stats(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
    redis_client=Depends(get_redis_client),
):
    """Retrieve Port Stats from Elasticache."""
    return await get_user_ports_count(filter_data, current_user, redis_client)


@api_router.post(
    "/num-vulns",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[stat_schema.VulnerabilityStat],
    tags=["Stats"],
)
async def get_num_vulns_stats(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Retrieve number of vulnerabilities stats from ElastiCache (Redis) filtered by user."""
    return await get_num_vulns(filter_data, current_user, redis_client)


@api_router.post(
    "/latest-vulns",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[stat_schema.LatestVulnerability],
    tags=["Stats"],
)
async def get_latest_vulnerabilities(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Get latest vulnerabilities."""
    return await stats_latest_vulns(filter_data, current_user, redis_client, request)


@api_router.post(
    "/most-common-vulns",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[stat_schema.MostCommonVulnerability],
    tags=["Stats"],
)
async def get_most_common_vulns(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Get most common vulns."""
    return await stats_most_common_vulns(
        filter_data, current_user, redis_client, request
    )


@api_router.post(
    "/severity-counts",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[stat_schema.SeverityCountStat],
    tags=["Stats"],
)
async def get_severity_counts(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Retrieve the count of open vulnerabilities grouped by severity from Redis."""
    return await get_severity_stats(filter_data, current_user, redis_client)


@api_router.post(
    "/by-org",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[stat_schema.ByOrgStat],
    tags=["Stats"],
)
async def get_by_org(
    filter_data: OrganizationSchema.StatsPayloadSchema,
    current_user: User = Depends(get_current_active_user),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Retrieve the count of open vulnerabilities grouped by severity from Redis."""
    return await get_by_org_stats(filter_data, current_user, redis_client)


# ========================================
#   Testing Endpoints
# ========================================


# Healthcheck endpoint
@api_router.get("/healthcheck", tags=["Testing"])
async def healthcheck():
    """
    Healthcheck endpoint.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "ok"}


# ========================================
#   User Endpoints
# ========================================


@api_router.post(
    "/users/me/acceptTerms",
    response_model=UserSchema,
    dependencies=[Depends(get_current_active_user_unsafe)],
    tags=["Users"],
)
async def call_accept_terms(
    version_data: VersionModel,
    current_user: User = Depends(get_current_active_user_unsafe),
):
    """Accept the latest terms of service."""
    return accept_terms(version_data, current_user)


@api_router.get("/users/me", tags=["Users"])
async def read_users_me(current_user: User = Depends(get_current_active_user_unsafe)):
    """Get current user."""
    return get_me(current_user)


@api_router.delete(
    "/users/{user_id}",
    response_model=OrganizationSchema.DeleteUserResponseModel,
    dependencies=[Depends(get_current_active_user_unsafe)],
    tags=["Users"],
)
@log_action(
    action="USER DENY/REMOVE",
    message_or_cb=lambda current_user, response, user_id, **kwargs: {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "user_performed_removal": serialize_user(current_user)
        if current_user
        else None,
        "removal_result": response,
    },
)
async def call_delete_user(
    user_id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete user."""
    return delete_user(user_id, current_user)


@api_router.get(
    "/users",
    response_model=List[UserResponseV2],
    dependencies=[Depends(get_current_active_user)],
    tags=["Users"],
)
async def call_get_users(current_user: User = Depends(get_current_active_user)):
    """Get all users."""
    return get_users(current_user)


@api_router.get(
    "/users/region_id/{region_id}",
    response_model=List[UserResponseV2],
    dependencies=[Depends(get_current_active_user)],
    tags=["Users"],
)
async def call_get_users_by_region_id(
    region_id, current_user: User = Depends(get_current_active_user)
):
    """Call get_users_by_region_id()."""
    return get_users_by_region_id(region_id, current_user)


@api_router.get(
    "/users/state/{state}",
    response_model=List[UserResponseV2],
    dependencies=[Depends(get_current_active_user)],
    tags=["Users"],
)
async def call_get_users_by_state(
    state, current_user: User = Depends(get_current_active_user)
):
    """Call get_users_by_state()."""
    return get_users_by_state(state, current_user)


@api_router.get(
    "/v2/users",
    response_model=List[UserResponseV2],
    dependencies=[Depends(get_current_active_user)],
    tags=["Users"],
)
async def call_get_users_v2(
    state: Optional[str] = Query(None),
    region_id: Optional[str] = Query(None),
    invite_pending: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """Get users with filter."""
    return get_users_v2(state, region_id, invite_pending, current_user)


@api_router.put(
    "/v2/users/{user_id}",
    dependencies=[Depends(get_current_active_user_unsafe)],
    response_model=UserResponseV2,
    tags=["Users"],
)
async def update_user_v2_view(
    user_id: str,
    user_data: UpdateUserV2,
    current_user: User = Depends(get_current_active_user_unsafe),
):
    """Update a particular user."""
    return update_user_v2(user_id, user_data, current_user)


@api_router.put(
    "/users/{user_id}/register/approve",
    dependencies=[Depends(get_current_active_user)],
    response_model=RegisterUserResponse,
    tags=["Users"],
)
@log_action(
    action="USER APPROVE",
    message_or_cb=lambda current_user, response, user_id, **kwargs: {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "user_performed_approval": serialize_user(current_user)
        if current_user
        else None,
        "user_to_approve": serialize_user(get_user_sync(user_id)) if user_id else None,
        "approval_result": response,
    },
)
async def register_approve(
    user_id: str, current_user: User = Depends(get_current_active_user)
):
    """Approve a registered user."""
    return user.approve_user_registration(user_id, current_user)


@api_router.put(
    "/users/{user_id}/register/deny",
    dependencies=[Depends(get_current_active_user)],
    response_model=RegisterUserResponse,
    tags=["Users"],
)
async def register_deny(
    user_id: str, current_user: User = Depends(get_current_active_user)
):
    """Deny a registered user."""
    return user.deny_user_registration(user_id, current_user)


@api_router.post(
    "/users",
    dependencies=[Depends(get_current_active_user)],
    response_model=NewUserResponseModel,
    tags=["Users"],
)
@log_action(
    action="USER INVITE",
    message_or_cb=lambda current_user, response, new_user, **kwargs: {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "user_performed_invite": serialize_user(current_user) if current_user else None,
        "invite_payload": new_user.dict() if new_user else None,
        "created_user_record": response,
    },
)
async def invite_user(
    new_user: NewUser, current_user: User = Depends(get_current_active_user)
):
    """Invite a user."""
    return user.invite(new_user, current_user)


# ========================================
#   Vulnerability Endpoints
# ========================================


@api_router.post(
    "/vulnerabilities/search",
    dependencies=[Depends(get_current_active_user)],
    response_model=VulnerabilitySearchResponse,
    tags=["Vulnerabilities"],
)
async def call_search_vulnerabilities(
    vulnerability_search: VulnerabilitySearch,
    current_user: User = Depends(get_current_active_user),
):
    """Search vulnerabilities."""
    vulnerabilities, count = search_vulnerabilities(vulnerability_search, current_user)

    if vulnerability_search.group_by:
        # Handle grouped results appropriately
        return VulnerabilitySearchResponse(result=vulnerabilities, count=count)

    try:
        enrich_kev_fields(vulnerabilities)

        # Convert each ORM instance to a Pydantic model
        result = [GetVulnerabilityResponse.model_validate(v) for v in vulnerabilities]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Serialization error: {}".format(str(e))
        )

    return VulnerabilitySearchResponse(result=result, count=count)


@api_router.post(
    "/vulnerabilities/export",
    dependencies=[Depends(get_current_active_user)],
    tags=["Vulnerabilities"],
)
async def get_export_vulnerabilities(
    vulnerability_search: VulnerabilitySearch,
    current_user: User = Depends(get_current_active_user),
):
    """Export vulnerabilities."""
    return export_vulnerabilities(vulnerability_search, current_user)


@api_router.get(
    "/vulnerabilities/{vulnerability_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=GetVulnerabilityResponse,
    tags=["Vulnerabilities"],
)
async def call_get_vulnerability_by_id(
    vulnerability_id, current_user: User = Depends(get_current_active_user)
):
    """Get vulnerability by id."""
    return get_vulnerability_by_id(vulnerability_id, current_user)


@api_router.get(
    "/v2/vulnerabilities/{vuln_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=GetV2VulnerabilityResponse,
    tags=["Vulnerabilities"],
)
async def v2_call_get_vulnerability_by_id(
    vuln_id: str = Path(..., description="Vulnerability ID"),
    history: Optional[bool] = Query(False, description="Include ticket history"),
    history_limit: Optional[int] = Query(
        None, gt=0, description="Limit for scan history"
    ),
    current_user: User = Depends(get_current_active_user),
):
    """Get vulnerability by id."""
    request = VulnByIdRequest(history=history, history_limit=history_limit)
    return v2_get_vulnerability_by_id(vuln_id, request, current_user)


@api_router.get(
    "/v2/vulnerability_details/{vulnerability_id}",
    dependencies=[Depends(get_current_active_user)],
    response_model=Union[
        CredBreachVulnerabilityResponse,
        VsVulnerabilityResponse,
        ShodanVulnerabiltyResponse,
    ],
    tags=["Vulnerabilities"],
)
async def get_vulnerability_by_source_id_route(
    vulnerability_id: str = Path(..., description="The ID of the vulnerability"),
    scan_source: Optional[str] = Query(None, description="Scan source (e.g. shodan)"),
    history: Optional[bool] = Query(False, description="Include ticket history"),
    history_limit: Optional[int] = Query(
        10, gt=0, description="Limit for scan history"
    ),
    current_user: User = Depends(get_current_active_user),
):
    """Get vulnerability details by Id: V2."""
    request = GetVulnerabilityByIdRequest(
        scan_source=scan_source, history=history, history_limit=history_limit
    )
    return get_vulnerability_by_scan_source_and_id(
        vulnerability_id=vulnerability_id,
        request=request,
        current_user=current_user,
    )


# TODO: Deprecated until frontend feature is re-enabled
# @api_router.put(
#     "/vulnerabilities/{vulnerability_id}",
#     dependencies=[Depends(get_current_active_user)],
#     response_model=VulnerabilitySchema,
#     tags=["Vulnerabilities"],
# )
# async def call_update_vulnerability(
#     vulnerability_id,
#     data: VulnerabilitySchema,
#     current_user: User = Depends(get_current_active_user),
# ):
#     """
#     Update vulnerability by id.

#     Returns:
#         object: a single vulnerability object that has been modified.
#     """
#     return update_vulnerability(vulnerability_id, data, current_user)


# ========================================
#   Blocklist Endpoints
# ========================================


@api_router.get(
    "/blocklist/check",
    dependencies=[Depends(get_current_active_user)],
    response_model=BlocklistCheckResponse,
    tags=["Blocklist"],
)
async def get_blocklist(
    request: Request,
    ip_address: str = Query(..., description="IP address to check"),
    current_user: User = Depends(get_current_active_user),
):
    """Determine if IP is on the blocklist."""
    return await handle_check_ip(ip_address, current_user)


# ========================================
#   DMZ Sync Endpoints
# ========================================


# --- Cybersixgill Sync endpoint, CRASM-2433 ---
@api_router.post(
    "/dmz_sync/cybersix_sync",
    response_model=CybersixSyncResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_active_user)],
    tags=["Cybersix sync to LZ mdl"],
)
async def get_call_all_cybersixgill(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    params: CybersixSyncParams = Body(default_factory=CybersixSyncParams),
):
    """
    Get all Cybersixgill data, paginated.

    - Only global write-admins may call this.
    - Returns a JSON payload plus an X-Salted-Checksum header.
    """
    # enforce write-admin access
    if not is_global_write_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access."
        )

    try:
        try:
            raw_json, checksum = await cybersix_module.fetch_cybersix_data(
                params, current_user
            )
        except TypeError:
            # pylint: disable=no-value-for-parameter
            raw_json, checksum = await cybersix_module.fetch_cybersix_data()
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error("Sync error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sync error: {}".format(e),
        )

    # attach checksum header
    response.headers["X-Salted-Checksum"] = checksum

    if isinstance(raw_json, dict) and "payload" in raw_json and "status" in raw_json:
        wrapper = raw_json
    else:
        # Otherwise wrap raw_json (which in tests is just the six lists) with default pagination fields
        payload = raw_json.copy()
        payload.setdefault("total_pages", 1)
        payload.setdefault("current_page", params.page)
        wrapper = {
            "status": "ok",
            "payload": payload,
        }

    return CybersixSyncResponse(**wrapper)


@api_router.get(
    "/dmz_sync/data_sources",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[DataSource],
    tags=["Data Sources"],
)
async def list_data_sources(current_user: User = Depends(get_current_active_user)):
    """Retrieve a list of all data sources."""
    return dmz_sync_methods.list_data_sources(current_user)


def serialize_custom(obj):
    """Recursively convert objects to JSON-serializable formats."""
    if isinstance(obj, (datetime, UUID)):
        return str(obj)  # Convert datetime and UUID to ISO 8601 string
    elif isinstance(obj, list):
        return [serialize_custom(item) for item in obj]  # Recursively process lists
    elif isinstance(obj, dict):
        return {
            key: serialize_custom(value) for key, value in obj.items()
        }  # Recursively process dicts
    return obj


# POST
@api_router.post(
    "/dmz_sync/asm_sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=AsmSyncResponse,
    tags=["DMZ Sync"],
)
async def asm_sync(
    asm_sync_data: SyncRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Return ASM_sync findings for a provided organization.

    This endpoint retrieves findings from the ASM (Attack Surface Management) sync process
    based on the input parameters provided. The response is serialized and includes a
    SHA-256 checksum in the headers for integrity verification.

    ### Request Body Parameters (SyncRequest):
    - **page** (int, default=1):
    Page number for pagination of the results.

    - **page_size** (int, optional, default=25):
    Number of records per page.

    - **acronym** (str):
    Organization acronym to filter the results.

    - **since_date** (datetime):
    Return results updated or found since this date.

    ### Headers:
    - **X-Salted-Checksum**:
    A SHA-256 hash of the salted response body for response integrity verification.

    ### Returns:
    - JSON response containing ASM findings and a checksum header.
    """
    response_data = dmz_sync_methods.dmz_asm_sync(asm_sync_data, current_user)
    # # response_json = json.dumps(response_data, sort_keys=True)
    # Convert response data to a JSON-serializable format
    response_serializable = serialize_custom(response_data)

    response_json = json.dumps(response_serializable, default=str, sort_keys=True)

    checksum = hashlib.sha256((SALT + response_json).encode()).hexdigest()

    return JSONResponse(
        content=response_serializable, headers={"X-Salted-Checksum": checksum}
    )


@api_router.post(
    "/dmz_sync/shodan_sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=ShodanSyncResponse,
    tags=["DMZ Sync"],
)
async def shodan_sync(
    shodan_data: SyncRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Return Shodan Assets and Vulns for a provided org with checksum verification."""
    response_data = dmz_sync_methods.dmz_shodan_sync(shodan_data, current_user)

    response_serializable = serialize_custom(response_data)

    # Consistent JSON encoding: sort keys to ensure deterministic output
    response_json_obj = {"status": "ok", "payload": response_serializable}
    json_str = json.dumps(response_json_obj, default=str, sort_keys=True)
    checksum = hashlib.sha256((SALT + json_str).encode()).hexdigest()
    return JSONResponse(
        content=response_json_obj, headers={"X-Salted-Checksum": checksum}
    )


@api_router.post(
    "/dmz_sync/censys_sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=CensysSyncResponse,
    tags=["DMZ Sync"],
)
async def censys_sync(
    censys_data: SyncRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Return Censys data for a provided org with checksum verification."""
    response_data = dmz_sync_methods.dmz_censys_sync(censys_data, current_user)

    response_serializable = serialize_custom(response_data)

    # Consistent JSON encoding: sort keys to ensure deterministic output
    response_json_obj = {"status": "ok", "payload": response_serializable}
    json_str = json.dumps(response_json_obj, default=str, sort_keys=True)
    checksum = hashlib.sha256((SALT + json_str).encode()).hexdigest()
    return JSONResponse(
        content=response_json_obj, headers={"X-Salted-Checksum": checksum}
    )


# POST
@api_router.post(
    "/dmz_sync/cred_sync",
    dependencies=[Depends(get_current_active_user)],
    response_model=CredSyncResponse,
    tags=["DMZ Sync"],
)
async def cred_sync(
    cred_sync_data: SyncRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Return Credential Breach findings for a provided organization.

    This endpoint retrieves credential breach findings from the DMZ
    based on the input parameters provided. The response is serialized and includes a
    SHA-256 checksum in the headers for integrity verification.

    ### Request Body Parameters (SyncRequest):
    - **page** (int, default=1):
    Page number for pagination of the results.

    - **page_size** (int, optional, default=25):
    Number of records per page.

    - **acronym** (str):
    Organization acronym to filter the results.

    - **since_date** (datetime):
    Return results updated or found since this date.

    ### Headers:
    - **X-Salted-Checksum**:
    A SHA-256 hash of the salted response body for response integrity verification.

    ### Returns:
    - JSON response containing credential breach findings and a checksum header.
    """
    response_data = dmz_sync_methods.dmz_cred_sync(cred_sync_data, current_user)

    # Convert response data to a JSON-serializable format
    response_serializable = serialize_custom(response_data)

    response_json = json.dumps(response_serializable, default=str, sort_keys=True)

    checksum = hashlib.sha256((SALT + response_json).encode()).hexdigest()

    return JSONResponse(
        content=response_serializable, headers={"X-Salted-Checksum": checksum}
    )


############################
# Object Store Endpoints  #
############################


# POST
@api_router.post(
    "/v1/object-store/presigned-url",
    dependencies=[Depends(get_current_active_user)],
    response_model=ObjectStorePresignedUrlResponse,
    tags=["Object Store"],
    summary="Generate a presigned URL for a given object",
)
def generate_presigned_object_store_url(
    body: ObjectStorePresignedUrlRequest, current_user=Depends(get_current_active_user)
) -> ObjectStorePresignedUrlResponse:
    """Generate an Object Store Presigned URL.

    Args:
        body (ObjectStorePresignedUrlRequest): _description_
        current_user (_type_, optional): _description_. Defaults to Depends(get_current_active_user).

    Returns:
        ObjectStorePresignedUrlResponse: _description_
    """
    return get_object_store_presigned_url(current_user, body)


# ==========================
# WAS Scan Endpoints  #
# ==========================


# POST
@api_router.post(
    "/was_scan_summaries",
    response_model=GetWasScanSummariesResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_active_user)],
    tags=["WAS Scan Summaries"],
)
async def get_was_scan_summaries_endpoint(
    response: Response,
    page: int = Query(1, ge=1, description="Which page to fetch (1-indexed)."),
    per_page: int = Query(100, ge=1, description="How many items per page."),
):
    """
    Return paginated WAS scan summaries plus an X‑Salted‑Checksum header for integrity.

    - `page` & `per_page` control pagination.
    - Only authenticated users may call this.
    """
    try:
        total_pages, records = await get_all_was_scan_summaries(
            page=page,
            per_page=per_page,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {error}",
        )

    # Serialize ORM objects to plain dicts
    payload = [
        WasScanSummarySchema.model_validate(record, from_attributes=True).model_dump()
        for record in records
    ]

    response_body = {
        "status": "ok",
        "payload": jsonable_encoder(payload),
        "total_pages": total_pages,
        "current_page": page,
    }

    return build_checksum_response(response_body, response, status.HTTP_200_OK)


# WAS Findings Sync
@api_router.post(
    "/dmz_sync/was_findings",
    response_model=GetAllWasFindingsResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_active_user)],
    tags=["WAS findings to sync to LZ db"],
)
async def get_call_all_was_findings(  # noqa: D401
    response: Response,
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Which page to fetch (1-indexed)."),
    per_page: int = Query(
        200, ge=1, le=1000, description="How many items per page (max 1000)."
    ),
    since_date: date
    | None = Query(
        default=None,
        description="Optional date filter (records last_detected >= this).",
    ),
):
    """
    Return paginated WAS findings plus an X-Salted-Checksum header for integrity.

    Notes:
    - Authorization is enforced via `is_global_write_admin`.
    - Pagination is controlled by `page` and `per_page`.
    - The response body is JSON-serializable and signed with a salted checksum header.
    """
    # Enforce write-admin access using the shared helper (no functional change)
    if not is_global_write_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access.",
        )

    try:
        queryset = get_was_findings_queryset(since_date)
        total_pages, records = paginate_queryset(queryset, page, per_page)
    except Exception as error:
        LOGGER.exception("Failed to build WAS findings page: %s", error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error: {}".format(error),
        ) from error

    payload_items = [
        WasFinding.model_validate(record, from_attributes=True) for record in records
    ]
    response_body = {
        "status": "ok",
        "payload": jsonable_encoder(payload_items),
        "total_pages": total_pages,
        "current_page": page,
    }

    # Keep the same 201 return and checksum behavior
    return build_checksum_response(response_body, response, status.HTTP_201_CREATED)
