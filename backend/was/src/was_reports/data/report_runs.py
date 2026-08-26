"""Report run data access for WAS batch execution tracking."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection

RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"


@dataclass(frozen=True)
class ReportRun:
    """Database representation of one WAS report execution."""

    id: int
    stakeholder_tag: str
    status: str
    output_path: Optional[str] = None
    artifact_type: Optional[str] = None


@dataclass(frozen=True)
class ReportRunEmail:
    """Completed report run and stakeholder email fields."""

    id: int
    stakeholder_tag: str
    output_path: str
    report_password: Optional[str]
    distro_email: Optional[str]
    tech_poc_email: Optional[str]
    was_report_poc: Optional[str]


def create_report_run(
    stakeholder_tag: str,
    scheduled_epoch: Optional[int],
    conn: connection,
) -> ReportRun:
    """Create a running report execution record."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO was_report_runs (
                    stakeholder_tag,
                    status,
                    scheduled_epoch
                )
                VALUES (%s, %s, %s)
                RETURNING id, stakeholder_tag, status
                """,
                (stakeholder_tag, RUNNING, scheduled_epoch),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    return ReportRun(id=row[0], stakeholder_tag=row[1], status=row[2])


def complete_report_run(
    report_run_id: int,
    conn: connection,
    output_path: Optional[str] = None,
    artifact_type: Optional[str] = None,
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
    error_message: Optional[str],
    output_path: Optional[str],
    artifact_type: Optional[str],
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
    scheduled_epoch: Optional[int],
) -> ReportRun:
    """Create a report execution record using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return create_report_run(
            stakeholder_tag=stakeholder_tag,
            scheduled_epoch=scheduled_epoch,
            conn=conn,
        )
    finally:
        close(conn)


def complete_report_run_by_id(
    report_run_id: int,
    output_path: Optional[str] = None,
    artifact_type: Optional[str] = None,
) -> None:
    """Complete a report execution record using a managed database connection."""
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
                stakeholders.was_report_poc
            FROM was_report_runs AS runs
            JOIN was_stakeholders AS stakeholders
              ON stakeholders.tag = runs.stakeholder_tag
            WHERE runs.id = %s
              AND runs.status = %s
              AND runs.output_path IS NOT NULL
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
    )


def list_report_runs_ready_for_email(
    conn: connection,
    limit: Optional[int] = None,
    include_previous_failures: bool = False,
) -> List[ReportRunEmail]:
    """Return completed report runs that have not been emailed."""
    query = """
        SELECT
            runs.id,
            runs.stakeholder_tag,
            runs.output_path,
            stakeholders.report_password,
            stakeholders.distro_email,
            stakeholders.tech_poc_email,
            stakeholders.was_report_poc
        FROM was_report_runs AS runs
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = runs.stakeholder_tag
        WHERE runs.status = %s
          AND runs.output_path IS NOT NULL
          AND runs.emailed_at IS NULL
    """
    parameters = [COMPLETED]

    if not include_previous_failures:
        query += " AND runs.email_error IS NULL"

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
            )
        )

    return report_runs


def get_report_run_email_by_id(report_run_id: int) -> ReportRunEmail:
    """Return completed report run email details using a managed connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return get_report_run_email(report_run_id=report_run_id, conn=conn)
    finally:
        close(conn)


def list_report_runs_ready_for_email_from_db(
    limit: Optional[int] = None,
    include_previous_failures: bool = False,
) -> List[ReportRunEmail]:
    """Return ready-to-email report runs using a managed connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_report_runs_ready_for_email(
            conn=conn,
            limit=limit,
            include_previous_failures=include_previous_failures,
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
                UPDATE was_report_runs
                SET emailed_at = NOW(),
                    email_message_id = %s,
                    email_error = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (message_id, report_run_id),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_report_run_email_failed(
    report_run_id: int,
    error_message: str,
    conn: connection,
) -> None:
    """Record a report email delivery failure."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET email_error = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (error_message, report_run_id),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_report_run_emailed_by_id(report_run_id: int, message_id: str) -> None:
    """Mark a report run emailed using a managed database connection."""
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
) -> None:
    """Record report email failure using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_report_run_email_failed(
            report_run_id=report_run_id,
            error_message=error_message,
            conn=conn,
        )
    finally:
        close(conn)
