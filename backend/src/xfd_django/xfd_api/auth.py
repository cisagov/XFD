"""
This module provides authentication utilities for the FastAPI application.

It includes functions to:
- Decode JWT tokens and retrieve the current user.
- Retrieve a user by their API key.
- Ensure the current user is authenticated and active.

Functions:
    - get_current_user: Decodes a JWT token to retrieve the current user.
    - get_user_by_api_key: Retrieves a user by their API key.
    - get_current_active_user: Ensures the current user is authenticated and active.

Dependencies:
    - fastapi
    - django
    - hashlib
    - .jwt_utils
    - .models
"""
# Standard Python Libraries
from datetime import datetime
from hashlib import sha256
import os
from re import A

# Third-Party Libraries
from django.utils import timezone
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import jwt
import requests

# from .jwt_utils import decode_jwt_token
from xfd_api.jwt_utils import JWT_ALGORITHM, create_jwt_token, decode_jwt_token
from xfd_api.models import ApiKey, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def update_or_create_user(user_info):
    try:
        user, created = User.objects.get_or_create(email=user_info["email"])
        if created:
            user.cognitoId = user_info["sub"]
            user.firstName = ""
            user.lastName = ""
            user.type = "standard"
            user.save()
        else:
            if user.cognitoId != user_info["sub"]:
                user.cognitoId = user_info["sub"]
            user.lastLoggedIn = datetime.utcnow()
            user.save()
        return user
    except Exception as e:
        print(f"Error : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


async def get_user_info_from_cognito(token):
    jwks_url = f"https://cognito-idp.us-east-1.amazonaws.com/{os.getenv('REACT_APP_USER_POOL_ID')}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    print(f"response from get_user_info_from_cognito: {str(response.json())}")
    response.raise_for_status()  # Ensure we raise an HTTPError for bad responses
    jwks = response.json()

    unverified_header = jwt.get_unverified_header(token)
    print(f"response from get_user_info_from_cognito: {str(response)}")
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)
    print(f"get_user_info_from+cognito public key: {str(public_key)}")

    user_info = decode_jwt_token(token)
    return user_info


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decode a JWT token to retrieve the current user.

    Args:
        token (str): The JWT token.

    Raises:
        HTTPException: If the token is invalid or expired.

    Returns:
        User: The user object decoded from the token.
    """
    user = decode_jwt_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


def get_user_by_api_key(api_key: str):
    """
    Retrieve a user by their API key.

    Args:
        api_key (str): The API key.

    Returns:
        User: The user object associated with the API key, or None if not found.
    """
    hashed_key = sha256(api_key.encode()).hexdigest()
    try:
        api_key_instance = ApiKey.objects.get(hashedKey=hashed_key)
        api_key_instance.lastused = timezone.now()
        api_key_instance.save(update_fields=["lastUsed"])
        return api_key_instance.userid
    except ApiKey.DoesNotExist:
        print("API Key not found")
        return None


# TODO: Uncomment the token and if not user token once the JWT from OKTA is working
def get_current_active_user(
    api_key: str = Security(api_key_header),
    # token: str = Depends(oauth2_scheme),
):
    """
    Ensure the current user is authenticated and active.

    Args:
        api_key (str): The API key.

    Raises:
        HTTPException: If the user is not authenticated.

    Returns:
        User: The authenticated user object.
    """
    user = None
    if api_key:
        user = get_user_by_api_key(api_key)
    # if not user and token:
    #     user = decode_jwt_token(token)
    if user is None:
        print("User not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    print(f"Authenticated user: {user.id}")
    return user


async def get_jwt_from_code(auth_code: str):
    domain = os.getenv("REACT_APP_COGNITO_DOMAIN")
    client_id = os.getenv("REACT_APP_COGNITO_CLIENT_ID")
    callback_url = os.getenv("REACT_APP_COGNITO_CALLBACK_URL")
    # callback_url = "http%3A%2F%2Flocalhost%2Fokta-callback"
    # scope = "openid email profile"
    scope = "openid"
    authorize_token_url = f"https://{domain}/oauth2/token"
    # logging.debug(f"Authorize token url: {authorize_token_url}")
    print(f"Authorize token url: {authorize_token_url}")
    # authorize_token_body = f"grant_type=authorization_code&client_id={client_id}&code={auth_code}&redirect_uri={callback_url}&scope={scope}"
    authorize_token_body = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": auth_code,
        "redirect_uri": callback_url,
        "scope": scope,
    }
    # logging.debug(f"Authorize token body: {authorize_token_body}")
    print(f"Authorize token body: {authorize_token_body}")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            authorize_token_url, headers=headers, data=authorize_token_body
        )
    except Exception as e:
        print(f"requests error: {e}")
    token_response = response.json()
    print(f"oauth2/token response: {token_response}")

    token_response = response.json()
    print(f"token response: {token_response}")
    id_token = token_response.get("id_token")
    print(f"ID token: {id_token}")
    # access_token = token_response.get("token_token")
    # refresh_token = token_response.get("refresh_token")

    # decoded_token = jwt.decode(id_token, algorithms=JWT_ALGORITHM, audience=client_id)
    decoded_token = jwt.decode(id_token, algorithms=["RS256"], audience=client_id)
    print(f"decoded token: {decoded_token}")
    return {"resp": True}


async def handle_cognito_callback(body):
    try:
        print(f"handle_cognito_callback body input: {str(body)}")
        user_info = await get_user_info_from_cognito(body["token"])
        print(f"handle_cognito_callback user_info: {str(user_info)}")
        user = await update_or_create_user(user_info)
        token = create_jwt_token(user)
        print(f"handle_cognito_callback token: {str(token)}")
        return token, user
    except Exception as error:
        print(f"Error : {str(error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error
