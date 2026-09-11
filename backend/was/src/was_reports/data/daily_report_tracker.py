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
    id: int | None = None
    scan_execution_key: str | None = None
    digest_revision: int = 0


@dataclass(frozen=True)
class AssigneeDigest:
    """Tracker rows that should be emailed to one assignee."""

    assignee_id: int
    assignee: str
    email: str
    rows: list[DailyReportTrackerRow]
    claim_token: str | None = None


@dataclass(frozen=True)
class TrackerReportCandidate:
    """Recently scanned tracker row awaiting automated report delivery."""

    id: int
    tag: str
    data_pull_date: date
    schedule_id: int | None
    assignee_id: int | None
    template: str | None = None
    remove_nws: str | None = None
    report_run_id: int | None = None
    report_run_status: str | None = None
    report_email_status: str | None = None


@dataclass(frozen=True)
class TrackerTableRow:
    """Safe tracker fields displayed in the operator terminal table."""

    tracker_id: int
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
                    assignee_email_error,
                    scan_execution_key
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (scan_execution_key)
                    WHERE scan_execution_key IS NOT NULL
                DO UPDATE SET scan_execution_key = was_daily_report_tracker.scan_execution_key
                RETURNING id
                """,
                (
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
                    row.scan_execution_key,
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
    include_manual: bool = False,
) -> list[TrackerReportCandidate]:
    """Return tracker rows with a report-delivery gap."""
    query = """
        SELECT
            tracker.id,
            tracker.tag,
            tracker.data_pull_date,
            tracker.schedule_id,
            tracker.assignee_id,
            tracker.template,
            tracker.remove_nws,
            runs.id,
            runs.status,
            runs.email_status
        FROM was_daily_report_tracker AS tracker
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = tracker.tag
        LEFT JOIN was_report_runs AS runs
          ON runs.source_tracker_id = tracker.id
        WHERE tracker.report_sent_date IS NULL
          AND tracker.tag IS NOT NULL
          AND BTRIM(tracker.tag) <> ''
          AND COALESCE(tracker.template, '') <> 'Deactivated'
          AND stakeholders.retired IS NOT TRUE
    """
    parameters: list[object] = []
    if include_manual:
        query += """
          AND (
                stakeholders.manual_report IS TRUE
             OR NULLIF(BTRIM(tracker.report_scan_notes), '') IS NOT NULL
             OR NULLIF(BTRIM(tracker.qualys_error), '') IS NOT NULL
             OR UPPER(BTRIM(COALESCE(tracker.status, ''))) = 'ERROR'
          )
          AND (
                runs.id IS NULL
             OR (
                    runs.status = 'failed'
                AND COALESCE(runs.email_status, 'pending') <> 'held'
             )
             OR (
                    runs.status = 'completed'
                AND runs.emailed_at IS NULL
                AND COALESCE(runs.email_status, 'pending')
                    IN ('pending', 'failed')
             )
          )
        """
    else:
        query += """
          AND runs.id IS NULL
          AND (
                LOWER(BTRIM(COALESCE(tracker.status, ''))) = 'finished'
             OR (
                    LOWER(BTRIM(COALESCE(tracker.status, ''))) = 'error'
                AND BTRIM(COALESCE(tracker.qualys_error, '')) <> ''
             )
          )
          AND BTRIM(COALESCE(tracker.report_scan_notes, '')) = ''
          AND stakeholders.manual_report IS NOT TRUE
        """
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
            template=row[5],
            remove_nws=row[6],
            report_run_id=row[7],
            report_run_status=row[8],
            report_email_status=row[9],
        )
        for row in rows
    ]


def list_ready_report_candidates_from_db(
    stakeholder_tag: str | None = None,
    limit: int | None = None,
    include_manual: bool = False,
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
            include_manual=include_manual,
        )
    finally:
        close(conn)


def mark_tracker_report_manual(
    tracker_id: int,
    conn: connection,
    error_message: str | None = None,
) -> None:
    """Mark a tracker row for manual handling with a safe failure summary."""
    report_note = "MANUAL"
    if error_message:
        report_note = "MANUAL: {}".format(error_message)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET report_scan_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
                  AND report_sent_date IS NULL
                """,
                (report_note, tracker_id),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_tracker_report_manual_by_id(
    tracker_id: int,
    error_message: str | None = None,
) -> None:
    """Mark a tracker report manual using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_tracker_report_manual(
            tracker_id=tracker_id,
            conn=conn,
            error_message=error_message,
        )
    finally:
        close(conn)


def mark_manual_tracker_report_sent(
    tracker_id: int,
    sent_date: date,
    conn: connection,
) -> None:
    """Set the sent date for one unsent tracker row requiring manual handling."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_daily_report_tracker AS tracker
                SET report_sent_date = %s,
                    updated_at = NOW()
                FROM was_stakeholders AS stakeholders
                WHERE tracker.id = %s
                  AND stakeholders.tag = tracker.tag
                  AND tracker.report_sent_date IS NULL
                  AND (
                        stakeholders.manual_report IS TRUE
                     OR NULLIF(BTRIM(tracker.report_scan_notes), '') IS NOT NULL
                     OR NULLIF(BTRIM(tracker.qualys_error), '') IS NOT NULL
                     OR UPPER(BTRIM(COALESCE(tracker.status, ''))) = 'ERROR'
                  )
                RETURNING tracker.id
                """,
                (sent_date, tracker_id),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        raise KeyError("Unsent manual tracker row {} was not found.".format(tracker_id))


def mark_manual_tracker_report_sent_by_id(
    tracker_id: int,
    sent_date: date,
) -> None:
    """Set a manual tracker sent date using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_manual_tracker_report_sent(
            tracker_id=tracker_id,
            sent_date=sent_date,
            conn=conn,
        )
    finally:
        close(conn)


