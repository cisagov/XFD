"""Read-only workload inspection without Qualys calls or report side effects."""

# Standard Python Libraries
import argparse
import logging

# Third-Party Libraries
from psycopg2.extensions import connection

# First-Party Libraries
from was_reports.commands.batch_progress import (
    log_preflight_summary,
    summarize_candidates,
)
from was_reports.data.daily_report_tracker import list_ready_report_candidates
from was_reports.utils.database import close, connect

LOGGER = logging.getLogger(__name__)


def parse_window(value: str) -> int | None:
    """Accept a positive calendar-date count or explicit unlimited history."""
    if value.strip().lower() == "all":
        return None
    try:
        days_back = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a positive integer or all.") from error
    if days_back < 1:
        raise argparse.ArgumentTypeError("Use a positive integer or all.")
    return days_back


def inspect_exclusions(
    conn: connection, days_back: int | None, tag: str | None
) -> list[tuple[str, int]]:
    """Count mutually exclusive reasons across the stored tracker snapshot.

    Reasons use the same newest-live-row, scan-date, and delivery rules as
    automated generation. Legacy overlaps hold otherwise eligible candidates
    for reconciliation. Diagnostics separate modern schedule executions from
    historical rows without an execution key; they are not extra exclusions.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            """
            WITH scoped AS (
                SELECT tracker.*,
                    COALESCE(scan_execution_key, '') LIKE 'legacy-import:%%'
                        AS imported,
                    CASE
                        WHEN scan_execution_key LIKE 'schedule:%%'
                            THEN 'schedule execution'
                        WHEN scan_execution_key IS NULL THEN 'NULL historical key'
                        WHEN scan_execution_key LIKE 'legacy-import:%%'
                            THEN 'imported'
                        ELSE 'other key'
                    END AS origin
                FROM was_daily_report_tracker tracker
                WHERE (%s::text IS NULL OR tracker.tag = %s)
            ), ranked AS (
                SELECT scoped.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY tag, imported
                        ORDER BY scan_start_date DESC NULLS LAST,
                            data_pull_date DESC NULLS LAST, id DESC
                    ) AS candidate_rank
                FROM scoped
            ), classified AS (
                SELECT tracker.*,
                    CASE
                        WHEN imported THEN 'legacy imported row'
                        WHEN tracker.tag IS NULL OR BTRIM(tracker.tag) = ''
                            THEN 'missing tag'
                        WHEN %s::integer IS NOT NULL AND (
                            scan_start_date IS NULL OR
                            scan_start_date < CURRENT_DATE - (%s::integer - 1)
                        ) THEN 'outside scan-date window or missing scan date'
                        WHEN candidate_rank > 1 THEN 'older execution for tag'
                        WHEN stakeholders.tag IS NULL THEN 'missing stakeholder'
                        WHEN tracker.report_sent_date IS NOT NULL THEN 'already sent'
                        WHEN tracker.template = 'Deactivated' THEN 'deactivated'
                        WHEN stakeholders.retired IS TRUE THEN 'retired stakeholder'
                        WHEN EXISTS (
                            SELECT 1 FROM was_report_runs runs
                            WHERE runs.source_tracker_id = tracker.id
                        ) THEN 'existing report run'
                        WHEN NOT (
                            LOWER(BTRIM(COALESCE(tracker.status, ''))) = 'finished'
                            OR (
                                LOWER(BTRIM(COALESCE(tracker.status, ''))) = 'error'
                                AND BTRIM(COALESCE(tracker.qualys_error, '')) <> ''
                            )
                        ) THEN 'status not eligible'
                        WHEN BTRIM(COALESCE(tracker.report_scan_notes, '')) <> ''
                            THEN 'manual report notes'
                        WHEN stakeholders.manual_report IS TRUE
                            THEN 'manual stakeholder'
                        WHEN EXISTS (
                            SELECT 1 FROM was_daily_report_tracker legacy
                            WHERE legacy.id <> tracker.id
                                AND legacy.schedule_id = tracker.schedule_id
                                AND legacy.scan_start_date = tracker.scan_start_date
                                AND (
                                    legacy.scan_execution_key IS NULL
                                    OR legacy.scan_execution_key LIKE 'legacy-import:%%'
                                )
                        ) THEN 'held: otherwise eligible legacy schedule/date overlap'
                        WHEN EXISTS (
                            SELECT 1 FROM was_daily_report_tracker sibling
                            WHERE sibling.id <> tracker.id
                                AND sibling.schedule_id = tracker.schedule_id
                                AND sibling.scan_start_date = tracker.scan_start_date
                                AND BTRIM(COALESCE(tracker.scan_name, '')) <> ''
                                AND sibling.scan_name = tracker.scan_name
                                AND (
                                    sibling.report_sent_date IS NOT NULL
                                    OR EXISTS (
                                        SELECT 1 FROM was_report_runs sibling_run
                                        WHERE sibling_run.source_tracker_id = sibling.id
                                    )
                                )
                        ) THEN 'held: same scan run already claimed or sent'
                        ELSE 'eligible'
                    END AS reason
                FROM ranked tracker
                LEFT JOIN was_stakeholders stakeholders
                    ON stakeholders.tag = tracker.tag
            )
            SELECT reason, COUNT(*) FROM classified GROUP BY reason
            UNION ALL
            SELECT 'diagnostic: otherwise eligible legacy overlap: ' || origin,
                COUNT(*) FROM classified
            WHERE reason = 'held: otherwise eligible legacy schedule/date overlap'
            GROUP BY origin
            UNION ALL
            SELECT 'diagnostic: held overlap with already-sent legacy row', COUNT(*)
            FROM classified tracker
            WHERE reason = 'held: otherwise eligible legacy schedule/date overlap'
                AND EXISTS (
                    SELECT 1 FROM was_daily_report_tracker legacy
                    WHERE legacy.id <> tracker.id
                        AND legacy.schedule_id = tracker.schedule_id
                        AND legacy.scan_start_date = tracker.scan_start_date
                        AND legacy.report_sent_date IS NOT NULL
                        AND (
                            legacy.scan_execution_key IS NULL
                            OR legacy.scan_execution_key LIKE 'legacy-import:%%'
                        )
                )
            UNION ALL
            SELECT 'diagnostic: eligible: ' || origin, COUNT(*) FROM classified
            WHERE reason = 'eligible' GROUP BY origin
            UNION ALL
            SELECT 'diagnostic: stored rows: ' || origin, COUNT(*) FROM classified
            GROUP BY origin
            UNION ALL
            SELECT 'diagnostic: old scans pulled inside window: ' || origin, COUNT(*)
            FROM classified
            WHERE NOT imported AND %s::integer IS NOT NULL
                AND data_pull_date >= CURRENT_DATE - (%s::integer - 1)
                AND scan_start_date < CURRENT_DATE - (%s::integer - 1)
            GROUP BY origin
            ORDER BY 1
            """,
            (tag, tag, days_back, days_back, days_back, days_back, days_back),
        )
        return cursor.fetchall()


def main(argv: list[str] | None = None) -> int:
    """Display a consistent, database-enforced read-only batch snapshot."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-back", type=parse_window, default=7)
    parser.add_argument("--tag")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    conn = connect()
    try:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        candidates = list_ready_report_candidates(
            conn, stakeholder_tag=args.tag, days_back=args.days_back
        )
        log_preflight_summary(LOGGER, summarize_candidates(candidates), args.days_back)
        LOGGER.info("Window uses scan_start_date, including today (database date).")
        for reason, count in inspect_exclusions(conn, args.days_back, args.tag):
            LOGGER.info("%s: %d", reason, count)
        LOGGER.info("Snapshot only: no refresh, recovery, report generation or delivery.")
    finally:
        close(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
