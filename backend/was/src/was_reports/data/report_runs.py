"""Report run data access for WAS batch execution tracking."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

# Third-Party Libraries
from psycopg2 import sql
from was_reports.data.daily_report_tracker import record_tracker_digest_failure

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
DEFAULT_REPORT_RUN_STALE_SECONDS = 300
DEFAULT_EMAIL_CLAIM_STALE_SECONDS = 300
LOGGER = logging.getLogger(__name__)


class ActiveReportOperationError(RuntimeError):
    """Indicate that an active report operation already owns a stakeholder."""


@dataclass(frozen=True)
class ReportRun:
    """Database representation of one WAS report execution."""

    id: int
    stakeholder_tag: str
    status: str
    output_path: str | None = None
    artifact_type: str | None = None
    generation_token: str | None = None


@dataclass(frozen=True)
class ReportRunEmail:
    """Completed report run and stakeholder email fields."""

    id: int
    stakeholder_tag: str
    output_path: str | None
    report_password: str | None
    distro_email: str | None
    tech_poc_email: str | None
    was_report_poc: str | None
    source_tracker_id: int | None = None
    artifact_type: str | None = None
    template: str | None = None
    assignee_name: str | None = None
    recent_nws: str | None = None
    remove_nws: str | None = None
    qualys_error: str | None = None
    last_scanned: int | None = None
    next_scheduled: int | None = None
    email_claim_token: str | None = None
    delivery_purpose: str = "customer"


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


@dataclass(frozen=True)
class QualysReportPollingState:
    """Qualys report identifiers retained for restart-safe polling."""

    detail_report_id: str | None = None
    xml_report_id: str | None = None


QUALYS_REPORT_COLUMNS = {
    "detail": (
        "qualys_detail_report_id",
        "qualys_detail_report_status",
        "qualys_detail_last_polled_at",
    ),
    "xml": (
        "qualys_xml_report_id",
        "qualys_xml_report_status",
        "qualys_xml_last_polled_at",
    ),
}


def qualys_report_columns(artifact_label: str) -> tuple[str, str, str]:
    """Return approved report-state columns for one Qualys artifact label."""
    normalized_label = artifact_label.strip().lower()
    try:
        return QUALYS_REPORT_COLUMNS[normalized_label]
    except KeyError as error:
        raise ValueError("Qualys artifact label must be detail or xml.") from error


def get_qualys_report_polling_state(
    report_run_id: int,
    conn: connection,
) -> QualysReportPollingState:
    """Return persisted Qualys report identifiers for one report run."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT qualys_detail_report_id, qualys_xml_report_id
            FROM was_report_runs
            WHERE id = %s
            """,
            (report_run_id,),
        )
        row = cursor.fetchone()
    if row is None:
        raise LookupError("WAS report run {} was not found.".format(report_run_id))
    return QualysReportPollingState(
        detail_report_id=row[0],
        xml_report_id=row[1],
    )


def get_qualys_report_polling_state_by_id(
    report_run_id: int,
) -> QualysReportPollingState:
    """Return Qualys polling state using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return get_qualys_report_polling_state(report_run_id, conn)
    finally:
        close(conn)


def claim_qualys_report_creation(
    report_run_id: int,
    artifact_label: str,
    conn: connection,
    *,
    generation_token: str,
) -> bool:
    """Commit first creation intent, preserving uncertainty across retries.

    Legacy NULL status cannot prove whether a pre-upgrade create was attempted.
    Such runs require operator reconciliation before enabling retries.
    """
    id_column, status_column, _ = qualys_report_columns(artifact_label)
    query = sql.SQL(
        """
        UPDATE was_report_runs
        SET {status_column} = 'CREATE_REQUESTED', updated_at = NOW()
        WHERE id = %s AND status = %s AND generation_token = %s
          AND {status_column} IS NULL AND {id_column} IS NULL
        RETURNING id
        """
    ).format(
        status_column=sql.Identifier(status_column),
        id_column=sql.Identifier(id_column),
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (report_run_id, RUNNING, generation_token))
            claimed = cursor.fetchone() is not None
            if not claimed:
                cursor.execute(
                    """
                    SELECT id FROM was_report_runs
                    WHERE id = %s AND status = %s AND generation_token = %s
                    """,
                    (report_run_id, RUNNING, generation_token),
                )
                if cursor.fetchone() is None:
                    raise ActiveReportOperationError(
                        "WAS generation ownership was lost."
                    )
            conn.commit()
            return claimed
    except Exception:
        conn.rollback()
        raise


