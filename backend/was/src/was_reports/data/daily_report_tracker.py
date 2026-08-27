"""Data access helpers for WAS daily report tracker rows."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection


@dataclass(frozen=True)
class DailyReportTrackerRow:
    """Database representation of one WAS daily report tracker row."""

    source_row_number: Optional[int] = None
    data_pull_date: Optional[date] = None
    tag: Optional[str] = None
    scan_name: Optional[str] = None
    assignee_id: Optional[int] = None
    assignee: Optional[str] = None
    status: Optional[str] = None
    result: Optional[str] = None
    report_sent_date: Optional[date] = None
    report_scan_notes: Optional[str] = None
    scan_start_date: Optional[date] = None
    next_scan_date: Optional[date] = None
    poc: Optional[str] = None
    poc_email: Optional[str] = None
    customer_notes: Optional[str] = None
    nws: Optional[str] = None
    template: Optional[str] = None
    recent_nws: Optional[str] = None
    remove_nws: Optional[str] = None
    legacy_password: Optional[str] = None
    schedule_id: Optional[int] = None
    qualys_error: Optional[str] = None
    assignee_emailed_at: Optional[datetime] = None
    assignee_email_message_id: Optional[str] = None
    assignee_email_error: Optional[str] = None


@dataclass(frozen=True)
class AssigneeDigest:
    """Tracker rows that should be emailed to one assignee."""

    assignee_id: int
    assignee: str
    email: str
    rows: List[DailyReportTrackerRow]


def insert_daily_report_tracker_row(
    row: DailyReportTrackerRow,
    conn: connection,
) -> int:
    """Insert one WAS daily report tracker row and return the row ID."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO was_daily_report_tracker (
                    source_row_number,
                    data_pull_date,
                    tag,
                    scan_name,
                    assignee_id,
                    assignee,
                    status,
                    result,
                    report_sent_date,
                    report_scan_notes,
                    scan_start_date,
                    next_scan_date,
                    poc,
                    poc_email,
                    customer_notes,
                    nws,
                    template,
                    recent_nws,
                    remove_nws,
                    legacy_password,
                    schedule_id,
                    qualys_error,
                    assignee_emailed_at,
                    assignee_email_message_id,
                    assignee_email_error
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                RETURNING id
                """,
                (
                    row.source_row_number,
                    row.data_pull_date,
                    row.tag,
                    row.scan_name,
                    row.assignee_id,
                    row.assignee,
                    row.status,
                    row.result,
                    row.report_sent_date,
                    row.report_scan_notes,
                    row.scan_start_date,
                    row.next_scan_date,
                    row.poc,
                    row.poc_email,
                    row.customer_notes,
                    row.nws,
                    row.template,
                    row.recent_nws,
                    row.remove_nws,
                    row.legacy_password,
                    row.schedule_id,
                    row.qualys_error,
                    row.assignee_emailed_at,
                    row.assignee_email_message_id,
                    row.assignee_email_error,
                ),
            )
            inserted_row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    return inserted_row[0]


def insert_daily_report_tracker_row_in_db(row: DailyReportTrackerRow) -> int:
    """Insert one tracker row using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return insert_daily_report_tracker_row(row=row, conn=conn)
    finally:
        close(conn)


def latest_tracker_pull_date(conn: connection) -> datetime:
    """Return the latest tracker pull date or a safe initial fallback."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT MAX(data_pull_date)
            FROM was_daily_report_tracker
            """
        )
        row = cursor.fetchone()

    if row is None or row[0] is None:
        return datetime.now(timezone.utc)

    return datetime.combine(row[0], datetime.min.time(), timezone.utc)


def recent_schedule_ids(conn: connection, since_date: datetime) -> List[int]:
    """Return schedule IDs already tracked since the supplied pull date."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT schedule_id
            FROM was_daily_report_tracker
            WHERE data_pull_date >= %s
              AND schedule_id IS NOT NULL
            """,
            (since_date.date(),),
        )
        rows = cursor.fetchall()

    return [int(row[0]) for row in rows]


