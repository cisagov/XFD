"""Worker to stress-test latest_port_scan updates for a single org with deadlock logging on all inserts/updates."""

import logging
import random
import string
import uuid
from datetime import datetime, timedelta, timezone

from django.db import transaction, connections, OperationalError

from xfd_mini_dl.models import Ip, PortScan, LatestPortScan, Organization

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
if not LOGGER.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(funcName)s:%(lineno)d] - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    ch.setFormatter(formatter)
    LOGGER.addHandler(ch)

NUM_SCANS = 10_000
PORT_RANGE = list(range(20, 1025))
PROTOCOLS = ["tcp", "udp"]
LATEST_PORT_SCAN_CUTOFF_DAYS = 14
DB_ALIAS = "mini_data_lake"


def random_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def random_service():
    return {
        "name": random.choice(["http", "ssh", "mysql", "ftp", "smtp"]),
        "conf": random.randint(50, 100),
        "method": random.choice(["banner", "probe"]),
        "cpe": ["cpe:/a:dummy:service:1.0"],
        "hostname": f"host-{random.randint(1,1000)}",
        "extrainfo": None,
        "ostype": random.choice(["linux", "windows", None]),
        "product": None,
        "version": None,
        "tunnel": None,
        "devicetype": None,
    }


def log_deadlock_info(db_alias):
    """Log currently waiting and blocking queries from pg_locks and pg_stat_activity."""
    try:
        with connections[db_alias].cursor() as cursor:
            cursor.execute(
                """
                SELECT blocked_locks.pid AS blocked_pid,
                       blocked_activity.query AS blocked_query,
                       blocking_locks.pid AS blocking_pid,
                       blocking_activity.query AS blocking_query
                FROM pg_catalog.pg_locks blocked_locks
                JOIN pg_catalog.pg_stat_activity blocked_activity
                  ON blocked_activity.pid = blocked_locks.pid
                JOIN pg_catalog.pg_locks blocking_locks
                  ON blocking_locks.locktype = blocked_locks.locktype
                 AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
                 AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                 AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
                 AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
                 AND blocking_locks.pid != blocked_locks.pid
                JOIN pg_catalog.pg_stat_activity blocking_activity
                  ON blocking_activity.pid = blocking_locks.pid
                WHERE NOT blocked_locks.granted;
                """
            )
            rows = cursor.fetchall()
            if rows:
                LOGGER.warning("Deadlock detected: blocking queries:")
                for row in rows:
                    blocked_pid, blocked_query, blocking_pid, blocking_query = row
                    LOGGER.warning(
                        "Blocked PID %s: %s | Blocking PID %s: %s",
                        blocked_pid,
                        blocked_query.strip() if blocked_query else "<None>",
                        blocking_pid,
                        blocking_query.strip() if blocking_query else "<None>",
                    )
            else:
                LOGGER.warning("Deadlock detected but no blocking queries found.")
    except Exception as e:
        LOGGER.exception("Failed to fetch deadlock queries: %s", e)


def generate_port_scans(org_id):
    scans = []
    ip_objs = {}
    affected_keys = set()

    for _ in range(NUM_SCANS):
        ip_str = random_ip()
        port = random.choice(PORT_RANGE)
        protocol = random.choice(PROTOCOLS)
        time_scanned = datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, 30), hours=random.randint(0, 23)
        )
        service = random_service()

        # Prepare IP
        key = (ip_str, org_id)
        if key not in ip_objs:
            ip_objs[key] = Ip(ip=ip_str, organization_id=org_id)

        # Track affected keys for latest update
        affected_keys.add((org_id, ip_str, port))

        # Create PortScan record
        ps_id = str(uuid.uuid4())
        scans.append(
            PortScan(
                id=ps_id,
                ip_string=ip_str,
                ip=None,  # will link after bulk create
                latest=False,
                port=port,
                protocol=protocol,
                reason="dummy",
                service=service,
                service_name=service["name"],
                service_confidence=service["conf"],
                service_method=service["method"],
                state="open",
                source="dummy",
                time_scanned=time_scanned,
                organization_id=org_id,
            )
        )

    return scans, list(ip_objs.values()), affected_keys


