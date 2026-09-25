"""Durable, combined analyst notifications for a multi-process WAS batch."""

import argparse
from collections import Counter
import csv
from email.message import EmailMessage
from html.parser import HTMLParser
import io
import json
import logging
import math
import statistics

from was_mailer.message import approved_analyst_recipients
from was_mailer.ses_client import create_ses_client
from was_reports.data.assignees import (
    list_functional_test_recipient_emails_from_db,
)
from was_reports.data.daily_report_tracker import (
    DELIVERY_RECONCILIATION,
    MANUAL_WORK,
    list_ready_report_candidates_from_db,
    manual_work_classification,
)
from was_reports.data.manual_recovery import (
    FAILURE_NOTES,
    PASSWORD_VALIDATION,
    QUALYS_READ_TIMEOUT,
)
from was_reports.reporting.report_transformer import spreadsheet_safe_field
from was_reports.utils.database import connect
from was_reports.utils.capacity_telemetry import emit_metric
from was_reports.utils.capacity_scope import capacity_tracker_ids
from was_reports.utils.env import getenv

LOGGER = logging.getLogger(__name__)


def _execute(query, parameters=(), fetch=False):
    """Execute one committed database operation with managed ownership."""
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            rows = cursor.fetchall() if fetch else []
        connection.commit()
        return rows
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _safe_error(error):
    """Keep only a class-like code, never external payloads or credentials."""
    if error is None:
        return None
    if isinstance(error, BaseException):
        return type(error).__name__
    value = str(error)
    if (
        value
        and len(value) <= 80
        and all(character.isalnum() or character == "_" for character in value)
    ):
        return value
    return "OperationError"


def _duration(value):
    """Validate measured monotonic durations before persistence."""
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Duration must be finite and nonnegative.")
    return result


def start_batch(batch_id, worker_count=None, run_mode=None, workload_label=None):
    """Create the shared batch context once without resetting phase claims."""
    if not batch_id or len(batch_id) > 200:
        raise ValueError("A batch ID of at most 200 characters is required.")
    worker_count = int(worker_count if worker_count is not None else getenv("WAS_REPORT_WORKERS", "1"))
    run_mode = run_mode or getenv("WAS_RUN_MODE", "production")
    workload_label = workload_label if workload_label is not None else getenv("WAS_WORKLOAD_LABEL")
    if worker_count < 1 or run_mode not in {"production", "capacity"}:
        raise ValueError("Positive worker count and production/capacity run mode required.")
    if workload_label is not None and len(workload_label) > 200:
        raise ValueError("Workload label must be at most 200 characters.")
    _execute(
        "INSERT INTO was_batch_runs (batch_id, worker_count, run_mode, workload_label) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT (batch_id) DO NOTHING",
        (batch_id, worker_count, run_mode, workload_label),
    )


def finish_batch(batch_id, outcome="completed"):
    """Freeze coordinator completion once, independently of summary delivery."""
    if outcome not in {"completed", "failed"}:
        raise ValueError("Batch outcome must be completed or failed.")
    _execute(
        "UPDATE was_batch_runs SET finished_at=now(), outcome=%s, updated_at=now() "
        "WHERE batch_id=%s AND finished_at IS NULL",
        (outcome, batch_id),
    )


def record_tracker_result(batch_id, duration_seconds, error=None, rows_updated=None):
    """Persist tracker phase timing and a secret-safe failure code."""
    _execute(
        "UPDATE was_batch_runs SET tracker_duration_seconds=%s, "
        "tracker_error=%s, tracker_rows_updated=%s, updated_at=now() "
        "WHERE batch_id=%s",
        (_duration(duration_seconds), _safe_error(error), rows_updated, batch_id),
    )


