"""VS Ticket Helpers."""

# Standard Python Libraries
from datetime import timedelta
from datetime import timezone as dt_timezone
import json
import logging
import os
from typing import Dict

# Third-Party Libraries
from django.db import connections, transaction
from django.utils import timezone
from psycopg2 import sql
from psycopg2.extras import execute_values
from xfd_api.tasks.utils.cloudwatch_metrics import cloudwatch_metric
from xfd_api.tasks.utils.datetime_utils import (
    safe_fromisoformat,
    safe_parse_date,
    to_utc_naive,
)
from xfd_api.tasks.utils.query_redshift import query_redshift
from xfd_api.utils.hash import hash_ip
from xfd_mini_dl.models import Cve, Ip, PortScan, Ticket, TicketEvent, VulnScan

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="/tmp/vuln_scanning_sync.log",  # nosec B108
)
LOGGER = logging.getLogger(__name__)
SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")

VS_PULL_DATE_RANGE = os.getenv("VS_PULL_DATE_RANGE", "2")

# Chunking constants (tune as needed)
TICKET_ROWS_FLUSH = 25_000  # upsert tickets when batch hits this
EVENTS_FLUSH_THRESHOLD = 50_000  # flush events when staged hits this
BULK_CREATE_BATCH = 5_000  # execute_values page_size for tickets
EVENTS_CREATE_BATCH = 10_000  # TicketEvent bulk_create batch
DB_ALIAS = "mini_data_lake"


@cloudwatch_metric()
def fetch_tickets_from_redshift(
    org_id_dict: dict,
    risky_service_groups: dict,
    nmi_service_groups: dict,
    ps_start_dt,
    ps_end_dt,
):
    """Fetch and process tickets from Redshift for multiple orgs."""
    if not org_id_dict:
        LOGGER.warning("No organizations provided for ticket processing.")
        return

    LOGGER.info("Starting ticket processing for %d orgs.", len(org_id_dict))

    total_processed = 0
    chunk_number = 1
    org_acronyms = list(org_id_dict.keys())

    for chunk in fetch_ticket_chunks_frozen_multi_org(
        ps_start_dt,
        ps_end_dt,
        org_acronyms=org_acronyms,
    ):
        LOGGER.info(
            "Processing ticket chunk #%d with %d rows across %d orgs",
            chunk_number,
            len(chunk),
            len(org_acronyms),
        )

        process_tickets_multi_org(
            chunk,
            org_id_dict,
            risky_service_groups,
            nmi_service_groups,
            ps_start_dt,
            ps_end_dt,
        )

        total_processed += len(chunk)
        chunk_number += 1

    if total_processed == 0:
        LOGGER.info(
            "No tickets found in Redshift for the requested orgs in the last %d days.",
            int(VS_PULL_DATE_RANGE),
        )
    else:
        LOGGER.info(
            "Processed %d total tickets across %d chunks for %d orgs",
            total_processed,
            chunk_number - 1,
            len(org_acronyms),
        )

    LOGGER.info("Finished ticket processing for %d orgs.", len(org_acronyms))


@cloudwatch_metric()
def fetch_ticket_chunks_frozen_multi_org(
    ps_start_dt,
    ps_end_dt,
    org_acronyms: list[str],
    chunk_size: int = 5000,
):
    """Fetch ticket data in chunks for multiple orgs, safely parameterized."""
    if not org_acronyms:
        LOGGER.warning("No orgs provided to fetch tickets.")
        return

    last_time = None
    last_id = None
    start_param = to_utc_naive(ps_start_dt)
    end_param = to_utc_naive(ps_end_dt)

    while True:
        where_parts = [
            sql.SQL('"last_change" >= %s'),
            sql.SQL('"last_change" < %s'),
        ]
        params = [start_param, end_param]

        # Keyset pagination
        if last_time is not None and last_id is not None:
            where_parts.append(
                sql.SQL('("last_change" > %s OR ("last_change" = %s AND "_id" > %s))')
            )
            params.extend([last_time, last_time, last_id])

        # Org filter using IN
        owner_placeholders = sql.SQL(", ").join(sql.Placeholder() * len(org_acronyms))
        where_parts.append(sql.SQL("owner IN ({})").format(owner_placeholders))
        params.extend(org_acronyms)

        where_clause = sql.SQL(" AND ").join(where_parts)

        query = sql.SQL(
            """
            SELECT *
            FROM vmtableau.tickets
            WHERE {where_clause}
            ORDER BY "last_change", "_id"
            LIMIT %s
            """
        ).format(where_clause=where_clause)

        params.append(chunk_size)

        chunk = query_redshift(query, params=params)
        if not chunk:
            break

        last_row = chunk[-1]
        last_time = last_row["last_change"]
        last_id = str(last_row["_id"])

        yield chunk


