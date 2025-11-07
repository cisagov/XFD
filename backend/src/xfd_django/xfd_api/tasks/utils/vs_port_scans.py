"""VS Port Scan Helper."""

# Standard Python Libraries
from itertools import islice
import json
import logging
import os
import time
from typing import Iterable, Optional

# Third-Party Libraries
from django.db import connections, transaction
from django.db.models import Count, Max, Min
from django.utils import timezone
from psycopg2.extras import execute_values
from xfd_api.tasks.utils.cloudwatch_metrics import cloudwatch_metric
from xfd_api.tasks.utils.datetime_utils import safe_fromisoformat
from xfd_api.tasks.utils.query_redshift import fetch_in_chunks_keyset_frozen_bulk
from xfd_api.utils.hash import hash_ip
from xfd_api.utils.scan_utils.alerting import IngestionError, QueryError
from xfd_mini_dl.models import Ip, Organization, PortScan, PortScanServiceSummary

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="/tmp/vuln_scanning_sync.log",  # nosec B108
)
LOGGER = logging.getLogger(__name__)
IS_LOCAL = os.getenv("IS_LOCAL")
SCAN_NAME = "VulnScanningSync"
VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")

CHUNK_SIZE = 500_000


@cloudwatch_metric()
def fetch_port_scans_from_redshift(
    org_id_dict, risky_service_groups, nmi_service_groups, ps_start_dt, ps_end_dt
):
    """
    Fetch and process port scans for all organizations in org_id_dict at once.

    org_id_dict: {acronym: org_id}
    """
    if not org_id_dict:
        LOGGER.warning("No organizations provided for port scan fetch.")
        return

    total_processed = 0
    chunk_number = 1
    org_acronyms = list(org_id_dict.keys())

    for chunk in fetch_in_chunks_keyset_frozen_bulk(
        table="vmtableau.port_scans",
        time_col="time",
        start_dt=ps_start_dt,
        end_dt=ps_end_dt,
        chunk_size=CHUNK_SIZE,
        org_acronyms=org_acronyms,
    ):
        LOGGER.info(
            "Processing port scan chunk #%d with %d rows for %d orgs",
            chunk_number,
            len(chunk),
            len(org_acronyms),
        )

        bulk_insert_ips_and_link_to_port_scans(
            chunk, org_id_dict, risky_service_groups, nmi_service_groups
        )

        total_processed += len(chunk)
        chunk_number += 1

    if total_processed == 0:
        LOGGER.warning(
            "No port scans found in Redshift for the requested organizations within the specified date range."
        )
    else:
        LOGGER.info(
            "Processed %d total port scans across %d chunks for %d organizations",
            total_processed,
            chunk_number - 1,
            len(org_id_dict),
        )


# TODO: CRASM-3386: Review batch inserts for missing/duplicate data
@cloudwatch_metric()
def bulk_insert_ips_and_link_to_port_scans(
    port_scans, org_id_dict, risky_service_groups, nmi_service_groups
):
    """Bulk insert IPs and link them to port scans for multiple orgs."""
    ip_key_to_obj = {}
    port_scan_batch = []
    affected_keys = set()

    for port_scan in port_scans:
        try:
            owner = port_scan.get("owner")
            org_id = org_id_dict.get(owner)
            if not org_id:
                LOGGER.warning("No org_id found for owner '%s'. Skipping scan.", owner)
                continue

            ip_str = port_scan.get("ip")
            port_num = port_scan.get("port")

            if ip_str:
                key = (ip_str, org_id)
                if key not in ip_key_to_obj:
                    ip_key_to_obj[key] = Ip(
                        ip=ip_str,
                        organization_id=org_id,
                        ip_hash=hash_ip(ip_str),
                    )

            if ip_str and port_num is not None:
                affected_keys.add((org_id, ip_str, port_num))

            service_obj = json.loads(port_scan.get("service", "{}"))
            port_scan_batch.append(
                {
                    "raw": port_scan,
                    "service_obj": service_obj,
                    "org_id": org_id,
                }
            )

        except Exception as e:
            LOGGER.exception("Error staging port scan: %s", e)
            raise IngestionError(SCAN_NAME, str(e), "Failed staging port scans") from e

    # Bulk insert IPs
    ip_objs = list(ip_key_to_obj.values())
    if ip_objs:
        Ip.objects.bulk_create(ip_objs, ignore_conflicts=True, batch_size=1000)

    # Link to IP records
    ip_records = Ip.objects.filter(
        ip__in=[ip.ip for ip in ip_objs],
        organization_id__in=[ip.organization_id for ip in ip_objs],
    )
    ip_map = {(ip.ip, ip.organization_id): ip for ip in ip_records}

    # Insert port scans using psycopg2 execute_values
    insert_port_scans_sql(
        port_scan_batch, ip_map, risky_service_groups, nmi_service_groups
    )

    # Update latest flag
    if affected_keys:
        update_latest_flag_for_keys_batched(affected_keys, 5000)


