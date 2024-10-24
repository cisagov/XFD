"""Authentication utilities for the FastAPI application."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import hashlib
from hashlib import sha256
import os
from urllib.parse import urlencode
import uuid
from typing import Optional

# Third-Party Libraries
from django.conf import settings
from django.forms.models import model_to_dict
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
import requests

# from .helpers import user_to_dict
from .models import ApiKey, Organization, OrganizationTag, Role, User

# JWT_ALGORITHM = "RS256"
JWT_SECRET = os.getenv("JWT_SECRET")
SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_TIMEOUT_HOURS = 4

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


def user_to_dict(user):
    """Takes a user model object from django and
    sanitizes fields for output.

    Args:
        user (django model): Django User model object

    Returns:
        dict: Returns sanitized and formated dict
    """
    user_dict = model_to_dict(user)  # Convert model to dict
    # Convert any UUID fields to strings
    if isinstance(user_dict.get("id"), uuid.UUID):
        user_dict["id"] = str(user_dict["id"])
    for key, val in user_dict.items():
        if isinstance(val, datetime):
            user_dict[key] = str(val)
    return user_dict


def create_jwt_token(user):
    """
    Create a JWT token for a given user.

    Args:
        user (User): The user object for whom the token is created.

    Returns:
        str: The encoded JWT token.
    """
    payload = {
        "id": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_TIMEOUT_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token):
    """
    Decode a JWT token to retrieve the user.

    Args:
        token (str): The JWT token to decode.

    Returns:
        User: The user object decoded from the token, or None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithm=JWT_ALGORITHM)
        user = User.objects.get(id=payload["id"])
        return user
    except (ExpiredSignatureError, InvalidTokenError, User.DoesNotExist):
        return None


def hash_key(key: str) -> str:
    """
    Helper to hash API key.

    Returns:
        str: hashed API key value
    """
    return hashlib.sha256(key.encode()).hexdigest()


# TODO: Confirm still needed
# async def get_user_info_from_cognito(token):
#     """
#     Get user info from cognito

#     Args:
#         token (_type_): _description_

#     Returns:
#         _type_: _description_
#     """
#     jwks_url = f"https://cognito-idp.us-east-1.amazonaws.com/{os.getenv('REACT_APP_USER_POOL_ID')}/.well-known/jwks.json"
#     response = requests.get(jwks_url)
#     jwks = response.json()
#     unverified_header = jwt.get_unverified_header(token)

#     for key in jwks["keys"]:
#         if key["kid"] == unverified_header["kid"]:
#             rsa_key = {
#                 "kty": key["kty"],
#                 "kid": key["kid"],
#                 "use": key["use"],
#                 "n": key["n"],
#                 "e": key["e"],
#             }

#     user_info = decode_jwt_token(token)
#     return user_info


# def create_jwt_token(user):
#     """
#     Create a JWT token for a given user.

#     Args:
#         user (User): The user object for whom the token is created.

#     Returns:
#         str: The encoded JWT token.
#     """
#     payload = {
#         "id": str(user.id),
#         "email": user.email,
#         "exp": datetime.now(datetime.timezone.utc) + timedelta(hours=JWT_TIMEOUT_HOURS),
#     }
#     return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# def decode_jwt_token(token):
#     """
#     Decode a JWT token to retrieve the user.

#     Args:
#         token (str): The JWT token to decode.

#     Returns:
#         User: The user object decoded from the token, or None if invalid or expired.
#     """
#     try:
#         payload = jwt.decode(token, JWT_SECRET, algorithm=JWT_ALGORITHM)
#         user = User.objects.get(id=payload["id"])
#         return user
#     except (ExpiredSignatureError, InvalidTokenError, User.DoesNotExist):
#         return None


# def hash_key(key: str) -> str:
#     """
#     Helper to hash API key.

#     Returns:
#         str: hashed API key value
#     """
#     return hashlib.sha256(key.encode()).hexdigest()