def preload_os_type_map(ip_keys) -> dict:
    """Return mapping ip_str -> service_os_type."""
    scans = (
        PortScan.objects.filter(ip_string__in=ip_keys, service_os_type__isnull=False)
        .order_by("ip_string", "-time_scanned")
        .distinct("ip_string")
    )
    return {scan.ip_string: scan.service_os_type for scan in scans}


@cloudwatch_metric()
def process_tickets_multi_org(
    tickets,
    org_id_dict: dict[str, str],
    risky_service_groups: dict,
    nmi_service_groups: dict,
    ps_start_dt,
    ps_end_dt,
):
    """
    Process tickets across multiple orgs.

    - Early dedup by most recent 'last_change'
    - Bulk insert IPs & CVEs
    - Re-lookup IP/CVE ids
    - Bulk upsert Tickets via raw SQL (only if newer)
    - Stage TicketEvents and flush in large batches
    """
    if timezone.is_naive(ps_start_dt):
        ps_start_dt = timezone.make_aware(ps_start_dt)
    if timezone.is_naive(ps_end_dt):
        ps_end_dt = timezone.make_aware(ps_end_dt)

    window_days = (ps_end_dt - ps_start_dt).days
    if window_days == 2:
        ps_start_dt = ps_start_dt - timedelta(days=3)

    ps_start_dt = ps_start_dt.astimezone(dt_timezone.utc)
    ps_end_dt = ps_end_dt.astimezone(dt_timezone.utc)

    # ---- Step 0: Early dedup by id, keep most-recent last_change
    deduped: Dict[str, dict] = {}
    for t in tickets:
        tid = t["_id"].replace("ObjectId('", "").replace("')", "")
        cur_updated = safe_fromisoformat(t.get("last_change"))
        if tid in deduped:
            prev_updated = safe_fromisoformat(deduped[tid].get("last_change"))
            if cur_updated and prev_updated and cur_updated <= prev_updated:
                continue
        deduped[tid] = t

    # Preload os_type from port_scan
    os_type_map = preload_os_type_map(
        [t.get("ip") for t in deduped.values() if t.get("ip")]
    )

    ip_key_to_obj = {}
    cve_name_to_obj = {}
    ticket_data_map = {}

    for tid, t in deduped.items():
        details = json.loads(t.get("details", "{}"))
        events = json.loads(t.get("events", "[]"))
        ticket_data_map[tid] = {"raw": t, "details": details, "events": events}

        owner = t.get("owner")
        org_id = org_id_dict.get(owner)
        if not org_id:
            continue  # skip tickets for unknown orgs

        ip_str = t.get("ip")
        if ip_str:
            key = (ip_str, org_id)
            if key not in ip_key_to_obj:
                ip_key_to_obj[key] = Ip(
                    ip=ip_str, organization_id=org_id, ip_hash=hash_ip(ip_str)
                )

        cve_name = details.get("cve")
        if cve_name and cve_name not in cve_name_to_obj:
            cve_name_to_obj[cve_name] = Cve(name=cve_name)

    # Insert staged IPs/CVEs
    if ip_key_to_obj:
        Ip.objects.using(DB_ALIAS).bulk_create(
            list(ip_key_to_obj.values()), ignore_conflicts=True, batch_size=1_000
        )
    if cve_name_to_obj:
        Cve.objects.using(DB_ALIAS).bulk_create(
            list(cve_name_to_obj.values()), ignore_conflicts=True, batch_size=1_000
        )

    # ---- Step 2: Query back IP/CVE mapping from MDL
    ip_map = {
        (ip.ip, ip.organization_id): ip
        for ip in Ip.objects.using(DB_ALIAS).filter(
            ip__in=[i.ip for i in ip_key_to_obj.values()],
            organization_id__in=list(org_id_dict.values()),
        )
    }
    cve_map = {
        c.name: c
        for c in Cve.objects.using(DB_ALIAS).filter(
            name__in=list(cve_name_to_obj.keys())
        )
    }

    ticket_rows_batch = []
    staged_events = []

    for tid, tdata in ticket_data_map.items():
        raw = tdata["raw"]
        details = tdata["details"]
        events = tdata["events"]

        owner = raw.get("owner")
        org_id = org_id_dict.get(owner)
        if not org_id:
            continue

        ip_str = raw.get("ip")
        cve_name = details.get("cve")
        ip_fk = ip_map.get((ip_str, org_id))
        cve_fk = cve_map.get(cve_name)

        try:
            lon, lat = json.loads(raw.get("loc", "[]"))
        except Exception:
            lon, lat = (None, None)

        updated_ts = safe_fromisoformat(raw.get("last_change"))
        closed_ts = (
            safe_fromisoformat(raw.get("time_closed"))
            if raw.get("time_closed")
            else None
        )
        opened_ts = (
            safe_fromisoformat(raw.get("time_opened"))
            if raw.get("time_opened")
            else None
        )
        is_risky = "Potentially Risky Service Detected:" in (details.get("name") or "")

        row = {
            "id": tid,
            "cve_string": cve_name,
            "cve_id": cve_fk.id if cve_fk else None,
            "cvss_base_score": details.get("cvss_base_score"),
            "cvss_version": details.get("cvss_version"),
            "vuln_name": details.get("name"),
            "cvss_score_source": details.get("score_source"),
            "cvss_severity": details.get("severity"),
            "vpr_score": details.get("vpr_score"),
            "false_positive": raw.get("false_positive"),
            "ip_string": ip_str,
            "ip_id": ip_fk.id if ip_fk else None,
            "updated_timestamp": updated_ts,
            "location_longitude": lon,
            "location_latitude": lat,
            "organization_id": org_id,
            "vuln_port": raw.get("port"),
            "port_protocol": raw.get("protocol"),
            "snapshots_bool": bool(raw.get("snapshots", None)),
            "vuln_source": raw.get("source"),
            "vuln_source_id": raw.get("source_id"),
            "closed_timestamp": closed_ts,
            "opened_timestamp": opened_ts,
            "is_open": raw.get("open"),
            "is_kev": details.get("kev"),
            "is_kev_ransomware": details.get("kev_ransomware"),
            "is_risky": is_risky,
            "service_name": details.get("service"),
            "operating_system": os_type_map.get(ip_str),
            "risky_service_group": risky_service_groups.get(details.get("service")),
            "nmi_service_group": nmi_service_groups.get(details.get("service")),
        }
        ticket_rows_batch.append(row)

        # Stage TicketEvents
        for ev in reversed(events):
            ev_time = safe_parse_date(ev.get("time"))
            if not ev_time:
                continue
            if timezone.is_naive(ev_time):
                ev_time = timezone.make_aware(ev_time, dt_timezone.utc)
            else:
                ev_time = ev_time.astimezone(dt_timezone.utc)

            if ev_time >= ps_end_dt:
                continue

            if ev_time < ps_start_dt:
                break

            ref_id = ev.get("reference")
            if isinstance(ref_id, str):
                ref_id = ref_id.replace("ObjectId('", "").replace("')", "")

            staged_events.append(
                {
                    "ticket_id": tid,
                    "vuln_source": raw.get("source"),
                    "ref_id": ref_id,
                    "action": ev.get("action"),
                    "reason": ev.get("reason"),
                    "event_timestamp": ev_time,
                }
            )

        # Flush tickets/events in batches
        if len(ticket_rows_batch) >= TICKET_ROWS_FLUSH:
            with transaction.atomic(using=DB_ALIAS):
                bulk_upsert_tickets_sql(
                    ticket_rows_batch, using=DB_ALIAS, page_size=BULK_CREATE_BATCH
                )
            ticket_rows_batch.clear()

        if len(staged_events) >= EVENTS_FLUSH_THRESHOLD:
            if ticket_rows_batch:
                with transaction.atomic(using=DB_ALIAS):
                    bulk_upsert_tickets_sql(
                        ticket_rows_batch, using=DB_ALIAS, page_size=BULK_CREATE_BATCH
                    )
                ticket_rows_batch.clear()
            with transaction.atomic(using=DB_ALIAS):
                bulk_create_ticket_events(
                    staged_events, using=DB_ALIAS, batch_size=EVENTS_CREATE_BATCH
                )
            staged_events.clear()

    # Final flush
    if ticket_rows_batch:
        bulk_upsert_tickets_sql(
            ticket_rows_batch, using=DB_ALIAS, page_size=BULK_CREATE_BATCH
        )
    if staged_events:
        bulk_create_ticket_events(
            staged_events, using=DB_ALIAS, batch_size=EVENTS_CREATE_BATCH
        )

    LOGGER.info(
        "Finished processing %d deduped tickets across %d orgs.",
        len(deduped),
        len(org_id_dict),
    )


