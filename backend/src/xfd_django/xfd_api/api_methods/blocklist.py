"""Blocklist API."""

# Standard Python Libraries
import ipaddress

# Third-Party Libraries
from fastapi import HTTPException
from xfd_mini_dl.models import Blocklist

from ..auth import is_global_view_admin


async def handle_check_ip(ip_address: str, current_user):
    """
    Determine if an IP exists in our blocklist table.

    Returns:
        { reports: int, attacks: int }
    """
    try:
        # Validate the IP address format
        ipaddress.ip_address(ip_address)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address")
    attacks = 0
    reports = 0
    try:
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")
        record = Blocklist.objects.get(ip=ip_address)
        if isinstance(record.attacks, int) and record.attacks > 0:
            attacks = record.attacks
        if isinstance(record.reports, int) and record.reports > 0:
            reports = record.reports
        return {
            "attacks": attacks,
            "reports": reports,
        }
    except HTTPException as http_exc:
        raise http_exc
    except Blocklist.DoesNotExist:
        return {
            "attacks": 0,
            "reports": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
