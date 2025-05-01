"""Blocklist API."""

# Third-Party Libraries
from fastapi import HTTPException
from xfd_mini_dl.models import Blocklist

from ..auth import is_global_view_admin


async def handle_check_ip(ip_address: str, current_user):
    """
    Determine if an IP exists in our blocklist table.

    Returns:
        { status: "BLOCKED" or "UNBLOCKED" }
    """
    try:
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")
        Blocklist.objects.get(ip=ip_address)
        return {"status": "BLOCKED"}
    except HTTPException as http_exc:
        raise http_exc
    except Blocklist.DoesNotExist:
        return {"status": "UNBLOCKED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