@cloudwatch_metric()
def bulk_create_ticket_events(
    events_data, using=DB_ALIAS, batch_size=EVENTS_CREATE_BATCH
):
    """Bulk insert ticket events if they link to a valid port or vuln scan."""
    if not events_data:
        return

    # Build distinct ref sets
    port_refs = list(
        {e["ref_id"] for e in events_data if e["vuln_source"] == "nmap" and e["ref_id"]}
    )
    vuln_refs = list(
        {
            e["ref_id"]
            for e in events_data
            if e["vuln_source"] == "nessus" and e["ref_id"]
        }
    )

    # Early exit if there’s nothing to check
    if not port_refs and not vuln_refs:
        return

    existing_ports = set()
    existing_vulns = set()

    # Only query if we actually have refs. Use chunks to keep IN size sane.
    def _batched(iterable, n):
        for i in range(0, len(iterable), n):
            yield iterable[i : i + n]

    if port_refs:
        for chunk in _batched(port_refs, 10_000):
            existing_ports.update(
                PortScan.objects.using(using)
                .filter(id__in=chunk)
                .values_list("id", flat=True)
            )
    if vuln_refs:
        for chunk in _batched(vuln_refs, 10_000):
            existing_vulns.update(
                VulnScan.objects.using(using)
                .filter(id__in=chunk)
                .values_list("id", flat=True)
            )

    to_create = []
    skipped_nmap = skipped_nessus = 0

    for e in events_data:
        ref_id = e["ref_id"]
        source = e["vuln_source"]

        if source == "nmap":
            if ref_id not in existing_ports:
                skipped_nmap += 1
                continue
            port_scan_id = ref_id
            vuln_scan_id = None
        elif source == "nessus":
            if ref_id not in existing_vulns:
                skipped_nessus += 1
                continue
            port_scan_id = None
            vuln_scan_id = ref_id
        else:
            # Unknown source; skip or handle as needed
            continue

        to_create.append(
            TicketEvent(
                ticket_id=e["ticket_id"],  # FK by id → no ORM fetch
                reference=ref_id,
                port_scan_id=port_scan_id,
                vuln_scan_id=vuln_scan_id,
                action=e.get("action"),
                reason=e.get("reason"),
                event_timestamp=e.get("event_timestamp"),
            )
        )

    if to_create:
        # If you add a unique constraint on (ticket_id, reference, event_timestamp),
        # you can make this idempotent:
        TicketEvent.objects.using(using).bulk_create(
            to_create, batch_size=batch_size, ignore_conflicts=True
        )

    LOGGER.info(
        "TicketEvents created=%d, skipped_nmap=%d, skipped_nessus=%d",
        len(to_create),
        skipped_nmap,
        skipped_nessus,
    )


