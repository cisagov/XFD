"""Report run data access for WAS batch execution tracking."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection

RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
EMAIL_PENDING = "pending"
EMAIL_SENDING = "sending"
EMAIL_SENT = "sent"
EMAIL_FAILED = "failed"
EMAIL_HELD = "held"


@dataclass(frozen=True)
class ReportRun:
    """Database representation of one WAS report execution."""

    id: int
    stakeholder_tag: str
    status: str
    output_path: str | None = None
    artifact_type: str | None = None


@dataclass(frozen=True)
class ReportRunEmail:
    """Completed report run and stakeholder email fields."""

    id: int
    stakeholder_tag: str
    output_path: str
    report_password: str | None
    distro_email: str | None
    tech_poc_email: str | None
    was_report_poc: str | None
    source_tracker_id: int | None = None


@dataclass(frozen=True)
class ReportRunError:
    """Persisted report generation and email failure details."""

    id: int
    stakeholder_tag: str
    status: str
    email_status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    email_error: str | None


def create_report_run(
    stakeholder_tag: str,
    scheduled_epoch: int | None,
    conn: connection,
    source_tracker_id: int | None = None,
    email_status: str = EMAIL_PENDING,
) -> ReportRun | None:
    """Claim a scheduled execution and return its running report record."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO was_report_runs (
                    stakeholder_tag,
                    status,
                    scheduled_epoch,
                    source_tracker_id,
                    email_status
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id, stakeholder_tag, status
                """,
                (
                    stakeholder_tag,
                    RUNNING,
                    scheduled_epoch,
                    source_tracker_id,
                    email_status,
                ),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        return None
    return ReportRun(id=row[0], stakeholder_tag=row[1], status=row[2])


def complete_report_run(
    report_run_id: int,
    conn: connection,
    output_path: str | None = None,
    artifact_type: str | None = None,
) -> None:
    """Mark a report execution record as completed."""
    update_report_run_status(
        report_run_id=report_run_id,
        status=COMPLETED,
        error_message=None,
        output_path=output_path,
        artifact_type=artifact_type,
        conn=conn,
    )


def fail_report_run(
    report_run_id: int,
    error_message: str,
    conn: connection,
) -> None:
    """Mark a report execution record as failed."""
    update_report_run_status(
        report_run_id=report_run_id,
        status=FAILED,
        error_message=error_message,
        output_path=None,
        artifact_type=None,
        conn=conn,
    )


def update_report_run_status(
    report_run_id: int,
    status: str,
    error_message: str | None,
    output_path: str | None,
    artifact_type: str | None,
    conn: connection,
) -> None:
    """Update report execution status and completion metadata."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET status = %s,
                    completed_at = NOW(),
                    error_message = %s,
                    output_path = COALESCE(%s, output_path),
                    artifact_type = COALESCE(%s, artifact_type),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    status,
                    error_message,
                    output_path,
                    artifact_type,
                    report_run_id,
                ),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def create_report_run_for_tag(
    stakeholder_tag: str,
    scheduled_epoch: int | None,
) -> ReportRun | None:
    """Create a report execution record using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return create_report_run(
            stakeholder_tag=stakeholder_tag,
            scheduled_epoch=scheduled_epoch,
            conn=conn,
            source_tracker_id=None,
        )
    finally:
        close(conn)


def create_on_demand_report_run(
    stakeholder_tag: str,
    source_tracker_id: int | None = None,
) -> ReportRun:
    """Claim an explicit request without inventing a scan or schedule record."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT retired FROM was_stakeholders
                WHERE tag = %s FOR UPDATE
                """,
                (stakeholder_tag,),
            )
            stakeholder = cursor.fetchone()
            if stakeholder is None or stakeholder[0] is True:
                raise ValueError("An active WAS stakeholder is required.")
            cursor.execute(
                """
                SELECT id FROM was_report_runs
                WHERE stakeholder_tag = %s AND scheduled_epoch IS NULL
                  AND (status = 'running' OR email_status = 'sending')
                LIMIT 1
                """,
                (stakeholder_tag,),
            )
            if cursor.fetchone() is not None:
                raise RuntimeError("A report operation is already active for this tag.")
            if source_tracker_id is not None:
                cursor.execute(
                    """
                    SELECT tag, report_sent_date FROM was_daily_report_tracker
                    WHERE id = %s FOR UPDATE
                    """,
                    (source_tracker_id,),
                )
                tracker = cursor.fetchone()
                if (
                    tracker is None
                    or tracker[0] != stakeholder_tag
                    or tracker[1] is not None
                ):
                    raise ValueError("Tracker row must match the tag and be unsent.")
        report_run = create_report_run(
            stakeholder_tag,
            None,
            conn,
            source_tracker_id=source_tracker_id,
            email_status=EMAIL_HELD,
        )
        if report_run is None:
            raise RuntimeError(
                "Tracker row already has a report run; "
                "inspect that run before retrying."
            )
        return report_run
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)


def create_report_run_for_tracker(
    stakeholder_tag: str,
    source_tracker_id: int,
) -> ReportRun | None:
    """Atomically claim one daily tracker row for report generation."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return create_report_run(
            stakeholder_tag=stakeholder_tag,
            scheduled_epoch=None,
            source_tracker_id=source_tracker_id,
            conn=conn,
        )
    finally:
        close(conn)