def list_ready_assignee_digests(
    conn: connection,
    data_pull_date: date | None = None,
    limit: int | None = None,
    include_previous_failures: bool = False,
) -> list[AssigneeDigest]:
    """Return unsent tracker rows grouped by active assignee email address."""
    query = """
        SELECT
            tracker.id,
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
            assignees.email,
            tracker.scan_execution_key,
            tracker.digest_revision
        FROM was_daily_report_tracker tracker
        JOIN was_assignees assignees
          ON assignees.id = tracker.assignee_id
        WHERE tracker.assignee_emailed_at IS NULL
          AND tracker.assignee_email_status = ANY(%s)
          AND assignees.active IS TRUE
          AND assignees.email_enabled IS TRUE
          AND assignees.email IS NOT NULL
          AND BTRIM(assignees.email) <> ''
          AND tracker.data_pull_date IS NOT NULL
    """
    statuses = ["pending", "failed"] if include_previous_failures else ["pending"]
    parameters: list[object] = [statuses]
    if not include_previous_failures:
        query += " AND tracker.assignee_email_error IS NULL"

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
            id=row[0],
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
            scan_execution_key=row[23],
            digest_revision=row[24],
        )
        if row[4] not in digests_by_assignee:
            digests_by_assignee[row[4]] = AssigneeDigest(
                assignee_id=row[4],
                assignee=row[5],
                email=row[22],
                rows=[],
            )
        digests_by_assignee[row[4]].rows.append(tracker_row)

    return list(digests_by_assignee.values())


def list_ready_assignee_digests_from_db(
    data_pull_date: date | None = None,
    limit: int | None = None,
    include_previous_failures: bool = False,
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
            include_previous_failures=include_previous_failures,
        )
    finally:
        close(conn)


def validate_digest_claim(row_ids: list[int], token: str) -> list[int]:
    """Validate a nonempty, unique persisted snapshot and ownership token."""
    if not token or not token.strip():
        raise ValueError("A digest claim token is required.")
    if not row_ids or any(type(row_id) is not int or row_id <= 0 for row_id in row_ids):
        raise ValueError("Digest row IDs must be positive integers.")
    if len(set(row_ids)) != len(row_ids):
        raise ValueError("Digest row IDs must be unique.")
    return sorted(row_ids)


