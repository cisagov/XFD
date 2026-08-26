"""Report run data access for WAS batch execution tracking."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

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
