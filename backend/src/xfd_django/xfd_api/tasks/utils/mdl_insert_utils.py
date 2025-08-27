"""MDL Insert Helpers."""

# Standard Python Libraries
import logging
import time
from uuid import uuid4

# Third-Party Libraries
from django.db import connections, transaction
from xfd_mini_dl.models import Cve, Ip

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


def save_ip_to_datalake(ip_obj):
    """
    Save an IP record to the datalake, performing an upsert if necessary.

    Args:
        ip_obj (dict): A dictionary containing IP record data.

    Returns:
        Ip instance or None
    """
    ip_address = ip_obj.get("ip")
    organization_id = ip_obj.get("organization")

    # Fields to update except IP and organization_id
    ip_updated_values = [
        key
        for key in ip_obj.keys()
        if key not in ["ip", "organization"] and ip_obj[key] is not None
    ]

    try:
        with transaction.atomic(using="mini_data_lake"):
            if ip_updated_values:
                # Upsert: Insert or update if a conflict occurs
                ip_record, created = Ip.objects.update_or_create(
                    ip=ip_address,
                    organization_id=organization_id,
                    defaults={key: ip_obj[key] for key in ip_updated_values},
                )
                return ip_record
            else:
                # Insert but ignore if the record already exists
                obj, created = Ip.objects.get_or_create(
                    ip=ip_address,
                    organization_id=organization_id,
                    defaults={
                        "ip": ip_address,
                        "organization_id": organization_id,
                        "ip_hash": ip_obj["ip_hash"],
                    },
                )
                if created:
                    LOGGER.info("Created ip")
                return obj
    except Exception as e:
        LOGGER.error("Error saving IP to Datalake: %s", e)
        # optionally re-raise or handle accordingly
        return None


def save_cve_to_datalake(cve_obj):
    """
    Save a CVE record to the datalake, performing an upsert if necessary.

    Args:
        cve_obj (dict): A dictionary containing CVE record data.

    Returns:
        str or None: The ID of the inserted/updated record.
    """
    cve_name = cve_obj.get("name")

    # Determine fields to update, excluding 'name'
    cve_updated_values = [
        key
        for key in cve_obj.keys()
        if key not in ["name"] and cve_obj[key] is not None
    ]

    try:
        with transaction.atomic(using="mini_data_lake"):
            if cve_updated_values:
                # Upsert: Insert or update if a conflict occurs
                cve_record, created = Cve.objects.update_or_create(
                    name=cve_name,
                    defaults={key: cve_obj[key] for key in cve_updated_values}
                    | {"id": str(1)},
                )
                LOGGER.info("Updated CVE" if not created else "Created CVE")
                return cve_record
            else:
                # Insert but ignore if the record already exists
                obj, created = Cve.objects.get_or_create(
                    name=cve_name, defaults=cve_obj | {"id": str(uuid4())}
                )
                return obj
    except Exception as e:
        LOGGER.error("Error saving CVE to Datalake: %s", e)
        return None


def fill_cidr_live_ips_bulk_update():
    """Fill live_ips field in the cidr table based on recent port scans."""
    start_time = time.time()

    with transaction.atomic(using="mini_data_lake"):
        with connections["mini_data_lake"].cursor() as cursor:
            cursor.execute(
                """
                WITH new_ips AS (
                    SELECT
                        cidr.id AS cidr_id,
                        array_agg(DISTINCT ip.ip) AS new_ip_list
                    FROM cidr
                    JOIN cidr_orgs ON cidr_orgs.cidr_id = cidr.id
                    JOIN port_scan ON port_scan.state = 'open'
                        AND port_scan.time_scanned >= NOW() - INTERVAL '90 days'
                    JOIN ip ON port_scan.ip_id = ip.id
                    WHERE cidr_orgs.current = TRUE
                      AND cidr.network IS NOT NULL
                      AND ip.ip << cidr.network
                    GROUP BY cidr.id
                ),
                merged_ips AS (
                    SELECT
                        cidr.id,
                        ARRAY(
                            SELECT DISTINCT ip_address::inet
                            FROM jsonb_array_elements_text(
                                COALESCE(cidr.live_ips, '[]'::jsonb) || to_jsonb(new_ips.new_ip_list)
                            ) AS ip_address
                        ) AS updated_ips
                    FROM cidr
                    JOIN new_ips ON cidr.id = new_ips.cidr_id
                )
                UPDATE cidr
                SET live_ips = to_jsonb(merged_ips.updated_ips)
                FROM merged_ips
                WHERE cidr.id = merged_ips.id;
                """  # nosec B608
            )

    duration = time.time() - start_time
    LOGGER.info("fill_cidr_live_ips_bulk_update completed in %.2f seconds", duration)