def claim_qualys_report_creation_by_run_id(
    report_run_id: int,
    artifact_label: str,
    *,
    generation_token: str,
) -> bool:
    """Claim creation intent using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return claim_qualys_report_creation(
            report_run_id,
            artifact_label,
            conn,
            generation_token=generation_token,
        )
    finally:
        close(conn)


def record_qualys_report_id(
    report_run_id: int,
    artifact_label: str,
    report_id: str,
    conn: connection,
    *,
    generation_token: str,
) -> None:
    """Persist one Qualys report ID before status polling begins."""
    id_column, _, polled_column = qualys_report_columns(artifact_label)
    query = sql.SQL(
        """
        UPDATE was_report_runs
        SET {id_column} = %s,
            {polled_column} = NULL,
            updated_at = NOW()
        WHERE id = %s
          AND status = %s
          AND generation_token = %s
        RETURNING id
        """
    ).format(
        id_column=sql.Identifier(id_column),
        polled_column=sql.Identifier(polled_column),
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (report_id, report_run_id, RUNNING, generation_token))
            if cursor.fetchone() is None:
                raise ActiveReportOperationError(
                    "Report run {} no longer owns the generation lease.".format(
                        report_run_id
                    )
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def record_qualys_report_id_by_run_id(
    report_run_id: int,
    artifact_label: str,
    report_id: str,
    *,
    generation_token: str,
) -> None:
    """Persist a Qualys report ID using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        record_qualys_report_id(
            report_run_id,
            artifact_label,
            report_id,
            conn,
            generation_token=generation_token,
        )
    finally:
        close(conn)