def claim_assignee_digest_rows(
    row_ids: list[int],
    token: str,
    expected_revisions: dict[int, int] | None = None,
) -> bool:
    """Atomically claim every requested row or leave the entire snapshot unchanged."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    row_ids = validate_digest_claim(row_ids, token)
    if expected_revisions is not None and (
        set(expected_revisions) != set(row_ids)
        or any(
            type(value) is not int or value < 0 for value in expected_revisions.values()
        )
    ):
        raise ValueError("Every digest row requires a nonnegative snapshot revision.")
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, digest_revision FROM was_daily_report_tracker
                WHERE id = ANY(%s)
                  AND assignee_emailed_at IS NULL
                  AND assignee_email_status IN ('pending', 'failed')
                ORDER BY id FOR UPDATE
                """,
                (row_ids,),
            )
            rows = cursor.fetchall()
            if [row[0] for row in rows] != row_ids or (
                expected_revisions is not None
                and any(row[1] != expected_revisions[row[0]] for row in rows)
            ):
                conn.rollback()
                return False
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET assignee_email_status = 'sending',
                    assignee_email_claim_token = %s,
                    assignee_email_claimed_at = NOW(),
                    digest_claimed_revision = digest_revision,
                    assignee_email_error = NULL,
                    updated_at = NOW()
                WHERE id = ANY(%s)
                """,
                (token, row_ids),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)


def finish_assignee_digest_rows(
    row_ids: list[int],
    token: str,
    message_id: str | None = None,
    error_message: str | None = None,
    uncertain: bool = False,
) -> None:
    """Finish only a fully owned snapshot, holding any uncertain delivery."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    row_ids = validate_digest_claim(row_ids, token)
    if (not message_id and not error_message) or (message_id and error_message):
        raise ValueError("Supply exactly one digest delivery result.")
    status = "held" if uncertain else ("sent" if message_id else "failed")
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM was_daily_report_tracker
                WHERE id = ANY(%s)
                  AND assignee_email_status = 'sending'
                  AND assignee_email_claim_token = %s
                ORDER BY id FOR UPDATE
                """,
                (row_ids, token),
            )
            if [row[0] for row in cursor.fetchall()] != row_ids:
                raise RuntimeError("Digest claim ownership was lost.")
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET assignee_email_status = CASE
                        WHEN %s = 'sent'
                         AND digest_revision IS DISTINCT FROM digest_claimed_revision
                            THEN 'pending'
                        ELSE %s END,
                    assignee_emailed_at = CASE
                        WHEN %s = 'sent' AND digest_revision = digest_claimed_revision
                            THEN NOW()
                        ELSE NULL END,
                    assignee_email_message_id = %s,
                    assignee_email_error = %s,
                    assignee_email_claim_token = NULL,
                    assignee_email_claimed_at = NULL,
                    digest_claimed_revision = NULL,
                    updated_at = NOW()
                WHERE id = ANY(%s)
                  AND assignee_email_claim_token = %s
                  AND assignee_email_status = 'sending'
                """,
                (status, status, status, message_id, error_message, row_ids, token),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)


