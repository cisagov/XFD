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
import hashlib
import secrets
from typing import List, Optional
import uuid

# Third-Party Libraries
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import model_serializer

from .auth import get_current_active_user, get_jwt_from_code, process_user
from .login_gov import login
from .models import ApiKey, Cpe, Cve, Domain, Organization, User, Vulnerability
from .schemas import Cpe as CpeSchema
from .schemas import Cve as CveSchema
from .schemas import Domain as DomainSchema
from .schemas import DomainSearch
from .schemas import Organization as OrganizationSchema
from .schemas import User as UserSchema
from .schemas import Vulnerability as VulnerabilitySchema

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


@api_router.get("/login")
async def login_route():
    login_data = login()
    return login_data


@api_router.post("/auth/callback")
async def callback_route(request: Request):
    body = await request.json()
    try:
        user_info = callback(body)
        return user_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @api_router.post("/auth/callback")
# async def callback_endpoint(request: Request):
#     body = request.json()
#     print(f"body: {body}")
# try:
#     if os.getenv("USE_COGNITO"):
#         token, user = await handle_cognito_callback(body)
#     else:
#         user_info = await handle_callback(body)
#         user = await update_or_create_user(user_info)
#         token = create_jwt_token(user)
#     return JSONResponse(content={"token": token, "user": user})
# except Exception as error:
#     raise HTTPException(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
#     ) from error


@api_router.post("/auth/okta-callback")
async def callback(request: Request):
    print(f"Request from /auth/okta-callback: {str(request)}")
    body = await request.json()
    print(f"Request json from callback: {str(request)}")
    print(f"Request json from callback: {body}")
    print(f"Body type: {type(body)}")
    code = body.get("code")
    print(f"Code: {code}")
    if not code:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code not found in request body",
        )
    jwt_data = await get_jwt_from_code(code)
    print(f"JWT Data: {jwt_data}")
    if jwt_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization code or failed to retrieve tokens",
        )
    access_token = jwt_data.get("access_token")
    refresh_token = jwt_data.get("refresh_token")
    decoded_token = jwt_data.get("decoded_token")

    resp = await process_user(decoded_token, access_token, refresh_token)
    token = resp.get("token")

    # print(f"Response from process_user: {json.dumps(resp)}")
    # Response(status_code=200, set("crossfeed-token", resp.get("token"))
    # return json.dumps(resp)
    # Create a JSONResponse object to return the response and set the cookie
    response = JSONResponse(
        content={"message": "User authenticated", "data": resp, "token": token}
    )
    response.body = resp
    # response.body = resp
    response.set_cookie(key="token", value=token)

    # Set the 'crossfeed-token' cookie
    response.set_cookie(
        key="crossfeed-token",
        value=token,
        # httponly=True,  # This makes the cookie inaccessible to JavaScript
        # secure=True,    # Ensures the cookie is only sent over HTTPS
        # samesite="Lax"  # Restricts when cookies are sent, adjust as necessary (e.g., "Strict" or "None")
    )
    return response


# @api_router.post("/auth/login")
# async def login_endpoint():
#     print(f"Returning auth/login response")
#     # result = await get_login_gov()
#     # return JSONResponse(content=result)


# @api_router.get("/login")
# async def login_route():
#     login_data = login()
#     return login_data


# @api_router.post("/auth/callback")
# async def callback_route(request: Request):
#     body = await request.json()
#     try:
#         user_info = callback(body)
#         return user_info
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @api_router.post("/auth/callback")
# async def callback_endpoint(request: Request):
#     body = request.json()
#     print(f"body: {body}")
# try:
#     if os.getenv("USE_COGNITO"):
#         token, user = await handle_cognito_callback(body)
#     else:
#         user_info = await handle_callback(body)
#         user = await update_or_create_user(user_info)
#         token = create_jwt_token(user)
#     return JSONResponse(content={"token": token, "user": user})
# except Exception as error:
#     raise HTTPException(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
#     ) from error


# @api_router.post("/auth/okta-callback")
# async def callback(request: Request):
#     print(f"Request from /auth/okta-callback: {str(request)}")
#     body = await request.json()
#     print(f"Request json from callback: {str(request)}")
#     print(f"Request json from callback: {body}")
#     print(f"Body type: {type(body)}")
#     code = body.get("code")
#     print(f"Code: {code}")
#     if not code:
#         return HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Code not found in request body",
#         )
#     jwt_data = await get_jwt_from_code(code)
#     print(f"JWT Data: {jwt_data}")
#     if jwt_data is None:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid authorization code or failed to retrieve tokens",
#         )
#     access_token = jwt_data.get("access_token")
#     refresh_token = jwt_data.get("refresh_token")
#     decoded_token = jwt_data.get("decoded_token")

