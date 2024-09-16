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
from hashlib import sha256

# Third-Party Libraries
from django.utils import timezone
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from .jwt_utils import decode_jwt_token
from .models import ApiKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


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
        api_key_instance.lastUsed = timezone.now()
        api_key_instance.save(update_fields=["lastUsed"])
        return api_key_instance.userId
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