def retry_failed_report_run_for_tracker(
    source_tracker_id: int,
    conn: connection,
) -> ReportRun | None:
    """Atomically reclaim one failed tracker report run for generation."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET status = %s,
                    output_path = NULL,
                    artifact_type = NULL,
                    completed_at = NULL,
                    error_message = NULL,
                    email_error = NULL,
                    email_status = %s,
                    email_claimed_at = NULL,
                    updated_at = NOW()
                WHERE source_tracker_id = %s
                  AND status = %s
                RETURNING id, stakeholder_tag, status
                """,
                (RUNNING, EMAIL_PENDING, source_tracker_id, FAILED),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        return None
    return ReportRun(id=row[0], stakeholder_tag=row[1], status=row[2])


def retry_failed_report_run_for_tracker_by_id(
    source_tracker_id: int,
) -> ReportRun | None:
    """Reclaim one failed tracker report run using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return retry_failed_report_run_for_tracker(
            source_tracker_id=source_tracker_id,
            conn=conn,
        )
    finally:
        close(conn)


def complete_report_run_by_id(
    report_run_id: int,
    output_path: str | None = None,
    artifact_type: str | None = None,
) -> None:
    """Complete a report execution record using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        complete_report_run(
            report_run_id=report_run_id,
            output_path=output_path,
            artifact_type=artifact_type,
            conn=conn,
        )
    finally:
        close(conn)


def fail_report_run_by_id(report_run_id: int, error_message: str) -> None:
    """Fail a report execution record using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        fail_report_run(
            report_run_id=report_run_id,
            error_message=error_message,
            conn=conn,
        )
    finally:
        close(conn)


def list_report_run_errors(
    conn: connection,
    days_back: int = 7,
    stakeholder_tag: str | None = None,
    limit: int = 100,
) -> list[ReportRunError]:
    """Return recent persisted report generation and delivery errors."""
    if days_back < 0:
        raise ValueError("Days back must be zero or greater.")
    if limit < 1:
        raise ValueError("Limit must be greater than zero.")
    normalized_tag = None
    if stakeholder_tag is not None:
        normalized_tag = stakeholder_tag.strip()
        if not normalized_tag:
            raise ValueError("Stakeholder tag must not be empty.")

    query = """
        SELECT
            id,
            stakeholder_tag,
            status,
            email_status,
            started_at,
            completed_at,
            error_message,
            email_error
        FROM was_report_runs
        WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
          AND (
                NULLIF(BTRIM(error_message), '') IS NOT NULL
             OR NULLIF(BTRIM(email_error), '') IS NOT NULL
          )
    """
    parameters: list[object] = [days_back]
    if normalized_tag is not None:
        query += " AND stakeholder_tag = %s"
        parameters.append(normalized_tag)
    query += " ORDER BY created_at DESC, id DESC LIMIT %s"
    parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    return [
        ReportRunError(
            id=row[0],
            stakeholder_tag=row[1],
            status=row[2],
            email_status=row[3],
            started_at=row[4],
            completed_at=row[5],
            error_message=row[6],
            email_error=row[7],
        )
        for row in rows
    ]


def list_report_run_errors_from_db(
    days_back: int = 7,
    stakeholder_tag: str | None = None,
    limit: int = 100,
) -> list[ReportRunError]:
    """Return recent report errors using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_report_run_errors(
            conn=conn,
            days_back=days_back,
            stakeholder_tag=stakeholder_tag,
            limit=limit,
        )
    finally:
        close(conn)


