"""Data access helpers for WAS daily report tracker rows."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection


@dataclass(frozen=True)
class DailyReportTrackerRow:
    """Database representation of one WAS daily report tracker row."""

    source_row_number: int | None = None
    data_pull_date: date | None = None
    tag: str | None = None
    scan_name: str | None = None
    assignee_id: int | None = None
    assignee: str | None = None
    status: str | None = None
    result: str | None = None
    report_sent_date: date | None = None
    report_scan_notes: str | None = None
    scan_start_date: date | None = None
    next_scan_date: date | None = None
    poc: str | None = None
    poc_email: str | None = None
    customer_notes: str | None = None
    nws: str | None = None
    template: str | None = None
    recent_nws: str | None = None
    remove_nws: str | None = None
    legacy_password: str | None = None
    schedule_id: int | None = None
    qualys_error: str | None = None
    assignee_emailed_at: datetime | None = None
    assignee_email_message_id: str | None = None
    assignee_email_error: str | None = None


@dataclass(frozen=True)
class AssigneeDigest:
    """Tracker rows that should be emailed to one assignee."""

    assignee_id: int
    assignee: str
    email: str
    rows: list[DailyReportTrackerRow]


@dataclass(frozen=True)
class TrackerReportCandidate:
    """Recently scanned tracker row awaiting automated report delivery."""

    id: int
    tag: str
    data_pull_date: date
    schedule_id: int | None
    assignee_id: int | None


@dataclass(frozen=True)
class TrackerTableRow:
    """Safe tracker fields displayed in the operator terminal table."""

    data_pull_date: date | None
    tag: str | None
    scan_name: str | None
    assignee: str | None
    scan_status: str | None
    scan_result: str | None
    report_status: str
    report_sent_date: date | None
    notes: str | None
    next_scan_date: date | None


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
    # Third-Party Libraries
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


def recent_schedule_ids(conn: connection, since_date: datetime) -> list[int]:
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


def list_ready_report_candidates(
    conn: connection,
    stakeholder_tag: str | None = None,
    limit: int | None = None,
) -> list[TrackerReportCandidate]:
    """Return finished tracker rows with a report-delivery gap."""
    query = """
        SELECT
            tracker.id,
            tracker.tag,
            tracker.data_pull_date,
            tracker.schedule_id,
            tracker.assignee_id
        FROM was_daily_report_tracker AS tracker
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = tracker.tag
        LEFT JOIN was_report_runs AS runs
          ON runs.source_tracker_id = tracker.id
        WHERE tracker.report_sent_date IS NULL
          AND runs.id IS NULL
          AND tracker.tag IS NOT NULL
          AND BTRIM(tracker.tag) <> ''
          AND LOWER(BTRIM(COALESCE(tracker.status, ''))) = 'finished'
          AND BTRIM(COALESCE(tracker.report_scan_notes, '')) = ''
          AND BTRIM(COALESCE(tracker.qualys_error, '')) = ''
          AND COALESCE(tracker.template, '') <> 'Deactivated'
          AND stakeholders.manual_report IS NOT TRUE
          AND stakeholders.retired IS NOT TRUE
    """
    parameters: list[object] = []
    if stakeholder_tag is not None:
        query += " AND tracker.tag = %s"
        parameters.append(stakeholder_tag)
    query += " ORDER BY tracker.data_pull_date ASC, tracker.id ASC"
    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    return [
        TrackerReportCandidate(
            id=row[0],
            tag=row[1],
            data_pull_date=row[2],
            schedule_id=row[3],
            assignee_id=row[4],
        )
        for row in rows
    ]


def list_ready_report_candidates_from_db(
    stakeholder_tag: str | None = None,
    limit: int | None = None,
) -> list[TrackerReportCandidate]:
    """Return report-delivery gaps using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_ready_report_candidates(
            conn=conn,
            stakeholder_tag=stakeholder_tag,
            limit=limit,
        )
    finally:
        close(conn)


