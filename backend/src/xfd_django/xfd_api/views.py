

from django.shortcuts import render

# Third party imports
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Security,
    UploadFile,
    status,
)
from .models import ApiKey

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


@api_router.get("/apikeys")
async def get_api_keys():
    """
    Get all API keys.

    Returns:
        list: A list of all API keys.
    """
    try:
        print("API KEYS!!!!!!")
        api_keys = ApiKey.objects.all()
        # return api_keys
        return [
            {
                "id": api_key.id,
                "created_at": api_key.createdat,
                "updated_at": api_key.updatedat,
                "last_used": api_key.lastused,
                "hashed_key": api_key.hashedkey,
                "last_four": api_key.lastfour,
                "user_id": api_key.userid.id if api_key.userid else None,
            }
            for api_key in api_keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))