def get_report_run_email(report_run_id: int, conn: connection) -> ReportRunEmail:
    """Return completed report run details needed for email delivery."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                runs.id,
                runs.stakeholder_tag,
                runs.output_path,
                stakeholders.report_password,
                stakeholders.distro_email,
                stakeholders.tech_poc_email,
                stakeholders.was_report_poc,
                runs.source_tracker_id
            FROM was_report_runs AS runs
            JOIN was_stakeholders AS stakeholders
              ON stakeholders.tag = runs.stakeholder_tag
            WHERE runs.id = %s
              AND runs.status = %s
              AND runs.output_path IS NOT NULL
              AND runs.emailed_at IS NULL
            """,
            (report_run_id, COMPLETED),
        )
        row = cursor.fetchone()

    if row is None:
        raise KeyError(
            "Completed report run {} with output path was not found.".format(
                report_run_id
            )
        )

    return ReportRunEmail(
        id=row[0],
        stakeholder_tag=row[1],
        output_path=row[2],
        report_password=row[3],
        distro_email=row[4],
        tech_poc_email=row[5],
        was_report_poc=row[6],
        source_tracker_id=row[7],
    )


def list_report_runs_ready_for_email(
    conn: connection,
    limit: int | None = None,
    include_previous_failures: bool = False,
    stakeholder_tag: str | None = None,
) -> list[ReportRunEmail]:
    """Return completed report runs that have not been emailed."""
    query = """
        SELECT
            runs.id,
            runs.stakeholder_tag,
            runs.output_path,
            stakeholders.report_password,
            stakeholders.distro_email,
            stakeholders.tech_poc_email,
            stakeholders.was_report_poc,
            runs.source_tracker_id
        FROM was_report_runs AS runs
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = runs.stakeholder_tag
        WHERE runs.status = %s
          AND runs.output_path IS NOT NULL
          AND runs.emailed_at IS NULL
          AND COALESCE(runs.email_status, %s) = ANY(%s)
    """
    allowed_email_statuses = [EMAIL_PENDING]
    if include_previous_failures:
        allowed_email_statuses.append(EMAIL_FAILED)
    parameters: list[object] = [
        COMPLETED,
        EMAIL_PENDING,
        allowed_email_statuses,
    ]

    if stakeholder_tag is not None:
        query += " AND runs.stakeholder_tag = %s"
        parameters.append(stakeholder_tag)

    query += " ORDER BY runs.completed_at ASC NULLS LAST, runs.id ASC"

    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    report_runs = []
    for row in rows:
        report_runs.append(
            ReportRunEmail(
                id=row[0],
                stakeholder_tag=row[1],
                output_path=row[2],
                report_password=row[3],
                distro_email=row[4],
                tech_poc_email=row[5],
                was_report_poc=row[6],
                source_tracker_id=row[7],
            )
        )

    return report_runs


