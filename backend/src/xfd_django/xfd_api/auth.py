from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from hashlib import sha256
from .jwt_utils import decode_jwt_token
from .models import ApiKey, User
from django.utils import timezone

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_jwt_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user

def get_user_by_api_key(api_key: str):
    hashed_key = sha256(api_key.encode()).hexdigest()
    try:
        api_key_instance = ApiKey.objects.get(hashedkey=hashed_key)
        api_key_instance.lastused = timezone.now()
        api_key_instance.save(update_fields=['lastused'])
        return api_key_instance.userid
    except ApiKey.DoesNotExist:
        print("API Key not found")
        return None

# TODO: Uncomment the token and if not user token once the JWT from OKTA is working
def get_current_active_user(
    api_key: str = Security(api_key_header),
    # token: str = Depends(oauth2_scheme),
):
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