@cloudwatch_metric()
def bulk_upsert_tickets_sql(rows, using=DB_ALIAS, page_size=BULK_CREATE_BATCH):
    """Insert or update Ticket rows, but only update when EXCLUDED.updated_timestamp is newer."""
    if not rows:
        return

    conn = connections[using]
    qn = conn.ops.quote_name
    table = qn(Ticket._meta.db_table)

    columns = [
        "id",
        "cve_string",
        "cve_id",
        "cvss_base_score",
        "cvss_version",
        "vuln_name",
        "cvss_score_source",
        "cvss_severity",
        "vpr_score",
        "false_positive",
        "ip_string",
        "ip_id",
        "updated_timestamp",
        "location_longitude",
        "location_latitude",
        "organization_id",
        "vuln_port",
        "port_protocol",
        "snapshots_bool",
        "vuln_source",
        "vuln_source_id",
        "closed_timestamp",
        "opened_timestamp",
        "is_open",
        "is_kev",
        "is_kev_ransomware",
        "is_risky",
        "service_name",
        "operating_system",
        "risky_service_group",
        "nmi_service_group",
    ]

    col_list_sql = ", ".join(qn(c) for c in columns)
    set_sql = ", ".join(f"{qn(c)} = EXCLUDED.{qn(c)}" for c in columns if c != "id")
    where_sql = f"{table}.updated_timestamp IS NULL OR EXCLUDED.updated_timestamp > {table}.updated_timestamp"

    sql = f"""
        INSERT INTO {table} ({col_list_sql})
        VALUES %s
        ON CONFLICT (id) DO UPDATE
        SET {set_sql}
        WHERE {where_sql}
    """  # nosec B608

    values = [tuple(row.get(col) for col in columns) for row in rows]

    with conn.cursor() as cur:
        execute_values(cur, sql, values, page_size=page_size)