# TODO: CRASM-3386: Review batch inserts for missing/duplicate data
@cloudwatch_metric()
def insert_port_scans_sql(
    port_scan_batch, ip_map, risky_service_groups, nmi_service_groups
):
    """
    Fast, low-WAL SQL insert for port_scan using psycopg2.execute_values.

    Each batch runs inside its own transaction and commits automatically.
    """
    db = "mini_data_lake"
    columns = [
        "id",
        "ip_string",
        "ip_id",
        "latest",
        "port",
        "protocol",
        "reason",
        "service",
        "service_name",
        "service_confidence",
        "service_method",
        "service_cpe",
        "service_hostname",
        "service_extra_info",
        "service_os_type",
        "service_product",
        "service_version",
        "service_tunnel",
        "service_device_type",
        "source",
        "state",
        "time_scanned",
        "organization_id",
        "risky_service_group",
        "nmi_service_group",
    ]

    # Prepare tuples
    tuples = []
    for item in port_scan_batch:
        ps = item["raw"]
        svc = item["service_obj"]
        org_id = item["org_id"]

        ip_str = ps.get("ip")
        ip_obj = ip_map.get((ip_str, org_id)) if ip_str else None

        tuples.append(
            (
                ps["_id"].replace("ObjectId('", "").replace("')", ""),
                ip_str,
                ip_obj.id if ip_obj else None,
                False,  # latest flag always False initially
                ps.get("port"),
                ps.get("protocol"),
                ps.get("reason"),
                json.dumps(ps.get("service") or {}),  # convert dict to JSON string
                svc.get("name"),
                svc.get("conf"),
                svc.get("method"),
                (svc.get("cpe") or [None])[0],
                svc.get("hostname"),
                svc.get("extrainfo"),
                svc.get("ostype"),
                svc.get("product"),
                svc.get("version"),
                svc.get("tunnel"),
                svc.get("devicetype"),
                ps.get("source"),
                ps.get("state"),
                safe_fromisoformat(ps.get("time")),
                org_id,
                risky_service_groups.get(svc.get("name")),
                nmi_service_groups.get(svc.get("name")),
            )
        )

    if not tuples:
        return

    sql = f"""
        INSERT INTO port_scan ({', '.join(columns)})
        VALUES %s
        ON CONFLICT (id) DO NOTHING
    """  # nosec B608

    PAGE_SIZE = 5000  # number of rows per VALUES chunk
    BATCH_COMMIT = 10000  # number of rows per transaction

    total = len(tuples)

    for i in range(0, total, BATCH_COMMIT):
        subset = tuples[i : i + BATCH_COMMIT]
        with transaction.atomic(using=db):
            with connections[db].cursor() as cursor:
                # Safe with ON CONFLICT DO NOTHING
                cursor.execute("SET LOCAL synchronous_commit = OFF;")
                execute_values(cursor, sql, subset, page_size=PAGE_SIZE)


# TODO: CRASM-3386: Review batch inserts for missing/duplicate data
@cloudwatch_metric()
def update_latest_flag_for_keys_batched(affected_keys, batch_size=20000):
    """
    Mark latest rows using a temp table + DISTINCT ON.

    Only flips rows that actually need changing.
    """
    db = "mini_data_lake"
    if not affected_keys:
        return

    keys = sorted(set(affected_keys))

    with connections[db].cursor() as cur, transaction.atomic(using=db):
        cur.execute("SET LOCAL synchronous_commit = OFF;")

        # 1) Temp table for keys
        cur.execute(
            """
            CREATE TEMP TABLE _ps_keys(
              organization_id uuid,
              ip_string text,
              port int,
              PRIMARY KEY (organization_id, ip_string, port)
            ) ON COMMIT DROP;
        """
        )
        execute_values(
            cur,
            "INSERT INTO _ps_keys (organization_id, ip_string, port) VALUES %s",
            keys,
            page_size=batch_size,
        )
        cur.execute("ANALYZE _ps_keys;")

        # 2) Latest row per key, but ONLY look back 90 days
        cur.execute(
            """
            CREATE TEMP TABLE _ps_latest_ids (id text PRIMARY KEY) ON COMMIT DROP;

            INSERT INTO _ps_latest_ids (id)
            SELECT DISTINCT ON (ps.organization_id, ps.ip_string, ps.port) ps.id
            FROM port_scan ps
            JOIN _ps_keys k
              ON ps.organization_id = k.organization_id
             AND ps.ip_string      = k.ip_string
             AND ps.port           = k.port
            WHERE ps.time_scanned IS NOT NULL
              AND ps.time_scanned > NOW() - INTERVAL '90 days'
            ORDER BY ps.organization_id, ps.ip_string, ps.port, ps.time_scanned DESC;
        """
        )
        cur.execute("ANALYZE _ps_latest_ids;")

        # 3a) Turn off stale 'latest=true'
        cur.execute(
            """
            UPDATE port_scan p
               SET latest = FALSE
            FROM _ps_keys k
            WHERE p.latest = TRUE
              AND p.organization_id = k.organization_id
              AND p.ip_string       = k.ip_string
              AND p.port            = k.port
              AND NOT EXISTS (
                    SELECT 1 FROM _ps_latest_ids l WHERE l.id = p.id
              );
        """
        )

        # 3b) Turn on the true latest
        cur.execute(
            """
            UPDATE port_scan p
               SET latest = TRUE
            FROM _ps_latest_ids l
            WHERE p.id = l.id
              AND p.latest IS DISTINCT FROM TRUE;
        """
        )

    LOGGER.info("Updated latest flags for %d distinct keys via DISTINCT ON.", len(keys))


