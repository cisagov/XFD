"""
Daily worker to mark stale LatestPortScan rows as current = FALSE.

This worker:
- Runs once daily
- Processes the entire table
- Uses batched updates to avoid long-running locks
- Avoids deadlocks by being single-threaded
"""

import logging
from datetime import timedelta

from django.db import transaction, connections
from django.utils import timezone

from xfd_mini_dl.models import LatestPortScan

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


LATEST_PORT_SCAN_CUTOFF_DAYS = 14
BATCH_SIZE = 5000

def mark_stale_latest_port_scans():
    cutoff_date = timezone.now() - timedelta(days=LATEST_PORT_SCAN_CUTOFF_DAYS)

    with connections["mini_data_lake"].cursor() as cursor:
        cursor.execute(
            """
            UPDATE latest_port_scan
            SET current = FALSE
            WHERE current = TRUE
              AND time_scanned < %s
            """,
            [cutoff_date],
        )

        updated = cursor.rowcount

    LOGGER.info("Marked %d stale LatestPortScan rows.", updated)
    return updated

def mark_stale_latest_port_scans_batched():
    """
    Mark stale LatestPortScan rows as current = FALSE in batches.

    This avoids:
    - Long running table locks
    - Massive WAL spikes
    - Autovacuum starvation
    """

    cutoff_date = timezone.now() - timedelta(days=LATEST_PORT_SCAN_CUTOFF_DAYS)

    total_updated = 0

    LOGGER.info(
        "Starting daily stale LatestPortScan cleanup. Cutoff: %s",
        cutoff_date.isoformat(),
    )

    while True:
        with transaction.atomic():
            with connections["mini_data_lake"].cursor() as cursor:
                cursor.execute(
                    """
                    WITH stale_rows AS (
                        SELECT id
                        FROM latest_port_scan
                        WHERE current = TRUE
                          AND time_scanned < %s
                        ORDER BY id
                        LIMIT %s
                        FOR UPDATE SKIP LOCKED
                    )
                    UPDATE latest_port_scan lps
                    SET current = FALSE
                    FROM stale_rows
                    WHERE lps.id = stale_rows.id
                    RETURNING lps.id;
                    """,
                    [cutoff_date, BATCH_SIZE],
                )

                updated_rows = cursor.fetchall()
                batch_count = len(updated_rows)

        if batch_count == 0:
            break

        total_updated += batch_count
        LOGGER.info("Marked %d stale rows in this batch.", batch_count)

    LOGGER.info(
        "Daily stale LatestPortScan cleanup complete. Total rows updated: %d",
        total_updated,
    )

    return total_updated


def handler(event, context=None):
    """
    Entry point for daily stale cleanup worker.
    """

    try:
        # total = mark_stale_latest_port_scans_batched()
        total = mark_stale_latest_port_scans()

        return {
            "status_code": 200,
            "body": f"Completed stale cleanup. Total rows updated: {total}",
        }

    except Exception as e:
        LOGGER.exception("Daily stale cleanup failed: %s", e)
        return {
            "status_code": 500,
            "body": f"Cleanup failed: {str(e)}",
        }