#     resp = await process_user(decoded_token, access_token, refresh_token)
#     token = resp.get("token")

#     # print(f"Response from process_user: {json.dumps(resp)}")
#     # Response(status_code=200, set("crossfeed-token", resp.get("token"))
#     # return json.dumps(resp)
#     # Create a JSONResponse object to return the response and set the cookie
#     response = JSONResponse(content={"message": "User authenticated", "data": resp, "token": token})
#     response.body = resp
#     # response.body = resp
#     response.set_cookie(key="token", value=token)

#     # Set the 'crossfeed-token' cookie
#     response.set_cookie(
#         key="crossfeed-token",
#         value=token,
#         # httponly=True,  # This makes the cookie inaccessible to JavaScript
#         # secure=True,    # Ensures the cookie is only sent over HTTPS
#         # samesite="Lax"  # Restricts when cookies are sent, adjust as necessary (e.g., "Strict" or "None")
#     )

#     return response


# @api_router.get("/users/me", response_model=User)
# async def get_me(request: Request):
#     user = get_current_active_user(request)
#     return user


@api_router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# @api_router.post("/users/me/acceptTerms")
# async def accept_terms(request: Request):
#     user = await get_current_active_user(request)
#     user = get_object_or_404(User, id=user_id)
#     body = await request.json()

#     if not body:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request body")

#     user.dateAcceptedTerms = datetime.utcnow()
#     user.acceptedTermsVersion = body.get('version')
#     user.save()

#     return JSONResponse(content=user.to_dict(), status_code=status.HTTP_200_OK)
#
#
# @api_router.post("/users/me/acceptTerms")
# async def accept_terms(
#     version: str, current_user: User = Depends(get_current_active_user)
# ):
#     current_user.date_accepted_terms = datetime.utcnow()
#     current_user.accepted_terms_version = version
#     current_user.save()
#     return current_user


# POST /apikeys/generate
@api_router.post("/api-keys")
async def generate_api_key(current_user: User = Depends(get_current_active_user)):
    """
    Generate API key for user

    Args:
        current_user (User, optional): _description_. Defaults to Depends(get_current_active_user).

    Returns:
        dict: ApiKey model dict
    """
    # Generate a random 16-byte API key
    key = secrets.token_hex(16)

    # Hash the API key
    hashed_key = hashlib.sha256(key.encode()).hexdigest()

    # Create the ApiKey record in the database
    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashedKey=hashed_key,
        lastFour=key[-4:],  # Store the last four characters of the key
        userId=current_user,
    )

    # Return the API key to the user (Do NOT store the plain key in the database)
    return {
        "id": api_key.id,
        "status": "success",
        "api_key": key,
        "last_four": api_key.lastFour,
    }


# DELETE /apikeys/{keyId}
@api_router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str, current_user: User = Depends(get_current_active_user)
):
    try:
        # Validate that key_id is a valid UUID
        uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid API Key ID"
        )

    # Try to find the ApiKey by key_id and current user
    try:
        api_key = ApiKey.objects.get(id=key_id, userId=current_user)
    except ApiKey.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found"
        )

    # Delete the API Key
    api_key.delete()
    return {"status": "success", "message": "API Key deleted successfully"}


@api_router.get("/api-keys")
async def get_api_keys():
    """
    Get all API keys.

    Returns:
        list: A list of all API keys.
    """
    try:
        api_keys = ApiKey.objects.all()
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
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@api_router.post("/notifications")
async def create_notification():
    """
    Create Notification
    """
    return []


@api_router.get("/notifications")
async def get_all_notifications():
    """
    Get All Notifications
    """
    return []


@api_router.get("/notifications/{id}")
async def get_notification():
    """
    Get Notification by id
    """
    return []


@api_router.put("/notifications/{id}")
async def update_notifications():
    """
    Update Notification
    """
    return []


@api_router.delete("/notifications/{id}")
async def delete_notifications():
    """
    Delete Notification
    """
    return []


@api_router.get("/notifications/508-banner")
async def notification_banner():
    """ """
    return ""
