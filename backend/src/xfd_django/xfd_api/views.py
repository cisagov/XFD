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
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .api_methods import api_key as api_key_methods
from .api_methods import auth as auth_methods
from .api_methods import notification as notification_methods
from .auth import get_current_active_user
from .login_gov import callback, login
from .models import Cpe, Cve, Domain, Organization, User, Vulnerability
from .schema_models.api_key import ApiKey as ApiKeySchema
from .schema_models.cpe import Cpe as CpeSchema
from .schema_models.cve import Cve as CveSchema
from .schema_models.domain import Domain as DomainSchema
from .schema_models.domain import DomainSearch
from .schema_models.notification import Notification as NotificationSchema
from .schema_models.organization import Organization as OrganizationSchema
from .schema_models.user import User as UserSchema
from .schema_models.vulnerability import Vulnerability as VulnerabilitySchema

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


@api_router.get(
    "/test-orgs",
    dependencies=[Depends(get_current_active_user)],
    response_model=List[OrganizationSchema],
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
    response_model=CpeSchema,
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
    response_model=CveSchema,
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
    response_model=CveSchema,
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
async def get_domain_by_id(domain_id: str):
    """
    Get domain by id.
    Returns:
        object: a single Domain object.
    """
    try:
        domain = Domain.objects.get(id=domain_id)
        return domain
    except Domain.DoesNotExist:
        raise HTTPException(status_code=404, detail="Domain not found.")
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
    response_model=VulnerabilitySchema,
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
    response_model=VulnerabilitySchema,
    tags="Update vulnerability",
)
async def update_vulnerability(vuln_id, data: VulnerabilitySchema):
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


######################
# Auth
######################


# Okta Callback
@api_router.post("/auth/okta-callback", tags=["auth"])
async def okta_callback(request: Request):
    """Handle Okta Callback."""
    return auth_methods.handle_okta_callback(request)


# Login
@api_router.get("/login", tags=["auth"])
async def login_route():
    """Handle V1 Login."""
    return login()


# V1 Callback
@api_router.post("/auth/callback", tags=["auth"])
async def callback_route(request: Request):
    """Handle V1 Callback."""
    body = await request.json()
    try:
        user_info = callback(body)
        return user_info
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


######################
# Users
######################


# GET Current User
@api_router.get("/users/me", tags=["users"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# V2 GET Users
@api_router.get(
    "/v2/users",
    tags=["users"],
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


# @api_router.post("/users/me/acceptTerms")
# async def accept_terms(request: Request):
#     user = await get_current_active_user(request)
#     user = get_object_or_404(User, id=user_id)
#     body = await request.json()

#     if not body:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body"
#         )

#     user.dateAcceptedTerms = datetime.utcnow()
#     user.acceptedTermsVersion = body.get("version")
#     user.save()

#     return JSONResponse(content=user.to_dict(), status_code=status.HTTP_200_OK)


######################
# API-Keys
######################


# POST
@api_router.post("/api-keys", response_model=ApiKeySchema, tags=["api-keys"])
async def create_api_key(current_user: User = Depends(get_current_active_user)):
    """Create api key."""
    return api_key_methods.post(current_user)


# DELETE
@api_router.delete("/api-keys/{id}", tags=["api-keys"])
async def delete_api_key(
    id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete api key by id."""
    return api_key_methods.delete(id, current_user)


# GET ALL
@api_router.get("/api-keys", response_model=List[ApiKeySchema], tags=["api-keys"])
async def get_all_api_keys(current_user: User = Depends(get_current_active_user)):
    """Get all api keys."""
    return api_key_methods.get_all(current_user)


# GET BY ID
@api_router.get("/api-keys/{id}", response_model=ApiKeySchema, tags=["api-keys"])
async def get_api_key(id: str, current_user: User = Depends(get_current_active_user)):
    """Get api key by id."""
    return api_key_methods.get_by_id(id, current_user)


#########################
#     Notifications
#########################


# POST
@api_router.post(
    "/notifications", response_model=NotificationSchema, tags=["notifications"]
)
async def create_notification(current_user: User = Depends(get_current_active_user)):
    """Create notification key."""
    # return notification_handler.post(current_user)
    return []


# DELETE
@api_router.delete(
    "/notifications/{id}", response_model=NotificationSchema, tags=["notifications"]
)
async def delete_notification(
    id: str, current_user: User = Depends(get_current_active_user)
):
    """Delete notification by id."""
    return notification_methods.delete(id, current_user)


# GET ALL
@api_router.get(
    "/notifications", response_model=List[NotificationSchema], tags=["notifications"]
)
async def get_all_notifications(current_user: User = Depends(get_current_active_user)):
    """Get all notifications."""
    return notification_methods.get_all(current_user)


# GET BY ID
@api_router.get(
    "/notifications/{id}", response_model=NotificationSchema, tags=["notifications"]
)
async def get_notification(
    id: str, current_user: User = Depends(get_current_active_user)
):
    """Get notification by id."""
    return notification_methods.get_by_id(id, current_user)


# UPDATE BY ID
@api_router.put("/notifications/{id}", tags=["notifications"])
async def update_notification(
    id: str, current_user: User = Depends(get_current_active_user)
):
    """Update notification key by id."""
    return notification_methods.delete(id, current_user)


# GET 508 Banner
@api_router.get("/notifications/508-banner", tags=["notifications"])
async def get_508_banner(current_user: User = Depends(get_current_active_user)):
    """Get notification by id."""
    return notification_methods.get_508_banner(current_user)
