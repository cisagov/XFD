"""Blocklist API."""

# Standard Python Libraries
import ipaddress

# Third-Party Libraries
from fastapi import HTTPException
from xfd_mini_dl.models import Blocklist

from ..auth import is_global_view_admin


async def handle_bulk_check_ips(ip_addresses: list[str], current_user):
    """
    Determing if multiple IP's exist within our blocklist table.

    Returns: {
        ip_address: {
            reports: int,
            attacks: int
        }
    }
    """
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")
    results = {}
    for ip in ip_addresses:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid IP address: {ip}")
        attacks = 0
        reports = 0
        try:
            record = Blocklist.objects.get(ip=ip)
            if isinstance(record.attacks, int) and record.attacks > 0:
                attacks = record.attacks
            if isinstance(record.reports, int) and record.reports > 0:
                reports = record.reports
            results[ip] = {
                "attacks": attacks,
                "reports": reports,
            }
        except HTTPException as http_exc:
            raise http_exc
        except Blocklist.DoesNotExist:
            results[ip] = {
                "attacks": 0,
                "reports": 0,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return results
