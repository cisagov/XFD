"""Blocklist API."""

# Standard Python Libraries
import ipaddress
import logging

# Third-Party Libraries
from fastapi import HTTPException
from xfd_mini_dl.models import Blocklist

from ..auth import is_global_view_admin

LOGGER = logging.getLogger(__name__)


async def handle_bulk_check_ips(ip_addresses: list[str], current_user):
    """
    Determine if multiple IP's exist within our blocklist table.

    Returns: {
        ip_address: {
            reports: int,
            attacks: int
        }
    }
    """
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Validate all IPs first
    for ip in ip_addresses:
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            LOGGER.error("Invalid IP address provided: %s", ip)
            raise HTTPException(status_code=400, detail="Invalid IP address")

    # Initialize results with defaults for all IPs
    results = {str(ip): {"attacks": 0, "reports": 0} for ip in ip_addresses}

    # Single query to fetch all matching records
    records = Blocklist.objects.filter(ip__in=ip_addresses)
    for record in records:
        LOGGER.info("Processing blocklist record for IP: %s", record.ip)
        attacks = (
            record.attacks
            if isinstance(record.attacks, int) and record.attacks > 0
            else 0
        )
        reports = (
            record.reports
            if isinstance(record.reports, int) and record.reports > 0
            else 0
        )
        ip_str = str(ipaddress.ip_interface(record.ip).ip)
        results[ip_str] = {
            "attacks": attacks,
            "reports": reports,
        }

    return results
