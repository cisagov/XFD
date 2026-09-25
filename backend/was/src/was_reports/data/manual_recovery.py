"""Guarded recovery of report runs blocked by resolved historical failures."""

# Standard Python Libraries
from dataclasses import dataclass
from uuid import uuid4

# Third-Party Libraries
from psycopg2.extensions import connection

# First-Party Libraries
from was_reports.data.report_runs import EMAIL_PENDING, RUNNING, ReportRun
from was_reports.utils.passwords import (
    ExistingReportPasswordError,
    validate_existing_report_password,
)

PASSWORD_VALIDATION = "password-validation"
QUALYS_READ_TIMEOUT = "qualys-read-timeout"
RECOVERY_CAUSES = frozenset({PASSWORD_VALIDATION, QUALYS_READ_TIMEOUT})
FAILURE_NOTES = {
    PASSWORD_VALIDATION: frozenset(
        {
            "MANUAL: Report generation failed: ValueError occurred during report generation.",
            "MANUAL: Report generation failed: ExistingReportPasswordError occurred during report generation.",
        }
    ),
    QUALYS_READ_TIMEOUT: frozenset(
        {
            "MANUAL: Report generation failed: ReadTimeout occurred during report generation.",
            "MANUAL: Report generation failed: QualysReadTimeout occurred during report generation.",
        }
    ),
}


@dataclass(frozen=True)
class ManualRecoveryCheck:
    """Eligibility result for one explicitly selected tracker row."""

    tracker_id: int
    cause: str
    tag: str | None
    report_run_id: int | None
    eligible: bool
    reason: str


def _fetch_recovery_state(
    conn: connection,
    tracker_id: int,
    days_back: int,
    *,
    lock: bool,
) -> tuple[object, ...] | None:
    """Return all guarded recovery state, optionally locking mutable rows."""
    lock_clause = " FOR UPDATE OF tracker, stakeholders, runs" if lock else ""
    query = """
        SELECT
            tracker.tag,
            tracker.report_scan_notes,
            tracker.report_sent_date,
            tracker.status,
            tracker.qualys_error,
            tracker.scan_execution_key,
            stakeholders.report_password,
            stakeholders.retired,
            stakeholders.manual_report,
            runs.id,
            runs.status,
            runs.email_status,
            runs.emailed_at,
            runs.error_message,
            runs.delivery_purpose,
            tracker.scan_start_date >= CURRENT_DATE - (%s - 1),
            NOT EXISTS (
                SELECT 1
                FROM was_daily_report_tracker AS newer
                WHERE newer.tag = tracker.tag
                  AND COALESCE(newer.scan_execution_key, '') NOT LIKE 'legacy-import:%%'
                  AND (
                        COALESCE(newer.scan_start_date, '-infinity'::date),
                        COALESCE(newer.data_pull_date, '-infinity'::date),
                        newer.id
                  ) > (
                        COALESCE(tracker.scan_start_date, '-infinity'::date),
                        COALESCE(tracker.data_pull_date, '-infinity'::date),
                        tracker.id
                  )
            ),
            NOT EXISTS (
                SELECT 1
                FROM was_daily_report_tracker AS legacy
                WHERE legacy.id <> tracker.id
                  AND legacy.schedule_id = tracker.schedule_id
                  AND legacy.scan_start_date = tracker.scan_start_date
                  AND (
                        legacy.scan_execution_key IS NULL
                     OR legacy.scan_execution_key LIKE 'legacy-import:%%'
                  )
            ),
            NOT EXISTS (
                SELECT 1
                FROM was_daily_report_tracker AS sibling
                WHERE sibling.id <> tracker.id
                  AND sibling.schedule_id = tracker.schedule_id
                  AND sibling.scan_start_date = tracker.scan_start_date
                  AND BTRIM(COALESCE(tracker.scan_name, '')) <> ''
                  AND sibling.scan_name = tracker.scan_name
                  AND (
                        sibling.report_sent_date IS NOT NULL
                     OR EXISTS (
                            SELECT 1
                            FROM was_report_runs AS sibling_run
                            WHERE sibling_run.source_tracker_id = sibling.id
                        )
                  )
            )
        FROM was_daily_report_tracker AS tracker
        JOIN was_stakeholders AS stakeholders ON stakeholders.tag = tracker.tag
        JOIN was_report_runs AS runs ON runs.source_tracker_id = tracker.id
        WHERE tracker.id = %s
    """ + lock_clause
    with conn.cursor() as cursor:
        cursor.execute(query, (days_back, tracker_id))
        return cursor.fetchone()


