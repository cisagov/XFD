"""
Api-keys API.

"""

# Third-Party Libraries
from fastapi import HTTPException

from ..models import ApiKey


def get_api_keys():
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
                "createdAt": api_key.createdAt,
                "updatedAt": api_key.updatedAt,
                "lastUsed": api_key.lastUsed,
                "hashedKey": api_key.hashedKey,
                "lastFour": api_key.lastFour,
                "userId": api_key.userId.id if api_key.userId else None,
            }
            for api_key in api_keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