def mark_tracker_report_manual(
    tracker_id: int,
    conn: connection,
) -> None:
    """Mark a tracker row for manual handling after generation failure."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET report_scan_notes = 'MANUAL',
                    updated_at = NOW()
                WHERE id = %s
                  AND report_sent_date IS NULL
                """,
                (tracker_id,),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_tracker_report_manual_by_id(tracker_id: int) -> None:
    """Mark a tracker report manual using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_tracker_report_manual(tracker_id=tracker_id, conn=conn)
    finally:
        close(conn)


def list_ready_assignee_digests(
    conn: connection,
    data_pull_date: date | None = None,
    limit: int | None = None,
) -> list[AssigneeDigest]:
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
    parameters: list[object] = []

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

    digests_by_assignee: dict[int, AssigneeDigest] = {}
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
    data_pull_date: date | None = None,
    limit: int | None = None,
) -> list[AssigneeDigest]:
    """Return ready assignee digests using a managed database connection."""
    # Third-Party Libraries
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
    data_pull_date: date | None = None,
    assignee_id: int | None = None,
    days_back: int | None = None,
    assignee_name: str | None = None,
    limit: int | None = None,
) -> list[DailyReportTrackerRow]:
    """Return tracker rows for CSV export."""
    if days_back is not None and days_back < 0:
        raise ValueError("Days back must be zero or greater.")
    normalized_assignee = None
    if assignee_name is not None:
        normalized_assignee = assignee_name.strip()
        if not normalized_assignee:
            raise ValueError("Assignee name must not be empty.")
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
    parameters: list[object] = []

    if data_pull_date is not None:
        query += " AND data_pull_date = %s"
        parameters.append(data_pull_date)

    if days_back is not None:
        query += " AND data_pull_date >= CURRENT_DATE - %s"
        parameters.append(days_back)

    if assignee_id is not None:
        query += " AND assignee_id = %s"
        parameters.append(assignee_id)

    if normalized_assignee is not None:
        query += " AND LOWER(BTRIM(COALESCE(assignee, ''))) = LOWER(BTRIM(%s))"
        parameters.append(normalized_assignee)

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
    data_pull_date: date | None = None,
    assignee_id: int | None = None,
    days_back: int | None = None,
    assignee_name: str | None = None,
    limit: int | None = None,
) -> list[DailyReportTrackerRow]:
    """Return tracker rows for CSV export using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_tracker_rows_for_export(
            conn=conn,
            data_pull_date=data_pull_date,
            assignee_id=assignee_id,
            days_back=days_back,
            assignee_name=assignee_name,
            limit=limit,
        )
    finally:
        close(conn)


def list_tracker_table_rows(
    conn: connection,
    days_back: int,
    assignee_name: str,
    limit: int = 200,
) -> list[TrackerTableRow]:
    """Return recent tracker rows for one assignee without sensitive fields."""
    if days_back < 0:
        raise ValueError("Days back must be zero or greater.")
    normalized_assignee = assignee_name.strip()
    if not normalized_assignee:
        raise ValueError("Assignee name must not be empty.")
    if limit < 1:
        raise ValueError("Limit must be greater than zero.")

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tracker.data_pull_date,
                tracker.tag,
                tracker.scan_name,
                COALESCE(assignees.name, tracker.assignee),
                tracker.status,
                tracker.result,
                CASE
                    WHEN tracker.report_sent_date IS NOT NULL THEN 'SENT'
                    WHEN NULLIF(BTRIM(tracker.report_scan_notes), '')
                         IS NOT NULL
                      OR NULLIF(BTRIM(tracker.qualys_error), '') IS NOT NULL
                      OR UPPER(BTRIM(COALESCE(tracker.status, ''))) = 'ERROR'
                        THEN 'MANUAL'
                    ELSE 'PENDING'
                END,
                tracker.report_sent_date,
                tracker.report_scan_notes,
                tracker.next_scan_date
            FROM was_daily_report_tracker AS tracker
            LEFT JOIN was_assignees AS assignees
              ON assignees.id = tracker.assignee_id
            WHERE tracker.data_pull_date >= CURRENT_DATE - %s
              AND LOWER(BTRIM(COALESCE(
                    assignees.name,
                    tracker.assignee,
                    ''
                  ))) = LOWER(BTRIM(%s))
            ORDER BY tracker.data_pull_date DESC, tracker.tag ASC
            LIMIT %s
            """,
            (days_back, normalized_assignee, limit),
        )
        rows = cursor.fetchall()

    return [
        TrackerTableRow(
            data_pull_date=row[0],
            tag=row[1],
            scan_name=row[2],
            assignee=row[3],
            scan_status=row[4],
            scan_result=row[5],
            report_status=row[6],
            report_sent_date=row[7],
            notes=row[8],
            next_scan_date=row[9],
        )
        for row in rows
    ]


def list_tracker_table_rows_from_db(
    days_back: int,
    assignee_name: str,
    limit: int = 200,
) -> list[TrackerTableRow]:
    """Return recent assignee tracker rows using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_tracker_table_rows(
            conn=conn,
            days_back=days_back,
            assignee_name=assignee_name,
            limit=limit,
        )
    finally:
        close(conn)
