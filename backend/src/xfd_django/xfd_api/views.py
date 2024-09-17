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
import hashlib
from http.client import HTTPResponse
import json
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from .login_gov import login

from .auth import get_current_active_user, get_jwt_from_code, process_user
from .models import ApiKey, Organization, User

api_router = APIRouter()


@api_router.get("/notifications")
async def notifications():
    """ """
    return []


@api_router.get("/notifications/508-banner")
async def notification_banner():
    """ """
    return ""


# Healthcheck endpoint
@api_router.get("/healthcheck")
async def healthcheck():
    """
    Healthcheck endpoint.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "ok2"}


# Endpoint to read organizations
@api_router.get(
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


# @api_router.post("/auth/login")
# async def login_endpoint():
#     print(f"Returning auth/login response")
#     # result = await get_login_gov()
#     # return JSONResponse(content=result)


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
    response = JSONResponse(content={"message": "User authenticated", "data": resp, "token": token})
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


# @api_router.get("/users/me", response_model=User)
# async def get_me(request: Request):
#     user = get_current_active_user(request)
#     return user

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


@api_router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# @api_router.post("/users/me/acceptTerms")
# async def accept_terms(
#     version: str, current_user: User = Depends(get_current_active_user)
# ):
#     current_user.date_accepted_terms = datetime.utcnow()
#     current_user.accepted_terms_version = version
#     current_user.save()
#     return current_user

# Helper function to hash the API key
def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# POST /apikeys/generate
@api_router.post("/api-keys")
async def generate_api_key(current_user: User = Depends(get_current_active_user)):
    # Generate a random 16-byte API key
    key = secrets.token_hex(16)

    # Hash the API key
    hashed_key = hash_key(key)

    # Create the ApiKey record in the database
    api_key = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashedKey=hashed_key,
        lastFour=key[-4:],  # Store the last four characters of the key
        userId=current_user
    )

    # Return the API key to the user (Do NOT store the plain key in the database)
    return {
        "id": api_key.id,
        "status": "success",
        "api_key": key,
        "last_four": api_key.lastFour
    }


# DELETE /apikeys/{keyId}
@api_router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, current_user: User = Depends(get_current_active_user)):
    try:
        # Validate that key_id is a valid UUID
        uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid API Key ID")

    # Try to find the ApiKey by key_id and current user
    try:
        api_key = ApiKey.objects.get(id=key_id, userId=current_user)
    except ApiKey.DoesNotExist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found")

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