def record_report_attempt(
    batch_id,
    tracker_id,
    duration_seconds,
    generated=False,
    sent=False,
    error=None,
    report_run_id=None,
    delivery_duration_seconds=None,
    artifact_type=None,
):
    """Persist one tracker outcome, idempotently replacing repeated recording."""
    if artifact_type not in {None, "pdf", "notification"}:
        raise ValueError("Artifact type must be pdf or notification.")
    delivery_duration = (
        None if delivery_duration_seconds is None else _duration(delivery_duration_seconds)
    )
    _execute(
        """INSERT INTO was_batch_report_attempts
        (batch_id, tracker_id, duration_seconds, generated, sent, error,
         report_run_id, delivery_duration_seconds, artifact_type, sent_recorded_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,CASE WHEN %s THEN now() ELSE NULL END)
        ON CONFLICT (batch_id, tracker_id) DO UPDATE SET
        duration_seconds=GREATEST(was_batch_report_attempts.duration_seconds,
                                 EXCLUDED.duration_seconds),
        generated=was_batch_report_attempts.generated OR EXCLUDED.generated,
        sent=was_batch_report_attempts.sent OR EXCLUDED.sent,
        error=COALESCE(was_batch_report_attempts.error, EXCLUDED.error),
        report_run_id=COALESCE(EXCLUDED.report_run_id,
                              was_batch_report_attempts.report_run_id),
        delivery_duration_seconds=GREATEST(was_batch_report_attempts.delivery_duration_seconds,
                                          EXCLUDED.delivery_duration_seconds),
        artifact_type=COALESCE(EXCLUDED.artifact_type,was_batch_report_attempts.artifact_type),
        sent_recorded_at=COALESCE(was_batch_report_attempts.sent_recorded_at,
                                 EXCLUDED.sent_recorded_at)""",
        (
            batch_id,
            tracker_id,
            _duration(duration_seconds),
            bool(generated),
            bool(sent),
            _safe_error(error),
            report_run_id,
            delivery_duration,
            artifact_type,
            bool(sent),
        ),
    )
    emit_metric(
        "report_attempt",
        tracker_id=tracker_id,
        report_run_id=report_run_id,
        generation_duration_seconds=_duration(duration_seconds),
        delivery_duration_seconds=delivery_duration,
        generated=bool(generated),
        sent=bool(sent),
        artifact_type=artifact_type,
        error=_safe_error(error),
    )


class _ListCounter(HTMLParser):
    """Count explicit HTML target entries without interpreting remote content."""

    def __init__(self):
        """Initialize HTML entry counters."""
        super().__init__()
        self.entries = 0
        self.breaks = 0
        self.text = []

    def handle_starttag(self, tag, attributes):
        """Count list items and legacy break-separated entries."""
        self.entries += tag == "li"
        self.breaks += tag == "br"

    def handle_data(self, data):
        """Collect plain text solely to distinguish empty markup."""
        self.text.append(data)


def target_count(value):
    """Count explicit target lists; opaque nonempty text is unknown, not zero."""
    if not value or not str(value).strip():
        return 0
    parser = _ListCounter()
    parser.feed(str(value))
    if parser.entries:
        return parser.entries
    if parser.breaks:
        # Empty leading/trailing HTML breaks are not web applications.
        normalized = str(value).replace("<br/>", "<br>").replace("<br />", "<br>")
        return sum(bool(part.strip()) for part in normalized.split("<br>"))
    return None if "".join(parser.text).strip() else 0


def preflight_counts(rows):
    """Summarize report and target counts without treating unknown data as zero."""
    counts = {
        "reports": len(rows),
        "nws_reports": 0,
        "nws_webapps": 0,
        "nws_unknown": 0,
        "error_reports": 0,
        "error_webapps": 0,
        "error_unknown": 0,
    }
    for row in rows:
        nws = str(row.get("nws") or "").split(",")
        has_nws = (
            row.get("template")
            in {
                "All NWS",
                "FCEB All NWS",
                "Action Required",
                "FCEB Action Required",
                "Targets Removed",
                "Deactivated",
            }
            or len(nws) == 3
        )
        if has_nws:
            counts["nws_reports"] += 1
            if len(nws) == 3 and all(part.strip().isdigit() for part in nws):
                counts["nws_webapps"] += int(nws[1]) + int(nws[2])
            else:
                counts["nws_unknown"] += 1
        if str(row.get("qualys_error") or "").strip():
            counts["error_reports"] += 1
            errors = target_count(row["qualys_error"])
            counts["error_unknown"] += errors is None
            counts["error_webapps"] += errors or 0
    return counts


