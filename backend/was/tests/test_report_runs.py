"""Tests for WAS report run data access."""

# Standard Python Libraries
from datetime import datetime, timezone
import unittest

# Third-Party Libraries
# First-Party Libraries
from was_reports.data import report_runs


class FakeCursor:
    """Small cursor test double for report run tests."""

    def __init__(self, row=None):
        """Initialize the fake cursor."""
        self.row = row
        self.query = None
        self.parameters = None

    def __enter__(self):
        """Return this cursor for context manager usage."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""

    def execute(self, query, parameters):
        """Capture the executed query and parameters."""
        self.query = query
        self.parameters = parameters

    def fetchone(self):
        """Return the configured row."""
        return self.row

    def fetchall(self):
        """Return configured rows for list queries."""
        return self.row


class FakeConnection:
    """Small connection test double for report run tests."""

    def __init__(self, row=None):
        """Initialize the fake connection."""
        self.cursor_instance = FakeCursor(row=row)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        """Return the fake cursor."""
        return self.cursor_instance

    def commit(self):
        """Record commit usage."""
        self.committed = True

    def rollback(self):
        """Record rollback usage."""
        self.rolled_back = True


class ReportRunTests(unittest.TestCase):
    """Validate report run persistence helpers."""

    def test_create_report_run_inserts_running_record(self) -> None:
        """Create a running report execution record."""
        conn = FakeConnection(row=(7, "TAG1", report_runs.RUNNING))

        report_run = report_runs.create_report_run(
            stakeholder_tag="TAG1",
            scheduled_epoch=1720000001,
            conn=conn,
        )

        self.assertEqual(report_run.id, 7)
        self.assertEqual(report_run.status, report_runs.RUNNING)
        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("TAG1", report_runs.RUNNING, 1720000001, None),
        )
        self.assertIn("ON CONFLICT", conn.cursor_instance.query)

    def test_create_report_run_skips_an_active_schedule_claim(self) -> None:
        """Return no run when another worker already claimed the schedule."""
        conn = FakeConnection(row=None)

        report_run = report_runs.create_report_run(
            stakeholder_tag="TAG1",
            scheduled_epoch=1720000001,
            conn=conn,
        )

        self.assertIsNone(report_run)
        self.assertTrue(conn.committed)

    def test_create_report_run_claims_source_tracker_row(self) -> None:
        """Claim one tracker row using its unique report-run link."""
        conn = FakeConnection(row=(8, "TAG2", report_runs.RUNNING))

        report_run = report_runs.create_report_run(
            stakeholder_tag="TAG2",
            scheduled_epoch=None,
            source_tracker_id=42,
            conn=conn,
        )

        self.assertEqual(report_run.id, 8)
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("TAG2", report_runs.RUNNING, None, 42),
        )

    def test_complete_report_run_sets_completed_status(self) -> None:
        """Mark an existing report execution as completed."""
        conn = FakeConnection(row=(7,))

        report_runs.complete_report_run(report_run_id=7, conn=conn)

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (report_runs.COMPLETED, None, None, None, 7),
        )

    def test_retry_failed_tracker_run_reclaims_existing_record(self) -> None:
        """Reuse a failed tracker run without violating its unique link."""
        conn = FakeConnection(row=(7, "TAG1", report_runs.RUNNING))

        report_run = report_runs.retry_failed_report_run_for_tracker(
            source_tracker_id=42,
            conn=conn,
        )

        self.assertEqual(report_run.id, 7)
        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.RUNNING,
                report_runs.EMAIL_PENDING,
                42,
                report_runs.FAILED,
            ),
        )
        self.assertIn("error_message = NULL", conn.cursor_instance.query)

    def test_complete_report_run_can_store_output_metadata(self) -> None:
        """Mark a report complete with artifact details."""
        conn = FakeConnection()

        report_runs.complete_report_run(
            report_run_id=7,
            output_path="/WAS_REPORT_GENERATION/docs/TAG1_report_2026-08-25.pdf",
            artifact_type="pdf",
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                None,
                "/WAS_REPORT_GENERATION/docs/TAG1_report_2026-08-25.pdf",
                "pdf",
                7,
            ),
        )

    def test_fail_report_run_sets_failed_status(self) -> None:
        """Mark an existing report execution as failed."""
        conn = FakeConnection()

        report_runs.fail_report_run(
            report_run_id=7,
            error_message="Report generation failed.",
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (report_runs.FAILED, "Report generation failed.", None, None, 7),
        )

    def test_mark_report_run_emailed_records_message_id(self) -> None:
        """Record successful email delivery metadata."""
        conn = FakeConnection(row=(7,))

        report_runs.mark_report_run_emailed(
            report_run_id=7,
            message_id="message-id",
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                "message-id",
                report_runs.EMAIL_SENT,
                7,
                report_runs.EMAIL_SENDING,
            ),
        )
        self.assertIn("report_sent_date = CURRENT_DATE", conn.cursor_instance.query)

    def test_mark_report_run_email_failed_records_error(self) -> None:
        """Record email delivery failure metadata."""
        conn = FakeConnection(row=(7,))

        report_runs.mark_report_run_email_failed(
            report_run_id=7,
            error_message="delivery failed",
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                "delivery failed",
                report_runs.EMAIL_FAILED,
                7,
                report_runs.EMAIL_SENDING,
            ),
        )

    def test_list_report_runs_ready_for_email_excludes_failures(self) -> None:
        """Return completed report runs that are ready to email."""
        conn = FakeConnection(
            row=[
                (
                    7,
                    "TAG1",
                    "/WAS_REPORT_GENERATION/docs/report.pdf",
                    "password",
                    "distro@example.gov",
                    "tech@example.gov",
                    "poc@example.gov",
                    None,
                )
            ]
        )

        report_run_emails = report_runs.list_report_runs_ready_for_email(
            conn=conn,
            limit=5,
            stakeholder_tag="TAG1",
        )

        self.assertEqual(report_run_emails[0].id, 7)
        self.assertIn("COALESCE(runs.email_status", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING],
                "TAG1",
                5,
            ),
        )
        self.assertIn("runs.stakeholder_tag = %s", conn.cursor_instance.query)

    def test_list_report_runs_ready_for_email_can_retry_failures(self) -> None:
        """Allow failed email runs to be selected for retry."""
        conn = FakeConnection(row=[])

        report_runs.list_report_runs_ready_for_email(
            conn=conn,
            include_previous_failures=True,
        )

        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING, report_runs.EMAIL_FAILED],
            ),
        )

    def test_claim_report_run_email_updates_pending_row_atomically(self) -> None:
        """Claim one pending email before an external delivery side effect."""
        conn = FakeConnection(
            row=(
                7,
                "TAG1",
                "s3://reports/was_reports/report.pdf",
                42,
                "password",
                "distro@example.gov",
                "tech@example.gov",
                "poc@example.gov",
            )
        )

        claimed = report_runs.claim_report_run_email(
            report_run_id=7,
            conn=conn,
        )

        self.assertEqual(claimed.id, 7)
        self.assertEqual(claimed.source_tracker_id, 42)
        self.assertTrue(conn.committed)
        self.assertIn("UPDATE was_report_runs", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.EMAIL_SENDING,
                7,
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING],
            ),
        )

    def test_claim_report_run_email_rejects_existing_claim(self) -> None:
        """Return no email when another mailer already owns the run."""
        conn = FakeConnection(row=None)

        claimed = report_runs.claim_report_run_email(
            report_run_id=7,
            conn=conn,
        )

        self.assertIsNone(claimed)
        self.assertTrue(conn.committed)

    def test_list_report_run_errors_filters_recent_tag(self) -> None:
        """Return persisted report and delivery failures for operators."""
        timestamp = datetime(2026, 9, 1, tzinfo=timezone.utc)
        conn = FakeConnection(
            row=[
                (
                    7,
                    "TAG1",
                    report_runs.FAILED,
                    report_runs.EMAIL_PENDING,
                    timestamp,
                    timestamp,
                    "Report generation failed.",
                    None,
                )
            ]
        )

        errors = report_runs.list_report_run_errors(
            conn=conn,
            days_back=14,
            stakeholder_tag=" TAG1 ",
            limit=25,
        )

        self.assertEqual(errors[0].id, 7)
        self.assertEqual(errors[0].error_message, "Report generation failed.")
        self.assertEqual(conn.cursor_instance.parameters, (14, "TAG1", 25))
        self.assertIn("email_error", conn.cursor_instance.query)


if __name__ == "__main__":
    unittest.main()