def claim_report_run_email(
    report_run_id: int,
    conn: connection,
    include_previous_failure: bool = False,
    allow_held: bool = False,
) -> ReportRunEmail | None:
    """Atomically claim one completed report run for email delivery."""
    allowed_email_statuses = [EMAIL_PENDING]
    if allow_held:
        allowed_email_statuses.append(EMAIL_HELD)
    if include_previous_failure:
        allowed_email_statuses.append(EMAIL_FAILED)
    query = """
        WITH claimed AS (
            UPDATE was_report_runs
            SET email_status = %s,
                email_claimed_at = NOW(),
                email_error = NULL,
                updated_at = NOW()
            WHERE id = %s
              AND status = %s
              AND output_path IS NOT NULL
              AND emailed_at IS NULL
              AND COALESCE(email_status, %s) = ANY(%s)
            RETURNING id, stakeholder_tag, output_path, source_tracker_id
        )
        SELECT
            claimed.id,
            claimed.stakeholder_tag,
            claimed.output_path,
            claimed.source_tracker_id,
            stakeholders.report_password,
            stakeholders.distro_email,
            stakeholders.tech_poc_email,
            stakeholders.was_report_poc
        FROM claimed
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = claimed.stakeholder_tag
    """
    parameters: list[object] = [
        EMAIL_SENDING,
        report_run_id,
        COMPLETED,
        EMAIL_PENDING,
        allowed_email_statuses,
    ]
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        return None
    return ReportRunEmail(
        id=row[0],
        stakeholder_tag=row[1],
        output_path=row[2],
        source_tracker_id=row[3],
        report_password=row[4],
        distro_email=row[5],
        tech_poc_email=row[6],
        was_report_poc=row[7],
    )


def get_report_run_email_by_id(report_run_id: int) -> ReportRunEmail:
    """Return completed report run email details using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return get_report_run_email(report_run_id=report_run_id, conn=conn)
    finally:
        close(conn)


def claim_report_run_email_by_id(
    report_run_id: int,
    include_previous_failure: bool = False,
    allow_held: bool = False,
) -> ReportRunEmail | None:
    """Atomically claim one report email using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return claim_report_run_email(
            report_run_id=report_run_id,
            conn=conn,
            include_previous_failure=include_previous_failure,
            allow_held=allow_held,
        )
    finally:
        close(conn)


def list_report_runs_ready_for_email_from_db(
    limit: int | None = None,
    include_previous_failures: bool = False,
    stakeholder_tag: str | None = None,
) -> list[ReportRunEmail]:
    """Return ready-to-email report runs using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_report_runs_ready_for_email(
            conn=conn,
            limit=limit,
            include_previous_failures=include_previous_failures,
            stakeholder_tag=stakeholder_tag,
        )
    finally:
        close(conn)


def mark_report_run_emailed(
    report_run_id: int,
    message_id: str,
    conn: connection,
) -> None:
    """Mark a report run as successfully emailed."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                WITH emailed_run AS (
                    UPDATE was_report_runs
                    SET emailed_at = NOW(),
                        email_message_id = %s,
                        email_error = NULL,
                        email_status = %s,
                        email_claimed_at = NULL,
                        updated_at = NOW()
                    WHERE id = %s
                      AND email_status = %s
                    RETURNING id, source_tracker_id
                ),
                updated_tracker AS (
                    UPDATE was_daily_report_tracker AS tracker
                    SET report_sent_date = CURRENT_DATE,
                        updated_at = NOW()
                    FROM emailed_run
                    WHERE tracker.id = emailed_run.source_tracker_id
                    RETURNING tracker.id
                )
                SELECT id FROM emailed_run
                """,
                (message_id, EMAIL_SENT, report_run_id, EMAIL_SENDING),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("WAS report email claim was not active.")
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_report_run_email_failed(
    report_run_id: int,
    error_message: str,
    conn: connection,
    hold_for_manual_retry: bool = False,
) -> None:
    """Record a report email delivery failure."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET email_error = %s,
                    email_status = %s,
                    email_claimed_at = NULL,
                    updated_at = NOW()
                WHERE id = %s
                  AND email_status = %s
                RETURNING id
                """,
                (
                    error_message,
                    EMAIL_HELD if hold_for_manual_retry else EMAIL_FAILED,
                    report_run_id,
                    EMAIL_SENDING,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("WAS report email claim was not active.")
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_report_run_emailed_by_id(report_run_id: int, message_id: str) -> None:
    """Mark a report run emailed using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_report_run_emailed(
            report_run_id=report_run_id,
            message_id=message_id,
            conn=conn,
        )
    finally:
        close(conn)


def mark_report_run_email_failed_by_id(
    report_run_id: int,
    error_message: str,
    hold_for_manual_retry: bool = False,
) -> None:
    """Record report email failure using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_report_run_email_failed(
            report_run_id=report_run_id,
            error_message=error_message,
            conn=conn,
            hold_for_manual_retry=hold_for_manual_retry,
        )
    finally:
        close(conn)
