"""VS Port Scan Helper."""

# Standard Python Libraries
import json
import logging
import os
import time

# Third-Party Libraries
from django.db import connections, transaction
from django.db.models import Count, Max, Min, Q
from django.utils import timezone
from xfd_api.tasks.utils.datetime_utils import safe_fromisoformat
from xfd_api.tasks.utils.query_redshift import fetch_in_chunks_keyset_frozen
from xfd_api.utils.hash import hash_ip
from xfd_api.utils.scan_utils.alerting import IngestionError, QueryError
from xfd_mini_dl.models import (
    Ip,
    Organization,
    PortScan,
    PortScanServiceSummary,
    PortScanSummary,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"
VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")

CHUNK_SIZE = 500_000


def fetch_port_scans_from_redshift(
    org_id_dict, risky_service_groups, nmi_service_groups, ps_start_dt, ps_end_dt
):
    """Fetch port_scans from redshift."""
    LOGGER.info("Started processing port scans...")

    total_processed = 0
    chunk_number = 1
    for chunk in fetch_in_chunks_keyset_frozen(
        table="vmtableau.port_scans",
        time_col="time",
        start_dt=ps_start_dt,
        end_dt=ps_end_dt,
        chunk_size=CHUNK_SIZE,
    ):
        LOGGER.info(
            "Processing port scan chunk #%d with %d rows", chunk_number, len(chunk)
        )
        bulk_insert_ips_and_link_to_port_scans(
            chunk, org_id_dict, risky_service_groups, nmi_service_groups
        )
        total_processed += len(chunk)
        chunk_number += 1

    if total_processed == 0:
        LOGGER.warning(
            f"No port scans found in Redshift for the last {VS_PULL_DATE_RANGE} days."
        )
    else:
        LOGGER.info(
            "Processed %d total port scans across %d chunks",
            total_processed,
            chunk_number - 1,
        )


def bulk_insert_ips_and_link_to_port_scans(
    port_scans, org_id_dict, risky_service_groups, nmi_service_groups
):
    """Bulk insert IPs and link them to port scans, then update 'latest' flags efficiently."""
    ip_key_to_obj = {}
    port_scan_batch = []
    affected_keys = set()  # Collect affected keys for latest flag update

    # Step 1: Prepare IP insertions and staged port scan records
    for port_scan in port_scans:
        try:
            owner_id = org_id_dict.get(port_scan.get("owner"))
            if not owner_id:
                LOGGER.warning(
                    "%s is not a recognized organization, skipping host",
                    port_scan.get("owner"),
                )
                continue

            ip_str = port_scan.get("ip")
            port_num = port_scan.get("port")

            if ip_str:
                key = (ip_str, owner_id)
                if key not in ip_key_to_obj:
                    ip_key_to_obj[key] = Ip(
                        ip=ip_str,
                        organization_id=owner_id,
                        ip_hash=hash_ip(ip_str),
                    )

            if ip_str and port_num is not None and owner_id:
                affected_keys.add((owner_id, ip_str, port_num))

            service_obj = json.loads(port_scan.get("service", "{}"))
            port_scan_batch.append(
                {
                    "raw": port_scan,
                    "service_obj": service_obj,
                    "owner_id": owner_id,
                }
            )
        except Exception as e:
            LOGGER.exception("Error staging port scan: %s", e)
            raise IngestionError(SCAN_NAME, str(e), "Failed staging port scans") from e

    # Step 2: Bulk insert IPs, ignoring conflicts (safe due to unique_together constraint)
    ip_objs = list(ip_key_to_obj.values())
    if ip_objs:
        Ip.objects.bulk_create(ip_objs, ignore_conflicts=True, batch_size=1000)

    # Step 3: Fetch all inserted or existing IPs to link them
    ip_records = Ip.objects.filter(
        ip__in=[ip.ip for ip in ip_objs],
        organization_id__in=[ip.organization_id for ip in ip_objs],
    )
    ip_map = {(ip.ip, ip.organization_id): ip for ip in ip_records}

    # Step 4: Build and bulk insert PortScan records
    port_scan_objs = []
    for item in port_scan_batch:
        port_scan = item["raw"]
        service_obj = item["service_obj"]
        owner_id = item["owner_id"]

        ip_str = port_scan.get("ip")
        ip_obj = ip_map.get((ip_str, owner_id)) if ip_str else None

        try:
            port_scan_obj = PortScan(
                id=port_scan["_id"].replace("ObjectId('", "").replace("')", ""),
                ip_string=ip_str,
                ip=ip_obj,
                latest=False,
                port=port_scan.get("port"),
                protocol=port_scan.get("protocol"),
                reason=port_scan.get("reason"),
                service=port_scan.get("service"),
                service_name=service_obj.get("name"),
                service_confidence=service_obj.get("conf"),
                service_method=service_obj.get("method"),
                service_cpe=service_obj.get("cpe", [None])[0],
                service_hostname=service_obj.get("hostname"),
                service_extra_info=service_obj.get("extrainfo"),
                service_os_type=service_obj.get("ostype"),
                service_product=service_obj.get("product"),
                service_version=service_obj.get("version"),
                service_tunnel=service_obj.get("tunnel"),
                service_device_type=service_obj.get("devicetype"),
                source=port_scan.get("source"),
                state=port_scan.get("state"),
                time_scanned=safe_fromisoformat(port_scan.get("time")),
                organization_id=owner_id,
                risky_service_group=risky_service_groups.get(service_obj.get("name")),
                nmi_service_group=nmi_service_groups.get(service_obj.get("name")),
            )
            port_scan_objs.append(port_scan_obj)
        except Exception as e:
            LOGGER.exception("Error building PortScan object: %s", e)
            raise IngestionError(SCAN_NAME, str(e), "Failed building port scans") from e

    if port_scan_objs:
        LOGGER.info("Bulk creating port scans")
        PortScan.objects.bulk_create(
            port_scan_objs, batch_size=5000, ignore_conflicts=True
        )

    # Step 5: Update 'latest' flag only for affected keys
    if affected_keys:
        update_latest_flag_for_keys_batched(affected_keys, 5000)


def update_latest_flag_for_keys_batched(affected_keys, batch_size=5000):
    """Update the latest flag for a large set of affected keys in manageable batches."""
    db = "mini_data_lake"

    if not affected_keys:
        return

    def chunked(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    try:
        with transaction.atomic(using=db):
            with connections[db].cursor() as cursor:
                batch_num = 1
                for batch in chunked(list(affected_keys), batch_size):
                    params = []
                    placeholders = []
                    for org_id, ip, port in batch:
                        params.extend([org_id, ip, port])
                        placeholders.append("(%s, %s, %s)")
                    values_sql = ", ".join(placeholders)

                    sql = f"""
                    WITH ranked AS (
                        SELECT
                            ps.id,
                            ROW_NUMBER() OVER (
                                PARTITION BY ps.organization_id, ps.ip_string, ps.port
                                ORDER BY ps.time_scanned DESC
                            ) AS rn
                        FROM port_scan ps
                        JOIN (
                            VALUES {values_sql}
                        ) AS keys(org_id, ip_string, port)
                        ON ps.organization_id = keys.org_id
                        AND ps.ip_string = keys.ip_string
                        AND ps.port = keys.port
                    )
                    UPDATE port_scan
                    SET latest = (ranked.rn = 1)
                    FROM ranked
                    WHERE port_scan.id = ranked.id;
                    """  # nosec B608

                    cursor.execute(sql, params)
                    batch_num += 1

        LOGGER.info(
            f"Updated latest flags for {len(affected_keys)} keys in batches of {batch_size}."
        )

    except Exception as e:
        LOGGER.error(f"Failed to update latest flags: {e}", exc_info=True)


def create_port_scan_summary(summary_date=None):
    """Create port summary record for each organization."""
    try:
        if summary_date is None:
            summary_date = timezone.now().date()

        for org in Organization.objects.all():
            scans = PortScan.objects.filter(
                organization=org,
                latest=True,  # only latest scans
                time_scanned__isnull=False,
                state="open",
            )

            if not scans.exists():
                continue

            aggregated = scans.aggregate(
                start_date=Min("time_scanned"),
                end_date=Max("time_scanned"),
                open_port_count=Count("id"),
                risky_port_count=Count(
                    "id", filter=Q(risky_service_group__isnull=False)
                ),
                nmi_service_count=Count(
                    "id", filter=Q(nmi_service_group__isnull=False)
                ),
                unique_ip_count=Count("ip_string", distinct=True),
                unique_service_count=Count("service_name", distinct=True),
            )

            risky_group_data = (
                scans.filter(risky_service_group__isnull=False)
                .values("risky_service_group")
                .annotate(count=Count("id"))
            )

            # Convert to dict: {group: count}
            risky_service_group_counts = {
                item["risky_service_group"]: item["count"] for item in risky_group_data
            }

            PortScanSummary.objects.update_or_create(
                organization=org,
                summary_date=summary_date,
                defaults={
                    "start_date": aggregated["start_date"],
                    "end_date": aggregated["end_date"],
                    "open_port_count": aggregated["open_port_count"],
                    "risky_port_count": aggregated["risky_port_count"],
                    "nmi_service_count": aggregated["nmi_service_count"],
                    "unique_ip_count": aggregated["unique_ip_count"],
                    "unique_service_count": aggregated["unique_service_count"],
                    "risky_service_group_counts": risky_service_group_counts,
                },
            )

    except Exception as e:
        LOGGER.exception("Error creating port scan summary: %s", e)
        raise QueryError(SCAN_NAME, str(e), "Error creating port scan summary") from e


def create_port_scan_service_summaries(summary_date=None):
    """Fill the port scan service summary table."""
    try:
        if summary_date is None:
            summary_date = timezone.now().date()

        for org in Organization.objects.all():
            scans = PortScan.objects.filter(
                organization=org,
                latest=True,
                time_scanned__isnull=False,
                service_name__isnull=False,
            )

            if not scans.exists():
                continue

            # Group by service_name
            service_names = scans.values_list("service_name", flat=True).distinct()

            for service in service_names:
                service_scans = scans.filter(service_name=service)

                agg = service_scans.aggregate(
                    start_date=Min("time_scanned"),
                    end_date=Max("time_scanned"),
                    unique_ip_count=Count("ip_string", distinct=True),
                    unique_service_count=Count("service_name", distinct=True),
                )

                # Collect risky ports
                risky_ports_qs = service_scans.filter(risky_service_group__isnull=False)
                risky_ports = list(
                    risky_ports_qs.values_list("port", flat=True).distinct()
                )

                PortScanServiceSummary.objects.update_or_create(
                    organization=org,
                    summary_date=summary_date,
                    service_name=service,
                    defaults={
                        "start_date": agg["start_date"],
                        "end_date": agg["end_date"],
                        "unique_ip_count": agg["unique_ip_count"],
                        "unique_service_count": agg["unique_service_count"],
                        "risky_ports": risky_ports,
                    },
                )
    except Exception as e:
        LOGGER.exception("Error creating port scan service summary: %s", e)
        raise QueryError(
            SCAN_NAME, str(e), "Error creating port scan service summary"
        ) from e


def enforce_latest_flag_port_scan():
    """
    Enforce the `latest` boolean flag on the PortScan table for all orgs/IPs/ports.

    Uses a single indexed update with a window function for maximum efficiency.
    Only the most recent scan per (organization_id, ip_string, port) within
    the last 90 days is flagged as latest=True; all others are latest=False.
    """
    start = time.time()
    db = "mini_data_lake"

    sql = """
        WITH ranked_scans AS (
            SELECT
                id,
                RANK() OVER (
                    PARTITION BY organization_id, ip_string, port
                    ORDER BY time_scanned DESC
                ) AS scan_rank
            FROM port_scan
            WHERE time_scanned IS NOT NULL
              AND time_scanned > NOW() - INTERVAL '90 days'
        )
        UPDATE port_scan
        SET latest = (ranked_scans.scan_rank = 1)
        FROM ranked_scans
        WHERE port_scan.id = ranked_scans.id
          AND port_scan.latest IS DISTINCT FROM (ranked_scans.scan_rank = 1);
    """

    with connections[db].cursor() as cursor:
        cursor.execute(sql)

    duration = time.time() - start
    LOGGER.info("Completed enforce_latest_flag in %.2fs", duration)