def list_ready_assignee_digests(
    conn: connection,
    data_pull_date: Optional[date] = None,
    limit: Optional[int] = None,
) -> List[AssigneeDigest]:
    """Return unsent tracker rows grouped by active assignee email address."""
    query = """
        SELECT
            tracker.id,
            tracker.source_row_number,
            tracker.data_pull_date,
            tracker.tag,
            tracker.scan_name,
            tracker.assignee_id,
            tracker.assignee,
            tracker.status,
            tracker.result,
            tracker.report_sent_date,
            tracker.report_scan_notes,
            tracker.scan_start_date,
            tracker.next_scan_date,
            tracker.poc,
            tracker.poc_email,
            tracker.customer_notes,
            tracker.nws,
            tracker.template,
            tracker.recent_nws,
            tracker.remove_nws,
            tracker.legacy_password,
            tracker.schedule_id,
            tracker.qualys_error,
            assignees.email
        FROM was_daily_report_tracker tracker
        JOIN was_assignees assignees
          ON assignees.id = tracker.assignee_id
        WHERE tracker.assignee_emailed_at IS NULL
          AND tracker.assignee_email_error IS NULL
          AND assignees.active IS TRUE
          AND assignees.email_enabled IS TRUE
          AND assignees.email IS NOT NULL
          AND BTRIM(assignees.email) <> ''
          AND tracker.data_pull_date IS NOT NULL
    """
    parameters = []

    if data_pull_date is not None:
        query += " AND tracker.data_pull_date = %s"
        parameters.append(data_pull_date)

    query += " ORDER BY assignees.id ASC, tracker.id ASC"

    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    digests_by_assignee: Dict[int, AssigneeDigest] = {}
    for row in rows:
        tracker_row = DailyReportTrackerRow(
            source_row_number=row[1],
            data_pull_date=row[2],
            tag=row[3],
            scan_name=row[4],
            assignee_id=row[5],
            assignee=row[6],
            status=row[7],
            result=row[8],
            report_sent_date=row[9],
            report_scan_notes=row[10],
            scan_start_date=row[11],
            next_scan_date=row[12],
            poc=row[13],
            poc_email=row[14],
            customer_notes=row[15],
            nws=row[16],
            template=row[17],
            recent_nws=row[18],
            remove_nws=row[19],
            legacy_password=row[20],
            schedule_id=row[21],
            qualys_error=row[22],
        )
        if row[5] not in digests_by_assignee:
            digests_by_assignee[row[5]] = AssigneeDigest(
                assignee_id=row[5],
                assignee=row[6],
                email=row[23],
                rows=[],
            )
        digests_by_assignee[row[5]].rows.append(tracker_row)

    return list(digests_by_assignee.values())


def list_ready_assignee_digests_from_db(
    data_pull_date: Optional[date] = None,
    limit: Optional[int] = None,
) -> List[AssigneeDigest]:
    """Return ready assignee digests using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_ready_assignee_digests(
            conn=conn,
            data_pull_date=data_pull_date,
            limit=limit,
        )
    finally:
        close(conn)


def mark_assignee_digest_emailed(
    conn: connection,
    assignee_id: int,
    data_pull_date: date,
    message_id: str,
) -> None:
    """Mark tracker rows for an assignee and pull date as emailed."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET assignee_emailed_at = NOW(),
                    assignee_email_message_id = %s,
                    assignee_email_error = NULL,
                    updated_at = NOW()
                WHERE assignee_id = %s
                  AND data_pull_date = %s
                  AND assignee_emailed_at IS NULL
                """,
                (message_id, assignee_id, data_pull_date),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_assignee_digest_failed(
    conn: connection,
    assignee_id: int,
    data_pull_date: date,
    error_message: str,
) -> None:
    """Record an assignee digest email failure for tracker rows."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET assignee_email_error = %s,
                    updated_at = NOW()
                WHERE assignee_id = %s
                  AND data_pull_date = %s
                  AND assignee_emailed_at IS NULL
                """,
                (error_message, assignee_id, data_pull_date),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def list_tracker_rows_for_export(
    conn: connection,
    data_pull_date: Optional[date] = None,
    assignee_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[DailyReportTrackerRow]:
    """Return tracker rows for CSV export."""
    query = """
        SELECT
            source_row_number,
            data_pull_date,
            tag,
            scan_name,
            assignee_id,
            assignee,
            status,
            result,
            report_sent_date,
            report_scan_notes,
            scan_start_date,
            next_scan_date,
            poc,
            poc_email,
            customer_notes,
            nws,
            template,
            recent_nws,
            remove_nws,
            legacy_password,
            schedule_id,
            qualys_error
        FROM was_daily_report_tracker
        WHERE 1 = 1
    """
    parameters = []

    if data_pull_date is not None:
        query += " AND data_pull_date = %s"
        parameters.append(data_pull_date)

    if assignee_id is not None:
        query += " AND assignee_id = %s"
        parameters.append(assignee_id)

    query += " ORDER BY data_pull_date DESC, assignee ASC, tag ASC"

    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    return [
        DailyReportTrackerRow(
            source_row_number=row[0],
            data_pull_date=row[1],
            tag=row[2],
            scan_name=row[3],
            assignee_id=row[4],
            assignee=row[5],
            status=row[6],
            result=row[7],
            report_sent_date=row[8],
            report_scan_notes=row[9],
            scan_start_date=row[10],
            next_scan_date=row[11],
            poc=row[12],
            poc_email=row[13],
            customer_notes=row[14],
            nws=row[15],
            template=row[16],
            recent_nws=row[17],
            remove_nws=row[18],
            legacy_password=row[19],
            schedule_id=row[20],
            qualys_error=row[21],
        )
        for row in rows
    ]


def list_tracker_rows_for_export_from_db(
    data_pull_date: Optional[date] = None,
    assignee_id: Optional[int] = None,
    limit: Optional[int] = None,
) -> List[DailyReportTrackerRow]:
    """Return tracker rows for CSV export using a managed connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_tracker_rows_for_export(
            conn=conn,
            data_pull_date=data_pull_date,
            assignee_id=assignee_id,
            limit=limit,
        )
    finally:
        close(conn)