def chunked(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    it = iter(iterable)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            break
        yield chunk


@cloudwatch_metric()
def create_port_scan_summaries_bulk(
    org_ids: Iterable[str], summary_date: Optional[str] = None
) -> None:
    """
    Compute PortScanSummary for *all* org_ids in one SQL and upsert in bulk.

    :param org_ids: iterable of organization UUIDs (strings)
    :param summary_date: ISO date string (YYYY-MM-DD) or None -> today() in DB
    """
    if not org_ids:
        LOGGER.info("No org_ids provided for bulk port scan summary.")
        return

    # We pass org_ids as a Postgres array parameter.
    # summary_date is passed as date (or defaults to CURRENT_DATE in SQL).
    with transaction.atomic(using="mini_data_lake"):
        with connections["mini_data_lake"].cursor() as cur:
            sql = """
            WITH base AS (
                SELECT
                    ps.organization_id,
                    ps.time_scanned,
                    ps.ip_string,
                    ps.service_name,
                    ps.risky_service_group,
                    ps.nmi_service_group
                FROM port_scan ps
                WHERE ps.latest = TRUE
                AND ps.state = 'open'
                AND ps.organization_id = ANY(%s)  -- only requested orgs
            ),
            agg_main AS (
                SELECT
                    organization_id,
                    MIN(time_scanned)    AS start_date,
                    MAX(time_scanned)    AS end_date,
                    COUNT(*)             AS open_port_count,
                    COUNT(*) FILTER (WHERE risky_service_group IS NOT NULL) AS risky_port_count,
                    COUNT(*) FILTER (WHERE nmi_service_group IS NOT NULL)   AS nmi_service_count,
                    COUNT(DISTINCT ip_string)       AS unique_ip_count,
                    COUNT(DISTINCT service_name)    AS unique_service_count
                FROM base
                GROUP BY organization_id
            ),
            risky_counts AS (
                SELECT
                    organization_id,
                    jsonb_object_agg(risky_service_group, cnt) AS risky_service_group_counts
                FROM (
                    SELECT
                        organization_id,
                        risky_service_group,
                        COUNT(*) AS cnt
                    FROM base
                    WHERE risky_service_group IS NOT NULL
                    GROUP BY organization_id, risky_service_group
                    ORDER BY organization_id
                ) t
                GROUP BY organization_id
            ),
            final AS (
                SELECT
                    a.organization_id,
                    COALESCE(%s::date, CURRENT_DATE) AS summary_date,
                    a.start_date,
                    a.end_date,
                    a.open_port_count,
                    a.risky_port_count,
                    a.nmi_service_count,
                    a.unique_ip_count,
                    a.unique_service_count,
                    COALESCE(r.risky_service_group_counts, '{}'::jsonb) AS risky_service_group_counts
                FROM agg_main a
                LEFT JOIN risky_counts r USING (organization_id)
            )
            INSERT INTO port_scan_summary AS ps
                (organization_id, summary_date, start_date, end_date,
                open_port_count, risky_port_count, nmi_service_count,
                unique_ip_count, unique_service_count, risky_service_group_counts)
            SELECT
                organization_id, summary_date, start_date, end_date,
                open_port_count, risky_port_count, nmi_service_count,
                unique_ip_count, unique_service_count, risky_service_group_counts
            FROM final
            ON CONFLICT (organization_id, summary_date)
            DO UPDATE SET
                start_date                = EXCLUDED.start_date,
                end_date                  = EXCLUDED.end_date,
                open_port_count           = EXCLUDED.open_port_count,
                risky_port_count          = EXCLUDED.risky_port_count,
                nmi_service_count         = EXCLUDED.nmi_service_count,
                unique_ip_count           = EXCLUDED.unique_ip_count,
                unique_service_count      = EXCLUDED.unique_service_count,
                risky_service_group_counts= EXCLUDED.risky_service_group_counts;
            """
            # Convert to list so it’s a concrete array param
            org_id_list = list(org_ids)
            i = 1
            for org_chunk in chunked(org_id_list, 10):
                cur.execute(sql, [org_chunk, summary_date])
                LOGGER.info("Finished %d/15 chunks", i)
                i += 1

            LOGGER.info(
                "Bulk port scan summaries upserted for %d orgs", len(org_id_list)
            )


@cloudwatch_metric()
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


@cloudwatch_metric()
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
