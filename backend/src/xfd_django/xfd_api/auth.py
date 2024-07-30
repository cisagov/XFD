from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from xfd_api.jwt_utils import decode_jwt_token
from xfd_api.models import ApiKey, User
from hashlib import sha256

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
        return api_key_instance.userid
    except ApiKey.DoesNotExist:
        return None

def get_current_active_user(
    api_key: str = Security(api_key_header),
    token: str = Depends(oauth2_scheme)
):
    if api_key:
        user = get_user_by_api_key(api_key)
    else:
        user = decode_jwt_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return user
