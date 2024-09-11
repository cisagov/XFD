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
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from .auth import get_current_active_user, get_jwt_from_code, handle_cognito_callback, process_user
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


@api_router.post("/auth/login")
async def login_endpoint():
    print(f"Returning auth/login response")
    # result = await get_login_gov()
    # return JSONResponse(content=result)


@api_router.post("/auth/callback")
async def callback_endpoint(request: Request):
    body = request.json()
    print(f"body: {body}")
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
    # if not code:
    #     return HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Code not found in request body",
    #     )
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

    return await process_user(decoded_token, access_token, refresh_token)
    # try:
    #     token_endpoint = f"https://{domain}/oauth2/token"
    #     token_data = (
    #         f"grant_type=authorization_code&client_id={client_id}&code={code}"
    #         f"&redirect_uri={callback_url}&scope=openid"
    #     )

    #     response = requests.post(
    #         token_endpoint,
    #         headers={'Content-Type': 'application/x-www-form-urlencoded'},
    #         data=token_data
    #     )

    #     # Assuming the response is in JSON format
    #     response_json = response.json()
    #     id_token = response_json.get('id_token')
    #     access_token = response_json.get('access_token')
    #     refresh_token = response_json.get('refresh_token')

    #     print(f"id_token: {id_token}")
    #     print(f"access_token: {access_token}")
    #     print(f"refresh_token: {refresh_token}")

    #     # return JSONResponse(content={"token": access_token, "user": user}, status_code=status.HTTP_200_OK)
    #     return response_json
    # except HTTPException as e:
    #     raise HTTPException(status_code=e.status_code, detail=e.detail)


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
