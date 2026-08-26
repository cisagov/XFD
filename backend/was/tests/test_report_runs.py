"""Tests for WAS report run data access."""

# Standard Python Libraries
import unittest

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
            ("TAG1", report_runs.RUNNING, 1720000001),
        )

    def test_complete_report_run_sets_completed_status(self) -> None:
        """Mark an existing report execution as completed."""
        conn = FakeConnection()

        report_runs.complete_report_run(report_run_id=7, conn=conn)

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (report_runs.COMPLETED, None, None, None, 7),
        )

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
        conn = FakeConnection()

        report_runs.mark_report_run_emailed(
            report_run_id=7,
            message_id="message-id",
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(conn.cursor_instance.parameters, ("message-id", 7))

    def test_mark_report_run_email_failed_records_error(self) -> None:
        """Record email delivery failure metadata."""
        conn = FakeConnection()

        report_runs.mark_report_run_email_failed(
            report_run_id=7,
            error_message="delivery failed",
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(conn.cursor_instance.parameters, ("delivery failed", 7))

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
                )
            ]
        )

        report_run_emails = report_runs.list_report_runs_ready_for_email(
            conn=conn,
            limit=5,
        )

        self.assertEqual(report_run_emails[0].id, 7)
        self.assertIn("runs.email_error IS NULL", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (report_runs.COMPLETED, 5))

    def test_list_report_runs_ready_for_email_can_retry_failures(self) -> None:
        """Allow failed email runs to be selected for retry."""
        conn = FakeConnection(row=[])

        report_runs.list_report_runs_ready_for_email(
            conn=conn,
            include_previous_failures=True,
        )

        self.assertNotIn("runs.email_error IS NULL", conn.cursor_instance.query)


if __name__ == "__main__":
    unittest.main()
