"""Guarded metadata corrections, never a way to reset report delivery history."""

from psycopg2 import sql

from was_reports.data.daily_report_tracker import get_tracker_record_by_id
from was_reports.utils.database import connect, close

EDITABLE_FIELDS = (
    "status",
    "result",
    "report_scan_notes",
    "customer_notes",
    "template",
    "nws",
    "recent_nws",
    "remove_nws",
    "qualys_error",
    "tag_id",
)
TEMPLATES = {
    "Results",
    "Action Required",
    "Targets Removed",
    "All NWS",
    "FCEB Action Required",
    "FCEB All NWS",
    "Deactivated",
}


def correct_tracker_row(tracker_id: int, updates: dict, *, expected: dict) -> None:
    """Lock and compare the inspected row before correcting an unclaimed report."""
    if tracker_id < 1 or not updates or set(updates) - set(EDITABLE_FIELDS):
        raise ValueError("Only supported tracker corrections are allowed.")
    updates = dict(updates)
    if "tag_id" in updates:
        if updates["tag_id"] is None or int(updates["tag_id"]) < 1:
            raise ValueError("Qualys tag ID must be positive.")
        updates["tag_id"] = int(updates["tag_id"])
    if "status" in updates and updates["status"] not in {
        "Finished",
        "Error",
        "Processing",
    }:
        raise ValueError("Status must be Finished, Error, or Processing.")
    if "template" in updates and updates["template"] not in TEMPLATES:
        raise ValueError("Template must be an approved report template.")
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '5s'")
            # Also excludes imports and tracker writers while the row is checked.
            cursor.execute(
                "LOCK TABLE was_daily_report_tracker IN SHARE ROW EXCLUSIVE MODE"
            )
            cursor.execute(
                "SELECT id FROM was_daily_report_tracker WHERE id = %s FOR UPDATE",
                (tracker_id,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Tracker row was not found.")
            record = get_tracker_record_by_id(tracker_id, conn)
            if record != expected:
                raise ValueError(
                    "Tracker row changed since inspection; reload it before editing."
                )
            if (
                record["report_sent_date"] is not None
                or record.get("assignee_email_status") == "sending"
            ):
                raise ValueError(
                    "Sent rows or active delivery rows cannot be edited here."
                )
            cursor.execute(
                "SELECT id FROM was_report_runs WHERE source_tracker_id = %s LIMIT 1",
                (tracker_id,),
            )
            if cursor.fetchone() is not None:
                raise ValueError(
                    "A report run already exists. Reconcile that run before correcting the tracker; no delivery state was reset."
                )
            assignments = sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(field)) for field in updates
            )
            cursor.execute(
                sql.SQL(
                    "UPDATE was_daily_report_tracker SET {}, updated_at = NOW(), digest_revision = digest_revision + 1 WHERE id = %s"
                ).format(assignments),
                tuple(updates.values()) + (tracker_id,),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)
