# xfd_api/jwt_utils.py
"""
This module provides utilities for creating and decoding JWT tokens for the xfd_django project.

Functions:
    - create_jwt_token: Create a JWT token for a given user.
    - decode_jwt_token: Decode a JWT token to retrieve the user.

Dependencies:
    - jwt
    - datetime
    - django.conf.settings
    - django.contrib.auth.get_user_model
"""
# Standard Python Libraries
from datetime import datetime, timedelta

# Third-Party Libraries
from django.conf import settings
from django.contrib.auth import get_user_model
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

User = get_user_model()
SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = "RS256"


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
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_jwt_token(token):
    """
    Decode a JWT token to retrieve the user.

    Args:
        token (str): The JWT token to decode.

    Returns:
        User: The user object decoded from the token, or None if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.objects.get(id=payload["id"])
        return user
    except (ExpiredSignatureError, InvalidTokenError, User.DoesNotExist):
        return None