# TODO: Confirm still needed
async def get_user_info_from_cognito(token):
    """Get user info from cognito."""
    jwks_url = f"https://cognito-idp.us-east-1.amazonaws.com/{os.getenv('REACT_APP_USER_POOL_ID')}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    jwks = response.json()
    unverified_header = jwt.get_unverified_header(token)

    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }

    user_info = decode_jwt_token(token)
    return user_info


def get_user_by_api_key(api_key: str):
    """Get a user by their API key."""
    hashed_key = sha256(api_key.encode()).hexdigest()
    try:
        api_key_instance = ApiKey.objects.get(hashedKey=hashed_key)
        api_key_instance.lastUsed = datetime.now(timezone.utc)
        api_key_instance.save(update_fields=["lastUsed"])
        return api_key_instance.userId
    except ApiKey.DoesNotExist:
        print("API Key not found")
        return None


def get_current_active_user(
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(oauth2_scheme)
):
    """Ensure the current user is authenticated and active."""
    user = None
    if api_key:
        user = get_user_by_api_key(api_key)
    else:
        try:
            # Decode token in Authorization header to get user
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("id")

            if user_id is None:
                print("No user ID found in token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Fetch the user by ID from the database
            user = User.objects.get(id=user_id)
        except jwt.ExpiredSignatureError:
            print("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            print("Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    if user is None:
        print("User not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user


async def process_user(decoded_token, access_token, refresh_token):
    # Find the user by email
    user = User.objects.filter(email=decoded_token["email"]).first()

    if not user:
        # Create a new user if they don't exist from Okta fields in SAML Response
        user = User(
            email=decoded_token["email"],
            oktaId=decoded_token["sub"],
            firstName=decoded_token.get("given_name"),
            lastName=decoded_token.get("family_name"),
            userType="standard",
            invitePending=True,
        )
        user.save()
    else:
        # Update user oktaId (legacy users) and login time
        user.oktaId = decoded_token["sub"]
        user.lastLoggedIn = datetime.now()
        user.save()

    # # Create response object
    # response = JSONResponse({"message": "User processed"})

    # # Set cookies for access token and refresh token
    # response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True)
    # response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True)
    # print(f"Response output: {str(response.headers)}")

    # If user exists, generate a signed JWT token
    if user:
        if not JWT_SECRET:
            raise HTTPException(status_code=500, detail="JWT_SECRET is not defined")

        # Generate JWT token
        signed_token = jwt.encode(
            {
                "id": str(user.id),
                "email": user.email,
                "exp": datetime.utcnow() + timedelta(hours=JWT_TIMEOUT_HOURS),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        # Set JWT token as a cookie
        # response.set_cookie(key="id_token", value=signed_token, httponly=True, secure=True)

        # Return the response with token and user info
        # return JSONResponse(

        process_resp = {
            "token": signed_token,
            "user": user_to_dict(user)
            # "user": {
            #     "id": str(user.id),
            #     "email": user.email,
            #     "firstName": user.firstName,
            #     "lastName": user.lastName,
            #     "state": user.state,
            #     "regionId": user.regionId,
            # }
        }
        print(f"process_resp: {process_resp}")
        return process_resp

    else:
        raise HTTPException(status_code=400, detail="User not found")


async def get_jwt_from_code(auth_code: str):
    try:
        callback_url = os.getenv("REACT_APP_COGNITO_CALLBACK_URL")
        client_id = os.getenv("REACT_APP_COGNITO_CLIENT_ID")
        domain = os.getenv("REACT_APP_COGNITO_DOMAIN")
        scope = "openid"
        authorize_token_url = f"https://{domain}/oauth2/token"
        authorize_token_body = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": auth_code,
            "redirect_uri": callback_url,
            "scope": scope,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        # Make Oauth2/token request with code
        response = requests.post(
            authorize_token_url, headers=headers, data=urlencode(authorize_token_body)
        )
        token_response = response.json()
        print(f"oauth2/token response: {token_response}")

        # Convert the id_token to bytes
        id_token = token_response["id_token"].encode("utf-8")
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")

        # Decode the token without verifying the signature (if needed)
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        print(f"decoded token: {decoded_token}")

        return {
            "refresh_token": refresh_token,
            "id_token": id_token,
            "access_token": access_token,
            "decoded_token": decoded_token,
        }

    except Exception as error:
        print(f"get_jwt_from_code post error: {error}")
        pass


# TODO: determine if we still need.
# async def handle_cognito_callback(body):
#     try:
#         print(f"handle_cognito_callback body input: {str(body)}")
#         user_info = await get_user_info_from_cognito(body["token"])
#         print(f"handle_cognito_callback user_info: {str(user_info)}")
#         user = await update_or_create_user(user_info)
#         token = create_jwt_token(user)
#         print(f"handle_cognito_callback token: {str(token)}")
#         return token, user
#     except Exception as error:
#         print(f"Error : {str(error)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
#         ) from error


# # TODO: Uncomment the token and if not user token once the JWT from OKTA is working
# def get_current_active_user(
#     api_key: str = Security(api_key_header),
#     # token: str = Depends(oauth2_scheme),
# ):
#     """Ensure the current user is authenticated and active."""
#     user = None
#     if api_key:
#         user = get_user_by_api_key(api_key)
#     # if not user and token:
#     #     user = decode_jwt_token(token)
#     if user is None:
#         print("User not authenticated")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#         )
#     print(f"Authenticated user: {user.id}")
#     return user


def is_global_write_admin(current_user) -> bool:
    """Check if the user has global write admin permissions."""
    return current_user and current_user.userType == "globalAdmin"


def is_global_view_admin(current_user) -> bool:
    """Check if the user has global view permissions."""
    return current_user and current_user.userType in ["globalView", "globalAdmin"]


def is_regional_admin(current_user) -> bool:
    """Check if the user has regional admin permissions."""
    return current_user and current_user.userType in ["regionalAdmin", "globalAdmin"]


def is_org_admin(current_user, organization_id) -> bool:
    """Check if the user is an admin of the given organization."""
    if not organization_id:
        return False

    # Check if the user has an admin role in the given organization
    for role in current_user.roles.all():
        if str(role.organization.id) == str(organization_id) and role.role == "admin":
            return True

    # If the user is a global write admin, they are considered an org admin
    return is_global_write_admin(current_user)


def is_regional_admin_for_organization(current_user, organization_id) -> bool:
    """Check if user is a regional admin and if a selected organization belongs to their region."""
    if not organization_id:
        return False

    # Check if the user is a regional admin
    if is_regional_admin(current_user):
        # Check if the organization belongs to the user's region
        user_region_id = (
            current_user.regionId
        )  # Assuming this is available in the user object
        organization_region_id = get_organization_region(
            organization_id
        )  # Function to fetch the organization's region
        return user_region_id == organization_region_id

    return False


def get_organization_region(organization_id: str) -> str:
    """Fetch the region ID for the given organization."""
    organization = Organization.objects.get(id=organization_id)
    return organization.regionId


def get_tag_organizations(current_user, tag_id: str) -> list[str]:
    """Returns the organizations belonging to a tag, if the user can access the tag."""
    # Check if the user is a global view admin
    if not is_global_view_admin(current_user):
        return []

    # Fetch the OrganizationTag and its related organizations
    tag = (
        OrganizationTag.objects.prefetch_related("organizations")
        .filter(id=tag_id)
        .first()
    )
    if tag:
        # Return a list of organization IDs
        return [org.id for org in tag.organizations.all()]

    # Return an empty list if tag is not found
    return []


def get_org_memberships(current_user) -> list[str]:
    """Returns the organization IDs that a user is a member of."""
    roles = Role.objects.filter(user=current_user)
    if not roles:
        return []
    return [role.organization.id for role in roles if role.organization]