def clear_qualys_report_id(
    report_run_id: int,
    artifact_label: str,
    report_id: str,
    conn: connection,
    *,
    generation_token: str,
) -> None:
    """Clear a Qualys report ID after its temporary report is deleted."""
    id_column, status_column, polled_column = qualys_report_columns(artifact_label)
    query = sql.SQL(
        """
        UPDATE was_report_runs
        SET {id_column} = NULL,
            {status_column} = NULL,
            {polled_column} = NULL,
            updated_at = NOW()
        WHERE id = %s
          AND status = %s
          AND generation_token = %s
          AND {id_column} = %s
        RETURNING id
        """
    ).format(
        id_column=sql.Identifier(id_column),
        status_column=sql.Identifier(status_column),
        polled_column=sql.Identifier(polled_column),
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (report_run_id, RUNNING, generation_token, report_id))
            if cursor.fetchone() is None:
                raise ActiveReportOperationError(
                    "Report run {} no longer owns Qualys report {}.".format(
                        report_run_id,
                        report_id,
                    )
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def clear_qualys_report_id_by_run_id(
    report_run_id: int,
    artifact_label: str,
    report_id: str,
    *,
    generation_token: str,
) -> None:
    """Clear a Qualys report ID using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        clear_qualys_report_id(
            report_run_id,
            artifact_label,
            report_id,
            conn,
            generation_token=generation_token,
        )
    finally:
        close(conn)


def record_qualys_report_status(
    report_run_id: int,
    artifact_label: str,
    status: str,
    conn: connection,
    *,
    generation_token: str,
) -> None:
    """Persist the latest status observed while polling a Qualys report."""
    _, status_column, polled_column = qualys_report_columns(artifact_label)
    query = sql.SQL(
        """
        UPDATE was_report_runs
        SET {status_column} = %s,
            {polled_column} = NOW(),
            updated_at = NOW()
        WHERE id = %s
          AND status = %s
          AND generation_token = %s
        RETURNING id
        """
    ).format(
        status_column=sql.Identifier(status_column),
        polled_column=sql.Identifier(polled_column),
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (status, report_run_id, RUNNING, generation_token))
            if cursor.fetchone() is None:
                raise ActiveReportOperationError(
                    "Report run {} no longer owns the generation lease.".format(
                        report_run_id
                    )
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def record_qualys_report_status_by_run_id(
    report_run_id: int,
    artifact_label: str,
    status: str,
    *,
    generation_token: str,
) -> None:
    """Persist a Qualys polling status using a managed connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        record_qualys_report_status(
            report_run_id,
            artifact_label,
            status,
            conn,
            generation_token=generation_token,
        )
    finally:
        close(conn)


def _positive_seconds(name: str, default: int) -> int:
    """Return a positive timeout configured through the environment."""
    # First-Party Libraries
    # Third-Party Libraries
    from was_reports.utils.env import getenv

    raw_value = getenv(name, str(default))
    try:
        value = int(raw_value or default)
    except ValueError as error:
        raise ValueError("{} must be an integer.".format(name)) from error
    if value < 1:
        raise ValueError("{} must be at least 1.".format(name))
    return value


def recover_stale_report_operations(conn: connection) -> tuple[int, int]:
    """Fail expired generation claims and hold uncertain email claims."""
    generation_timeout = timedelta(
        seconds=_positive_seconds(
            "WAS_REPORT_RUN_STALE_SECONDS",
            DEFAULT_REPORT_RUN_STALE_SECONDS,
        )
    )
    email_timeout = timedelta(
        seconds=_positive_seconds(
            "WAS_EMAIL_CLAIM_STALE_SECONDS",
            DEFAULT_EMAIL_CLAIM_STALE_SECONDS,
        )
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                WITH stale_runs AS (
                    UPDATE was_report_runs
                    SET status = %s,
                        generation_token = NULL,
                        completed_at = NOW(),
                        error_message = %s,
                        updated_at = NOW()
                    WHERE status = %s
                      AND updated_at < NOW() - %s
                    RETURNING id, source_tracker_id, delivery_purpose
                )
                SELECT COUNT(*), ARRAY_AGG(source_tracker_id) FILTER (
                    WHERE delivery_purpose = 'customer' AND source_tracker_id IS NOT NULL
                ) FROM stale_runs
                """,
                (
                    FAILED,
                    "Report generation claim expired before completion.",
                    RUNNING,
                    generation_timeout,
                ),
            )
            generation_count, generation_tracker_ids = cursor.fetchone()
            cursor.execute(
                """
                UPDATE was_report_runs
                SET email_status = %s,
                    email_error = %s,
                    email_claim_token = NULL,
                    email_claimed_at = NULL,
                    updated_at = NOW()
                WHERE email_status = %s
                  AND email_claimed_at IS NOT NULL
                  AND email_claimed_at < NOW() - %s
                RETURNING id, source_tracker_id, delivery_purpose
                """,
                (
                    EMAIL_HELD,
                    "Email delivery claim expired; verify SES delivery before retrying.",
                    EMAIL_SENDING,
                    email_timeout,
                ),
            )
            email_rows = cursor.fetchall()
            email_count = len(email_rows)
            for tracker_id in sorted(set(generation_tracker_ids or [])):
                record_tracker_digest_failure(
                    tracker_id,
                    conn,
                    "Report generation lease expired before completion.",
                )
            email_tracker_ids = {
                row[1]
                for row in email_rows
                if row[1] is not None and row[2] == "customer"
            }
            for tracker_id in sorted(email_tracker_ids):
                record_tracker_digest_failure(
                    tracker_id,
                    conn,
                    "Email delivery lease expired; verify SES delivery before retrying.",
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if generation_count or email_count:
        LOGGER.warning(
            "Recovered stale WAS operations: generation=%s email=%s.",
            generation_count,
            email_count,
        )
    return generation_count, email_count


def recover_stale_report_operations_in_db() -> tuple[int, int]:
    """Recover stale report operations using a managed connection."""
    # First-Party Libraries
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return recover_stale_report_operations(conn)
    finally:
        close(conn)


def touch_report_run(
    report_run_id: int,
    conn: connection,
    *,
    generation_token: str,
) -> bool:
    """Refresh an active report-generation lease."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET updated_at = NOW()
                WHERE id = %s
                  AND status = %s
          AND generation_token = %s
                RETURNING id
                """,
                (report_run_id, RUNNING, generation_token),
            )
            refreshed = cursor.fetchone() is not None
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    return refreshed


def touch_report_run_by_id(
    report_run_id: int,
    *,
    generation_token: str,
) -> bool:
    """Refresh a report-generation lease using a managed connection."""
    # First-Party Libraries
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return touch_report_run(
            report_run_id=report_run_id,
            conn=conn,
            generation_token=generation_token,
        )
    finally:
        close(conn)


def touch_report_email_claim(
    report_run_id: int,
    conn: connection,
    *,
    email_claim_token: str,
) -> bool:
    """Refresh an active report-email delivery lease."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET email_claimed_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                  AND email_status = %s
                  AND email_claim_token = %s
                RETURNING id
                """,
                (report_run_id, EMAIL_SENDING, email_claim_token),
            )
            refreshed = cursor.fetchone() is not None
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    return refreshed


def touch_report_email_claim_by_id(
    report_run_id: int,
    *,
    email_claim_token: str,
) -> bool:
    """Refresh a report-email lease using a managed connection."""
    # First-Party Libraries
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return touch_report_email_claim(
            report_run_id=report_run_id,
            conn=conn,
            email_claim_token=email_claim_token,
        )
    finally:
        close(conn)


def create_report_run(
    stakeholder_tag: str,
    scheduled_epoch: int | None,
    conn: connection,
    source_tracker_id: int | None = None,
    email_status: str = EMAIL_PENDING,
    delivery_purpose: str = "customer",
) -> ReportRun | None:
    """Claim a scheduled execution and return its running report record."""
    if delivery_purpose not in {"customer", "analyst"}:
        raise ValueError("Delivery purpose must be customer or analyst.")
    generation_token = str(uuid4())
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO was_report_runs (
                    stakeholder_tag,
                    status,
                    scheduled_epoch,
                    source_tracker_id,
                    email_status,
                    generation_token,
                    delivery_purpose
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id, stakeholder_tag, status
                """,
                (
                    stakeholder_tag,
                    RUNNING,
                    scheduled_epoch,
                    source_tracker_id,
                    email_status,
                    generation_token,
                    delivery_purpose,
                ),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        return None
    return ReportRun(
        id=row[0],
        stakeholder_tag=row[1],
        status=row[2],
        generation_token=generation_token,
    )


def complete_report_run(
    report_run_id: int,
    conn: connection,
    output_path: str | None = None,
    artifact_type: str | None = None,
    *,
    generation_token: str,
) -> None:
    """Mark a report execution record as completed."""
    update_report_run_status(
        report_run_id=report_run_id,
        status=COMPLETED,
        error_message=None,
        output_path=output_path,
        artifact_type=artifact_type,
        conn=conn,
        generation_token=generation_token,
    )


def fail_report_run(
    report_run_id: int,
    error_message: str,
    conn: connection,
    *,
    generation_token: str,
) -> None:
    """Mark a report execution record as failed."""
    update_report_run_status(
        report_run_id=report_run_id,
        status=FAILED,
        error_message=error_message,
        output_path=None,
        artifact_type=None,
        conn=conn,
        generation_token=generation_token,
    )


def update_report_run_status(
    report_run_id: int,
    status: str,
    error_message: str | None,
    output_path: str | None,
    artifact_type: str | None,
    conn: connection,
    *,
    generation_token: str,
) -> None:
    """Update report execution status and completion metadata."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                WITH changed_run AS (
                    UPDATE was_report_runs
                    SET status = %s,
                        completed_at = NOW(),
                        error_message = %s,
                        output_path = COALESCE(%s, output_path),
                        artifact_type = COALESCE(%s, artifact_type),
                        updated_at = NOW()
                    WHERE id = %s
                      AND status = %s
                      AND generation_token = %s
                    RETURNING id, source_tracker_id, status, error_message,
                              delivery_purpose
                )
                SELECT id, source_tracker_id, delivery_purpose FROM changed_run
                """,
                (
                    status,
                    error_message,
                    output_path,
                    artifact_type,
                    report_run_id,
                    RUNNING,
                    generation_token,
                ),
            )
            updated_row = cursor.fetchone()
            if updated_row is None:
                raise ActiveReportOperationError(
                    "Report run {} no longer owns its generation lease.".format(
                        report_run_id
                    )
                )
            if (
                status == FAILED
                and updated_row[1] is not None
                and updated_row[2] == "customer"
            ):
                record_tracker_digest_failure(
                    updated_row[1],
                    conn,
                    "Report generation failed: {}".format(error_message),
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
        recover_stale_report_operations(conn)
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
            active_run = cursor.fetchone()
            if active_run is not None:
                raise ActiveReportOperationError(
                    "Report run {} is already active for stakeholder {}.".format(
                        active_run[0], stakeholder_tag
                    )
                )
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
            delivery_purpose="analyst",
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
    generation_token = str(uuid4())
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_report_runs
                SET status = %s,
                    generation_token = %s,
                    email_claim_token = NULL,
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
                  AND delivery_purpose = 'customer'
                RETURNING id, stakeholder_tag, status
                """,
                (
                    RUNNING,
                    generation_token,
                    EMAIL_PENDING,
                    source_tracker_id,
                    FAILED,
                ),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        return None
    return ReportRun(
        id=row[0],
        stakeholder_tag=row[1],
        status=row[2],
        generation_token=generation_token,
    )


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
    *,
    generation_token: str,
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
            generation_token=generation_token,
        )
    finally:
        close(conn)


def fail_report_run_by_id(
    report_run_id: int,
    error_message: str,
    *,
    generation_token: str,
) -> None:
    """Fail a report execution record using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        fail_report_run(
            report_run_id=report_run_id,
            error_message=error_message,
            conn=conn,
            generation_token=generation_token,
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
                runs.source_tracker_id,
                runs.artifact_type,
                tracker.template,
                COALESCE(assignees.name, tracker.assignee),
                tracker.recent_nws,
                tracker.remove_nws,
                tracker.qualys_error,
                stakeholders.last_scanned,
                stakeholders.next_scheduled,
                runs.email_claim_token,
                runs.delivery_purpose
            FROM was_report_runs AS runs
            JOIN was_stakeholders AS stakeholders
              ON stakeholders.tag = runs.stakeholder_tag
            LEFT JOIN was_daily_report_tracker AS tracker
              ON tracker.id = runs.source_tracker_id
            LEFT JOIN was_assignees AS assignees
              ON assignees.id = tracker.assignee_id
            WHERE runs.id = %s
              AND runs.status = %s
              AND (
                    runs.output_path IS NOT NULL
                 OR runs.artifact_type = 'notification'
              )
              AND runs.emailed_at IS NULL
            """,
            (report_run_id, COMPLETED),
        )
        row = cursor.fetchone()

    if row is None:
        raise KeyError(
            "Completed report run {} with a deliverable was not found.".format(
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
        artifact_type=row[8],
        template=row[9],
        assignee_name=row[10],
        recent_nws=row[11],
        remove_nws=row[12],
        qualys_error=row[13],
        last_scanned=row[14],
        next_scheduled=row[15],
        email_claim_token=row[16],
        delivery_purpose=row[17],
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
            runs.source_tracker_id,
            runs.artifact_type,
            tracker.template,
            COALESCE(assignees.name, tracker.assignee),
            tracker.recent_nws,
            tracker.remove_nws,
            tracker.qualys_error,
            stakeholders.last_scanned,
            stakeholders.next_scheduled,
                runs.email_claim_token,
                runs.delivery_purpose
        FROM was_report_runs AS runs
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = runs.stakeholder_tag
        LEFT JOIN was_daily_report_tracker AS tracker
          ON tracker.id = runs.source_tracker_id
        LEFT JOIN was_assignees AS assignees
          ON assignees.id = tracker.assignee_id
        WHERE runs.status = %s
          AND (
                runs.output_path IS NOT NULL
             OR runs.artifact_type = 'notification'
          )
          AND runs.emailed_at IS NULL
          AND COALESCE(runs.email_status, %s) = ANY(%s)
          AND runs.delivery_purpose = 'customer'
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
                artifact_type=row[8],
                template=row[9],
                assignee_name=row[10],
                recent_nws=row[11],
                remove_nws=row[12],
                qualys_error=row[13],
                last_scanned=row[14],
                next_scheduled=row[15],
                email_claim_token=row[16],
                delivery_purpose=row[17],
            )
        )

    return report_runs


def claim_report_run_email(
    report_run_id: int,
    conn: connection,
    include_previous_failure: bool = False,
    allow_held: bool = False,
    delivery_purpose: str = "customer",
) -> ReportRunEmail | None:
    """Atomically claim one completed report run for email delivery."""
    if delivery_purpose not in {"customer", "analyst"}:
        raise ValueError("Delivery purpose must be customer or analyst.")
    email_claim_token = str(uuid4())
    allowed_email_statuses = [EMAIL_PENDING]
    if allow_held:
        allowed_email_statuses.append(EMAIL_HELD)
    if include_previous_failure:
        allowed_email_statuses.append(EMAIL_FAILED)
    query = """
        WITH claimed AS (
            UPDATE was_report_runs
            SET email_status = %s,
                email_claim_token = %s,
                email_claimed_at = NOW(),
                email_error = NULL,
                updated_at = NOW()
            WHERE id = %s
              AND status = %s
              AND (
                    output_path IS NOT NULL
                 OR artifact_type = 'notification'
              )
              AND emailed_at IS NULL
              AND COALESCE(email_status, %s) = ANY(%s)
              AND delivery_purpose = %s
            RETURNING id, stakeholder_tag, output_path, source_tracker_id,
                      artifact_type, email_claim_token, delivery_purpose
        )
        SELECT
            claimed.id,
            claimed.stakeholder_tag,
            claimed.output_path,
            claimed.source_tracker_id,
            claimed.artifact_type,
            stakeholders.report_password,
            stakeholders.distro_email,
            stakeholders.tech_poc_email,
            stakeholders.was_report_poc,
            tracker.template,
            COALESCE(assignees.name, tracker.assignee),
            tracker.recent_nws,
            tracker.remove_nws,
            tracker.qualys_error,
            stakeholders.last_scanned,
            stakeholders.next_scheduled,
            claimed.email_claim_token,
            claimed.delivery_purpose
        FROM claimed
        JOIN was_stakeholders AS stakeholders
          ON stakeholders.tag = claimed.stakeholder_tag
        LEFT JOIN was_daily_report_tracker AS tracker
          ON tracker.id = claimed.source_tracker_id
        LEFT JOIN was_assignees AS assignees
          ON assignees.id = tracker.assignee_id
    """
    parameters: list[object] = [
        EMAIL_SENDING,
        email_claim_token,
        report_run_id,
        COMPLETED,
        EMAIL_PENDING,
        allowed_email_statuses,
        delivery_purpose,
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
        artifact_type=row[4],
        report_password=row[5],
        distro_email=row[6],
        tech_poc_email=row[7],
        was_report_poc=row[8],
        template=row[9],
        assignee_name=row[10],
        recent_nws=row[11],
        remove_nws=row[12],
        qualys_error=row[13],
        last_scanned=row[14],
        next_scheduled=row[15],
        email_claim_token=row[16],
        delivery_purpose=row[17],
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
    delivery_purpose: str = "customer",
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
            delivery_purpose=delivery_purpose,
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
    *,
    email_claim_token: str,
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
                      AND email_claim_token = %s
                    RETURNING id, source_tracker_id, delivery_purpose
                ),
                updated_tracker AS (
                    UPDATE was_daily_report_tracker AS tracker
                    SET report_sent_date = CURRENT_DATE,
                        updated_at = NOW()
                    FROM emailed_run
                    WHERE tracker.id = emailed_run.source_tracker_id
                      AND emailed_run.delivery_purpose = 'customer'
                    RETURNING tracker.id
                )
                SELECT id FROM emailed_run
                """,
                (
                    message_id,
                    EMAIL_SENT,
                    report_run_id,
                    EMAIL_SENDING,
                    email_claim_token,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise ActiveReportOperationError(
                    "WAS report email claim was not active."
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_report_run_email_failed(
    report_run_id: int,
    error_message: str,
    conn: connection,
    hold_for_manual_retry: bool = False,
    *,
    email_claim_token: str,
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
                  AND email_claim_token = %s
                RETURNING id, source_tracker_id, delivery_purpose
                """,
                (
                    error_message,
                    EMAIL_HELD if hold_for_manual_retry else EMAIL_FAILED,
                    report_run_id,
                    EMAIL_SENDING,
                    email_claim_token,
                ),
            )
            row = cursor.fetchone()
            if row is None:
                raise ActiveReportOperationError(
                    "WAS report email claim was not active."
                )
            if row[1] is not None and row[2] == "customer":
                record_tracker_digest_failure(
                    row[1],
                    conn,
                    "Email delivery failed: {}".format(error_message),
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def mark_report_run_emailed_by_id(
    report_run_id: int,
    message_id: str,
    *,
    email_claim_token: str,
) -> None:
    """Mark a report run emailed using a managed database connection."""
    # Third-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        mark_report_run_emailed(
            report_run_id=report_run_id,
            message_id=message_id,
            conn=conn,
            email_claim_token=email_claim_token,
        )
    finally:
        close(conn)


def mark_report_run_email_failed_by_id(
    report_run_id: int,
    error_message: str,
    hold_for_manual_retry: bool = False,
    *,
    email_claim_token: str,
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
            email_claim_token=email_claim_token,
            hold_for_manual_retry=hold_for_manual_retry,
        )
    finally:
        close(conn)