def link_ips(port_scans, ip_map):
    for ps in port_scans:
        ps.ip = ip_map.get((ps.ip_string, ps.organization_id))


def bulk_insert_port_scans(port_scans):
    LOGGER.info("Bulk inserting %d PortScan rows...", len(port_scans))
    try:
        PortScan.objects.bulk_create(port_scans, batch_size=1000, ignore_conflicts=True)
    except OperationalError as e:
        if "deadlock detected" in str(e):
            LOGGER.error("Deadlock detected during bulk insert of PortScan!")
            log_deadlock_info(DB_ALIAS)
        raise


def create_latest_port_scans(port_scans):
    latest_objs = []
    for ps in port_scans:
        latest_objs.append(
            LatestPortScan(
                id=str(uuid.uuid4()),
                port_scan_id=ps.id,
                ip_string=ps.ip_string,
                ip=ps.ip,
                port=ps.port,
                protocol=ps.protocol,
                reason=ps.reason,
                service=ps.service,
                service_name=ps.service_name,
                service_confidence=ps.service_confidence,
                service_method=ps.service_method,
                state=ps.state,
                time_scanned=ps.time_scanned,
                organization_id=ps.organization_id,
                current=True,
            )
        )
    LOGGER.info("Bulk inserting %d LatestPortScan rows...", len(latest_objs))
    try:
        LatestPortScan.objects.bulk_create(latest_objs, batch_size=1000, ignore_conflicts=True)
    except OperationalError as e:
        if "deadlock detected" in str(e):
            LOGGER.error("Deadlock detected during bulk insert of LatestPortScan!")
            log_deadlock_info(DB_ALIAS)
        raise


def handler(event):
    """Accept a single org and run the test scenario with full deadlock logging."""
    org_name = event.get("organizationName")
    org_id = event.get("organizationId")
    LOGGER.info("Running version 1.1.1")
    if not org_name or not org_id:
        return {"status_code": 400, "body": "Organization name or ID not provided"}

    org_qs = Organization.objects.filter(id=org_id)
    if not org_qs.exists():
        return {"status_code": 404, "body": "Organization not found"}
    org = org_qs.first()

    LOGGER.info("Starting dummy port scan generation for org: %s", org_name)

    port_scans, ip_objs, affected_keys = generate_port_scans(org.id)

    # Bulk insert IPs
    if ip_objs:
        LOGGER.info("Creating %d new IPs...", len(ip_objs))
        try:
            Ip.objects.bulk_create(ip_objs, batch_size=500, ignore_conflicts=True)
        except OperationalError as e:
            if "deadlock detected" in str(e):
                LOGGER.error("Deadlock detected during bulk insert of IPs!")
                log_deadlock_info(DB_ALIAS)
            raise

    # Map IP objects for linking
    ip_records = Ip.objects.filter(
        ip__in=[ip.ip for ip in ip_objs], organization_id=org.id
    )
    ip_map = {(ip.ip, ip.organization_id): ip for ip in ip_records}
    link_ips(port_scans, ip_map)

    # Insert port scans and latest port scans
    bulk_insert_port_scans(port_scans)
    create_latest_port_scans(port_scans)

    # Run latest updater
    from xfd_api.tasks.utils.vs_port_scans import (
        update_latest_flag_for_keys_batched,
        mark_stale_latest_port_scans,
        mark_stale_latest_port_scans_batched
    )

    LOGGER.info("Running update_latest_flag_for_keys_batched...")
    update_latest_flag_for_keys_batched(affected_keys)

    # LOGGER.info('skipping marking stale latest port scans')
    LOGGER.info("Running mark_stale_latest_port_scans with deadlock logging...")
    try:
        mark_stale_latest_port_scans()
    except OperationalError as e:
        if "deadlock detected" in str(e):
            LOGGER.error("Deadlock detected in mark_stale_latest_port_scans()!")
            log_deadlock_info(DB_ALIAS)
        raise

    LOGGER.info("Dummy port scan load completed successfully for org %s", org_name)
    return {"status_code": 200, "body": "Completed dummy port scan test run"}