def record_tracker_digest_failure(
    tracker_id: int, conn: connection, error_message: str | None = None
) -> None:
    """Queue a failure revision and append an already-sanitized stage summary."""
    note = "MANUAL: {}".format(error_message.strip()) if error_message else None
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE was_daily_report_tracker
            SET digest_revision = digest_revision + 1,
                assignee_emailed_at = NULL,
                assignee_email_status = CASE
                    WHEN assignee_email_status IN ('sending', 'held')
                        THEN assignee_email_status
                    ELSE 'pending' END,
                assignee_email_error = CASE
                    WHEN assignee_email_status IN ('sending', 'held')
                        THEN assignee_email_error
                    ELSE NULL END,
                report_scan_notes = CASE
                    WHEN %s IS NULL OR position(%s in COALESCE(report_scan_notes, '')) > 0
                        THEN report_scan_notes
                    ELSE concat_ws(E'\\n', NULLIF(report_scan_notes, ''), %s)
                    END,
                updated_at = NOW()
            WHERE id = %s
            """,
            (note, note, note, tracker_id),
        )


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
            id,
            scan_execution_key
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
            data_pull_date=row[0],
            tag=row[1],
            scan_name=row[2],
            assignee_id=row[3],
            assignee=row[4],
            status=row[5],
            result=row[6],
            report_sent_date=row[7],
            report_scan_notes=row[8],
            scan_start_date=row[9],
            next_scan_date=row[10],
            poc=row[11],
            poc_email=row[12],
            customer_notes=row[13],
            nws=row[14],
            template=row[15],
            recent_nws=row[16],
            remove_nws=row[17],
            legacy_password=row[18],
            schedule_id=row[19],
            qualys_error=row[20],
            id=row[21],
            scan_execution_key=row[22],
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
    assignee_name: str | None = None,
    report_status: str | None = None,
    limit: int | None = 200,
) -> list[TrackerTableRow]:
    """Return recent tracker rows without sensitive fields."""
    if days_back < 0:
        raise ValueError("Days back must be zero or greater.")
    normalized_assignee = None
    if assignee_name is not None:
        normalized_assignee = assignee_name.strip()
        if not normalized_assignee:
            raise ValueError("Assignee name must not be empty.")
    normalized_report_status = None
    if report_status is not None:
        normalized_report_status = report_status.strip().upper()
        if normalized_report_status not in {"MANUAL", "PENDING", "SENT"}:
            raise ValueError("Report status must be MANUAL, PENDING, or SENT.")
    if limit is not None and limit < 1:
        raise ValueError("Limit must be greater than zero.")

    query = """
        WITH tracker_rows AS (
            SELECT
                tracker.id,
                tracker.data_pull_date,
                tracker.tag,
                tracker.scan_name,
                COALESCE(assignees.name, tracker.assignee) AS assignee,
                tracker.status,
                tracker.result,
                CASE
                    WHEN tracker.report_sent_date IS NOT NULL THEN 'SENT'
                    WHEN stakeholders.manual_report IS TRUE
                      OR NULLIF(BTRIM(tracker.report_scan_notes), '')
                         IS NOT NULL
                      OR NULLIF(BTRIM(tracker.qualys_error), '') IS NOT NULL
                      OR UPPER(BTRIM(COALESCE(tracker.status, ''))) = 'ERROR'
                        THEN 'MANUAL'
                    ELSE 'PENDING'
                END AS report_status,
                tracker.report_sent_date,
                tracker.report_scan_notes,
                tracker.next_scan_date
            FROM was_daily_report_tracker AS tracker
            LEFT JOIN was_assignees AS assignees
              ON assignees.id = tracker.assignee_id
            LEFT JOIN was_stakeholders AS stakeholders
              ON stakeholders.tag = tracker.tag
            WHERE tracker.data_pull_date >= CURRENT_DATE - %s
    """
    parameters: list[object] = [days_back]
    if normalized_assignee is not None:
        query += """
              AND LOWER(BTRIM(COALESCE(
                    assignees.name,
                    tracker.assignee,
                    ''
                  ))) = LOWER(BTRIM(%s))
        """
        parameters.append(normalized_assignee)
    query += """
        )
        SELECT
            id,
            data_pull_date,
            tag,
            scan_name,
            assignee,
            status,
            result,
            report_status,
            report_sent_date,
            report_scan_notes,
            next_scan_date
        FROM tracker_rows
        WHERE 1 = 1
    """
    if normalized_report_status is not None:
        query += " AND report_status = %s"
        parameters.append(normalized_report_status)
    query += " ORDER BY data_pull_date DESC, tag ASC"
    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    return [
        TrackerTableRow(
            tracker_id=row[0],
            data_pull_date=row[1],
            tag=row[2],
            scan_name=row[3],
            assignee=row[4],
            scan_status=row[5],
            scan_result=row[6],
            report_status=row[7],
            report_sent_date=row[8],
            notes=row[9],
            next_scan_date=row[10],
        )
        for row in rows
    ]


def list_tracker_table_rows_from_db(
    days_back: int,
    assignee_name: str | None = None,
    report_status: str | None = None,
    limit: int | None = 200,
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
            report_status=report_status,
            limit=limit,
        )
    finally:
        close(conn)