def _evaluate_recovery_state(
    tracker_id: int,
    cause: str,
    state: tuple[object, ...] | None,
) -> ManualRecoveryCheck:
    """Apply the recovery policy without exposing password values."""
    if cause not in RECOVERY_CAUSES:
        raise ValueError("Recovery cause is not supported.")
    if state is None:
        return ManualRecoveryCheck(
            tracker_id, cause, None, None, False, "tracker row was not found"
        )
    tag = str(state[0])
    report_run_id = int(state[9]) if state[9] is not None else None
    checks = (
        (state[1] in FAILURE_NOTES[cause], "failure note does not match the selected cause"),
        (state[2] is None, "tracker row is already marked sent"),
        (str(state[3] or "").strip().lower() == "finished", "tracker status is not Finished"),
        (not str(state[4] or "").strip(), "tracker row has a Qualys error"),
        (
            bool(state[5]) and not str(state[5]).startswith("legacy-import:"),
            "tracker row is legacy or has no execution identity",
        ),
        (state[7] is not True, "stakeholder is retired"),
        (state[8] is not True, "stakeholder requires manual reporting"),
        (report_run_id is not None, "tracker row has no report run"),
        (state[10] == "failed", "latest customer report run is not failed"),
        (str(state[11] or "pending") in {"pending", "failed"}, "email is sent, held, or active"),
        (state[12] is None, "report run is already recorded as emailed"),
        (state[14] == "customer", "report run is not a customer delivery"),
        (bool(state[15]), "tracker row is outside the recovery window"),
        (bool(state[16]), "tracker row is not the latest execution for its tag"),
        (bool(state[17]), "a legacy overlap exists for this execution"),
        (bool(state[18]), "a sibling execution was sent or already processed"),
        (
            "QualysReportCreationUncertainError" not in str(state[13] or "")
            and "creation outcome is uncertain" not in str(state[13] or ""),
            "Qualys report creation outcome requires reconciliation",
        ),
    )
    for passed, reason in checks:
        if not passed:
            return ManualRecoveryCheck(
                tracker_id, cause, tag, report_run_id, False, reason
            )
    if cause == PASSWORD_VALIDATION:
        try:
            validate_existing_report_password(str(state[6] or ""))
        except ExistingReportPasswordError:
            return ManualRecoveryCheck(
                tracker_id,
                cause,
                tag,
                report_run_id,
                False,
                "stored report password is still invalid",
            )
    return ManualRecoveryCheck(
        tracker_id, cause, tag, report_run_id, True, "eligible"
    )


def check_manual_report_recovery(
    conn: connection,
    tracker_id: int,
    cause: str,
    days_back: int = 7,
) -> ManualRecoveryCheck:
    """Preview whether one historical failure is eligible for recovery."""
    if days_back < 1:
        raise ValueError("Days back must be at least 1.")
    return _evaluate_recovery_state(
        tracker_id,
        cause,
        _fetch_recovery_state(conn, tracker_id, days_back, lock=False),
    )


def claim_manual_report_recovery(
    conn: connection,
    tracker_id: int,
    cause: str,
    days_back: int = 7,
) -> ReportRun | None:
    """Atomically revalidate and reclaim an eligible failed customer run."""
    if days_back < 1:
        raise ValueError("Days back must be at least 1.")
    generation_token = str(uuid4())
    try:
        state = _fetch_recovery_state(conn, tracker_id, days_back, lock=True)
        check = _evaluate_recovery_state(tracker_id, cause, state)
        if not check.eligible:
            conn.rollback()
            return None
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
                WHERE id = %s
                  AND status = 'failed'
                  AND delivery_purpose = 'customer'
                  AND emailed_at IS NULL
                  AND COALESCE(email_status, 'pending') IN ('pending', 'failed')
                  AND POSITION('QualysReportCreationUncertainError'
                      IN COALESCE(error_message, '')) = 0
                  AND POSITION('creation outcome is uncertain'
                      IN COALESCE(error_message, '')) = 0
                RETURNING id, stakeholder_tag, status
                """,
                (RUNNING, generation_token, EMAIL_PENDING, check.report_run_id),
            )
            row = cursor.fetchone()
            if row is None:
                conn.rollback()
                return None
            cursor.execute(
                """
                UPDATE was_daily_report_tracker
                SET report_scan_notes = NULL,
                    updated_at = NOW()
                WHERE id = %s AND report_scan_notes = %s
                RETURNING id
                """,
                (tracker_id, state[1]),
            )
            if cursor.fetchone() is None:
                conn.rollback()
                return None
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ReportRun(
        id=int(row[0]),
        stakeholder_tag=str(row[1]),
        status=str(row[2]),
        generation_token=generation_token,
    )


def check_manual_report_recovery_by_id(
    tracker_id: int, cause: str, days_back: int = 7
) -> ManualRecoveryCheck:
    """Preview recovery using a managed database connection."""
    # First-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return check_manual_report_recovery(conn, tracker_id, cause, days_back)
    finally:
        close(conn)


def claim_manual_report_recovery_by_id(
    tracker_id: int, cause: str, days_back: int = 7
) -> ReportRun | None:
    """Claim recovery using a managed database connection."""
    # First-Party Libraries
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return claim_manual_report_recovery(conn, tracker_id, cause, days_back)
    finally:
        close(conn)