TRACKER_EXPORT_FIELDS = (
    "id",
    "tag",
    "schedule_id",
    "data_pull_date",
    "next_scan_date",
    "poc",
    "poc_email",
    "customer_notes",
    "scan_start_date",
    "scan_started_at",
    "scan_ended_at",
    "scan_name",
    "assignee",
    "status",
    "result",
    "template",
    "report_sent_date",
    "report_scan_notes",
    "nws",
    "recent_nws",
    "remove_nws",
    "qualys_error",
)

EXPORT_FIELDS = TRACKER_EXPORT_FIELDS + (
    "current_batch_attempt",
    "open_manual",
    "delivery_reconciliation",
)

MANUAL_REASON_LABELS = (
    "Password validation failure",
    "Qualys read timeout",
    "Qualys scan error",
    "Stakeholder configured for manual reporting",
    "Legacy imported manual marker",
    "Other or unclassified",
)


def summary_csv(rows):
    """Export an explicit password-free allowlist with formula-safe cells."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(EXPORT_FIELDS)
    seen = set()
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        writer.writerow(
            [
                spreadsheet_safe_field("" if row.get(field) is None else row[field])
                for field in EXPORT_FIELDS
            ]
        )
    return output.getvalue()


def _tracker_rows(candidate_ids=None, batch_id=None, days_back=7):
    """Read batch rows plus recent manual and delivery-reconciliation work."""
    if days_back is not None and days_back < 1:
        raise ValueError("Days back must be at least 1.")
    manual_candidate = """(tracker.report_sent_date IS NULL AND
        (stakeholders.manual_report IS TRUE
         OR NULLIF(BTRIM(tracker.report_scan_notes),'') IS NOT NULL
         OR NULLIF(BTRIM(tracker.qualys_error),'') IS NOT NULL
         OR UPPER(BTRIM(COALESCE(tracker.status,'')))='ERROR'))"""
    fields = [
        "COALESCE(assignees.name, tracker.assignee, 'Unassigned')"
        if field == "assignee"
        else "tracker." + field
        for field in TRACKER_EXPORT_FIELDS
    ]
    condition = "tracker.id = ANY(%s)"
    current_batch_expression = "FALSE"
    parameters = [list(candidate_ids or [])]
    if batch_id is not None:
        current_batch_expression = (
            "EXISTS(SELECT 1 FROM was_batch_report_attempts current_attempt "
            "WHERE current_attempt.batch_id=%s "
            "AND current_attempt.tracker_id=tracker.id)"
        )
        recent_manual = manual_candidate
        parameters = [batch_id, batch_id]
        if days_back is not None:
            recent_manual = """({} AND COALESCE(tracker.scan_start_date,
                tracker.data_pull_date) >= CURRENT_DATE - (%s - 1)
                AND NOT EXISTS (
                    SELECT 1 FROM was_daily_report_tracker newer
                    WHERE newer.tag = tracker.tag
                      AND COALESCE(newer.scan_execution_key, '')
                          NOT LIKE 'legacy-import:%%'
                      AND ROW(
                          COALESCE(newer.scan_start_date, DATE '0001-01-01'),
                          COALESCE(newer.data_pull_date, DATE '0001-01-01'),
                          newer.id
                      ) > ROW(
                          COALESCE(tracker.scan_start_date, DATE '0001-01-01'),
                          COALESCE(tracker.data_pull_date, DATE '0001-01-01'),
                          tracker.id
                      )
                ))""".format(
                manual_candidate
            )
            parameters.append(days_back)
        condition = """(tracker.id IN (SELECT tracker_id
            FROM was_batch_report_attempts WHERE batch_id=%s) OR {})""".format(
            recent_manual
        )
    query = """SELECT {}, stakeholders.manual_report, {}
        FROM was_daily_report_tracker tracker
        LEFT JOIN was_stakeholders stakeholders ON stakeholders.tag=tracker.tag
        LEFT JOIN was_assignees assignees ON assignees.id=tracker.assignee_id
        WHERE {} ORDER BY LOWER(COALESCE(assignees.name, tracker.assignee,
        'Unassigned')), tracker.id""".format(
        ",".join(fields), current_batch_expression, condition
    )
    results = []
    for values in _execute(query, tuple(parameters), True):
        row = dict(zip(TRACKER_EXPORT_FIELDS, values))
        stakeholder_manual = bool(values[-2])
        classification = manual_work_classification(
            report_sent_date=row.get("report_sent_date"),
            report_scan_notes=row.get("report_scan_notes"),
            qualys_error=row.get("qualys_error"),
            status=row.get("status"),
            stakeholder_manual=stakeholder_manual,
        )
        row["stakeholder_manual"] = stakeholder_manual
        row["current_batch_attempt"] = bool(values[-1])
        row["open_manual"] = classification == MANUAL_WORK
        row["delivery_reconciliation"] = classification == DELIVERY_RECONCILIATION
        results.append(row)
    return results


def manual_reason_category(row):
    """Assign one stable primary category to an open manual tracker row."""
    note = str(row.get("report_scan_notes") or "").strip()
    if note in FAILURE_NOTES[PASSWORD_VALIDATION]:
        return "Password validation failure"
    if note in FAILURE_NOTES[QUALYS_READ_TIMEOUT]:
        return "Qualys read timeout"
    if (
        str(row.get("qualys_error") or "").strip()
        or str(row.get("status") or "").strip().upper() == "ERROR"
    ):
        return "Qualys scan error"
    if row.get("stakeholder_manual"):
        return "Stakeholder configured for manual reporting"
    if (
        str(row.get("scan_execution_key") or "").startswith("legacy-import:")
        or note.upper().startswith("LEGACY REPORT SENT DATE VALUE:")
    ):
        return "Legacy imported manual marker"
    return "Other or unclassified"


def manual_work_summary_lines(rows):
    """Return compact manual-work totals while row details remain in the CSV."""
    manuals = [row for row in rows if row.get("open_manual")]
    categories = Counter(manual_reason_category(row) for row in manuals)
    current_batch = sum(bool(row.get("current_batch_attempt")) for row in manuals)
    reconciliation_count = sum(
        bool(row.get("delivery_reconciliation")) for row in rows
    )
    lines = [
        "Open manual work: {} total".format(len(manuals)),
        "",
        "Current batch failures: {}".format(current_batch),
        "Existing manual backlog: {}".format(len(manuals) - current_batch),
        "",
        "Primary reason:",
    ]
    lines.extend(
        "- {}: {}".format(label, categories[label])
        for label in MANUAL_REASON_LABELS
    )
    lines.extend(
        (
            "",
            "Delivery reconciliation needed: {}".format(reconciliation_count),
            "",
            "See the attached tracker CSV for tags, tracker IDs, assignees, "
            "scan names, and complete notes.",
        )
    )
    return lines


def _recipients(override_recipients):
    """Resolve one enabled analyst-only recipient set, including inactive users."""
    configured = override_recipients
    if configured is None:
        configured = list_functional_test_recipient_emails_from_db()
        if not configured:
            return []
    if not isinstance(configured, str):
        configured = ";".join(configured)
    recipients = approved_analyst_recipients(configured)
    if len(recipients) > 50:
        raise ValueError("SES supports 50 recipients; configure a distribution list.")
    return recipients


def _deliver(batch_id, phase, source_email, override_recipients, body, rows, dry_run):
    """Claim once before SES; hold uncertain delivery permanently for review."""
    recipients = _recipients(override_recipients)
    if not recipients:
        LOGGER.info("No email-enabled analysts; skipping %s summary for batch %s.", phase, batch_id)
        return False
    message = EmailMessage()
    message["From"] = source_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = "WAS {} summary".format(phase)
    message.set_content(body)
    if phase == "final":
        message.add_attachment(
            summary_csv(rows).encode("utf-8"),
            maintype="text",
            subtype="csv",
            filename="WAS_batch_tracker.csv",
        )
    if dry_run:
        return True
    prefix = "tracker" if phase == "tracker" else "final"
    claimed = _execute(
        "UPDATE was_batch_runs SET {0}_summary_status='sending', updated_at=now() "
        "WHERE batch_id=%s AND {0}_summary_status='pending' RETURNING batch_id".format(
            prefix
        ),
        (batch_id,),
        True,
    )
    if not claimed:
        return False
    try:
        # Lazy import avoids cycles with the compatibility mailer entry point.
        from was_mailer.email_reports import send_message

        message_id = send_message(create_ses_client(), message)
        _execute(
            "UPDATE was_batch_runs SET {0}_summary_status='sent', "
            "{0}_summary_message_id=%s, updated_at=now() WHERE batch_id=%s".format(
                prefix
            ),
            (message_id, batch_id),
        )
    except Exception as error:
        _execute(
            "UPDATE was_batch_runs SET {0}_summary_status='held', updated_at=now() "
            "WHERE batch_id=%s".format(prefix),
            (batch_id,),
        )
        raise RuntimeError(
            "Analyst summary held for review: {}".format(_safe_error(error))
        ) from None
    return True


def send_tracker_summary(
    batch_id, candidate_ids, source_email, override_recipients=None, dry_run=False
):
    """Notify analysts once with the exact selected preflight candidate counts."""
    rows = _tracker_rows(candidate_ids=candidate_ids)
    counts = preflight_counts(rows)
    result = _execute(
        "SELECT tracker_duration_seconds, tracker_error, tracker_rows_updated "
        "FROM was_batch_runs WHERE batch_id=%s",
        (batch_id,),
        True,
    )
    if not result:
        raise ValueError("Unknown analyst batch ID.")
    duration, error, updated = result[0]
    body = "Tracker phase finished. Batch: {}\n".format(batch_id)
    body += "Tracker time: {} seconds; rows updated: {}; error: {}\n".format(
        duration if duration is not None else "Not available",
        updated if updated is not None else "Not available",
        _safe_error(error) or "none",
    )
    body += "\n".join("{}: {}".format(key, value) for key, value in counts.items())
    body += "\nWebapp totals are known entries only; unknown counts are reports requiring review.\n"
    return _deliver(
        batch_id, "tracker", source_email, override_recipients, body, rows, dry_run
    )


def send_batch_summary(
    batch_id,
    source_email,
    override_recipients=None,
    dry_run=False,
    days_back=7,
):
    """Send one aggregate outcome and only unresolved manual items in the body."""
    batch = _execute(
        "SELECT EXTRACT(EPOCH FROM (COALESCE(finished_at,now())-started_at)), tracker_duration_seconds, "
        "tracker_error, worker_count, run_mode, workload_label, finished_at, outcome "
        "FROM was_batch_runs WHERE batch_id=%s",
        (batch_id,),
        True,
    )
    if not batch:
        raise ValueError("Unknown analyst batch ID.")
    attempts = _execute(
        """SELECT attempts.duration_seconds, attempts.generated,
        attempts.sent, attempts.error,
        COALESCE(attempts.artifact_type, runs.artifact_type),
        attempts.delivery_duration_seconds
        FROM was_batch_report_attempts attempts
        LEFT JOIN was_report_runs runs ON runs.id=attempts.report_run_id
        WHERE attempts.batch_id=%s""",
        (batch_id,),
        True,
    )
    elapsed, tracker_duration, tracker_error, workers, mode, workload, finished, outcome = batch[0]
    continuation = mode == "capacity" and str(workload or "").startswith("continuation of ")
    total = sum(float(row[0]) for row in attempts)
    sent = sum(bool(row[2]) for row in attempts)
    durations = sorted(
        float(row[0]) for row in attempts if row[4] == "pdf" and float(row[0]) > 0
    )
    median = statistics.median(durations) if durations else None
    percentile95 = durations[math.ceil(len(durations) * 0.95) - 1] if durations else None
    pdfs = sum(bool(row[1]) and row[4] == "pdf" for row in attempts)
    notifications = sum((bool(row[1]) or bool(row[2])) and row[4] == "notification" for row in attempts)
    error_codes = {_safe_error(row[3]) for row in attempts if row[3]}
    if tracker_error:
        error_codes.add(_safe_error(tracker_error))
    lines = [
        "WAS batch: {}".format(batch_id),
        "Run mode: {}; workers: {}; workload: {}; outcome: {}".format(
            mode, workers, workload or "Not supplied", outcome or "running"
        ),
        "Completion time: {}".format(finished or "Not finished; wall time is provisional"),
        "Elapsed wall time: {:.2f} seconds".format(float(elapsed)),
        "Tracker time: {} seconds".format(tracker_duration),
        "Attempted: {}; generated: {}; attempts with errors: {}; sent: {}; unsent: {}".format(
            len(attempts),
            sum(bool(row[1]) for row in attempts),
            sum(bool(row[3]) for row in attempts),
            sent,
            len(attempts) - sent,
        ),
        "Sum of recorded per-report artifact preparation durations: {:.2f} seconds".format(total),
        "PDFs generated: {}; notifications generated: {}".format(pdfs, notifications),
        "PDF generation median: {}; p95 (nearest rank): {} seconds".format(median, percentile95),
        "PDF timing statistics include positive-duration PDF attempts, including failed attempts.",
        "Accepted deliveries per minute: {}".format(
            "{:.2f}".format(sent * 60 / float(elapsed))
            if finished and float(elapsed) > 0 and not continuation else "Not available"
        ),
        "Accepted deliveries per hour: {}".format(
            "{:.2f}".format(sent * 3600 / float(elapsed))
            if finished and float(elapsed) > 0 and not continuation else "Not available"
        ),
        "Sum of recorded per-report delivery durations: {:.2f} seconds".format(
            sum(float(row[5]) for row in attempts if row[5] is not None)
        ),
        ("Sent totals include prior attempts' persisted SES acceptance; they are not new sends."
         if continuation else
         "Sent counts use this batch's recorded SES acceptance, not recipient delivery."),
        "Duration aggregates retain the longest observation per report on retries; they are not wall time or total retry cost.",
        "Average PDF generation time (timed PDF attempts): {}".format(
            "{:.2f} seconds".format(sum(durations) / len(durations))
            if durations
            else "Not available"
        ),
        "Errors: {}".format(", ".join(sorted(error_codes)) or "none"),
    ]
    if continuation:
        lines.insert(2, "CONTINUATION: workload totals include previous completions. "
                     "Generated totals mean artifacts available across attempts. "
                     "This is not a fresh throughput or 600-report capacity benchmark.")
    if mode == "capacity":
        try:
            progress = json.loads(getenv("WAS_CAPACITY_PROGRESS", "{}"))
            keys = ("total", "completed", "failed", "remaining", "blocked")
            if isinstance(progress, dict) and all(
                type(progress.get(key)) is int and progress[key] >= 0 for key in keys
            ):
                lines.insert(2, "Workload status: " + "; ".join(
                    "{}={}".format(key, progress[key]) for key in keys
                ))
        except (TypeError, ValueError):
            LOGGER.warning("Capacity progress summary metadata is invalid; omitted.")
    rows = _tracker_rows(batch_id=batch_id, days_back=days_back)
    lines.extend(("", *manual_work_summary_lines(rows)))
    if not attempts:
        lines.append("No recorded report attempts; generation metrics are unavailable.")
    return _deliver(
        batch_id,
        "final",
        source_email,
        override_recipients,
        "\n".join(lines),
        rows,
        dry_run,
    )


def main(argv=None):
    """Expose the combined summaries to the shell batch orchestrator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("tracker", "final"), required=True)
    parser.add_argument("--batch-id", default=getenv("WAS_ANALYST_BATCH_ID"))
    parser.add_argument("--source-email", default=getenv("WAS_EMAIL_SOURCE"))
    parser.add_argument("--days-back", default="7")
    parser.add_argument("--test-recipients")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--outcome", choices=("completed", "failed"),
                        default=getenv("WAS_BATCH_OUTCOME", "completed"))
    arguments = parser.parse_args(argv)
    if not arguments.batch_id or not arguments.source_email:
        parser.error("--batch-id and --source-email are required.")
    if arguments.phase == "tracker":
        days = (
            None if arguments.days_back.lower() == "all" else int(arguments.days_back)
        )
        candidates = list_ready_report_candidates_from_db(days_back=days)
        tracker_scope = capacity_tracker_ids()
        if tracker_scope is not None:
            candidates = [row for row in candidates if row.id in tracker_scope]
        send_tracker_summary(
            arguments.batch_id,
            [row.id for row in candidates],
            arguments.source_email,
            arguments.test_recipients,
            arguments.dry_run,
        )
    else:
        days = (
            None if arguments.days_back.lower() == "all" else int(arguments.days_back)
        )
        if not arguments.dry_run:
            finish_batch(arguments.batch_id, arguments.outcome)
        send_batch_summary(
            arguments.batch_id,
            arguments.source_email,
            arguments.test_recipients,
            arguments.dry_run,
            days,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
