"""Tests for the scheduled WAS batch runner."""

# Standard Python Libraries
from datetime import date
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import batch_runner
from was_reports.data.daily_report_tracker import TrackerReportCandidate
from was_reports.data.report_runs import ReportRun
from was_reports.data.stakeholders import Stakeholder, list_due_stakeholders


class FakeCursor:
    """Small DB cursor test double for stakeholder query tests."""

    def __init__(self, rows):
        """Initialize the fake cursor with rows."""
        self.rows = rows
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

    def fetchall(self):
        """Return configured rows."""
        return self.rows


class FakeConnection:
    """Small DB connection test double."""

    def __init__(self, rows):
        """Initialize the fake connection with cursor rows."""
        self.cursor_instance = FakeCursor(rows)

    def cursor(self):
        """Return the fake cursor."""
        return self.cursor_instance


class BatchRunnerTests(unittest.TestCase):
    """Validate scheduled report batch behavior."""

    def test_list_due_stakeholders_filters_manual_and_retired(self) -> None:
        """Query due stakeholders while excluding manual and retired rows."""
        conn = FakeConnection([("TAG1", "password", 1720000000, False, False)])

        stakeholders = list_due_stakeholders(conn, current_epoch=1720000001)

        self.assertEqual(stakeholders[0].tag, "TAG1")
        self.assertIn("manual_report IS NOT TRUE", conn.cursor_instance.query)
        self.assertIn("retired IS NOT TRUE", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (1720000001,))

    def test_list_due_stakeholders_applies_limit(self) -> None:
        """Apply a query limit when one is supplied."""
        conn = FakeConnection([])

        list_due_stakeholders(conn, current_epoch=1720000001, limit=5)

        self.assertIn("LIMIT %s", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (1720000001, 5))

    def test_build_report_arguments_forwards_report_options(self) -> None:
        """Build one single-report invocation from batch options."""
        arguments = batch_runner.build_report_arguments(
            stakeholder_tag="TAG1",
            resource_root="/WAS_REPORT_RESOURCES",
            output_directory="/WAS_REPORT_GENERATION/docs",
            python_executable="/usr/local/bin/python",
            create_missing_password=True,
        )

        self.assertEqual(
            arguments,
            [
                "--tag",
                "TAG1",
                "--resource-root",
                "/WAS_REPORT_RESOURCES",
                "--output-directory",
                "/WAS_REPORT_GENERATION/docs",
                "--python-executable",
                "/usr/local/bin/python",
                "--create-missing-password",
            ],
        )

    def test_summarize_report_failure_excludes_command_arguments(self) -> None:
        """Store legacy process failures without command arguments or passwords."""
        exception = subprocess.CalledProcessError(
            returncode=2,
            cmd=["legacy", "--encrypt", "secret-password"],
        )

        message = batch_runner.summarize_report_failure(exception)

        self.assertEqual(message, "Report generation failed with exit code 2.")
        self.assertNotIn("secret-password", message)
        self.assertNotIn("--encrypt", message)

    def test_summarize_report_failure_handles_missing_files(self) -> None:
        """Store a bounded message for missing report files."""
        message = batch_runner.summarize_report_failure(
            FileNotFoundError("/tmp/report.pdf")
        )

        self.assertEqual(message, "Required report file was not found.")

    @patch("was_reports.commands.batch_runner.report_generator.main")
    @patch("was_reports.commands.batch_runner.complete_report_run_by_id")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tag")
    @patch("was_reports.commands.batch_runner.list_due_stakeholders_for_report")
    def test_run_due_reports_generates_each_due_report(
        self,
        mock_list_stakeholders,
        mock_create_run,
        mock_complete_run,
        mock_report_main,
    ) -> None:
        """Run one report command per due stakeholder."""
        mock_list_stakeholders.return_value = [
            Stakeholder(tag="TAG1", report_password="password", next_scheduled=1),
            Stakeholder(tag="TAG2", report_password="password", next_scheduled=2),
        ]
        mock_create_run.side_effect = [
            ReportRun(id=1, stakeholder_tag="TAG1", status="running"),
            ReportRun(id=2, stakeholder_tag="TAG2", status="running"),
        ]

        failed_count = batch_runner.run_due_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            current_epoch=1720000001,
            create_missing_password=True,
            storage_mode="local",
        )

        self.assertEqual(failed_count, 0)
        self.assertEqual(mock_report_main.call_count, 2)
        self.assertEqual(mock_create_run.call_count, 2)
        self.assertEqual(mock_complete_run.call_count, 2)

    @patch("was_reports.commands.batch_runner.report_generator.main")
    @patch("was_reports.commands.batch_runner.fail_report_run_by_id")
    @patch("was_reports.commands.batch_runner.complete_report_run_by_id")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tag")
    @patch("was_reports.commands.batch_runner.LOGGER.exception")
    @patch("was_reports.commands.batch_runner.list_due_stakeholders_for_report")
    def test_run_due_reports_can_continue_after_failure(
        self,
        mock_list_stakeholders,
        mock_logger_exception,
        mock_create_run,
        mock_complete_run,
        mock_fail_run,
        mock_report_main,
    ) -> None:
        """Continue processing later stakeholders when requested."""
        mock_list_stakeholders.return_value = [
            Stakeholder(tag="TAG1", report_password="password"),
            Stakeholder(tag="TAG2", report_password="password"),
        ]
        mock_create_run.side_effect = [
            ReportRun(id=1, stakeholder_tag="TAG1", status="running"),
            ReportRun(id=2, stakeholder_tag="TAG2", status="running"),
        ]
        mock_report_main.side_effect = [
            subprocess.CalledProcessError(
                returncode=2,
                cmd=["legacy", "--encrypt", "secret-password"],
            ),
            0,
        ]

        failed_count = batch_runner.run_due_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            current_epoch=1720000001,
            continue_on_error=True,
            storage_mode="local",
        )

        self.assertEqual(failed_count, 1)
        self.assertEqual(mock_report_main.call_count, 2)
        self.assertEqual(mock_logger_exception.call_count, 1)
        self.assertEqual(mock_complete_run.call_count, 1)
        mock_fail_run.assert_called_once_with(
            report_run_id=1,
            error_message="Report generation failed with exit code 2.",
        )

    @patch("was_reports.commands.batch_runner.report_generator.main")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tag")
    @patch("was_reports.commands.batch_runner.list_due_stakeholders_for_report")
    def test_run_due_reports_skips_an_already_claimed_schedule(
        self,
        mock_list_stakeholders,
        mock_create_run,
        mock_report_main,
    ) -> None:
        """Do not generate a duplicate report claimed by another worker."""
        mock_list_stakeholders.return_value = [
            Stakeholder(tag="TAG1", report_password="password", next_scheduled=1)
        ]
        mock_create_run.return_value = None

        failed_count = batch_runner.run_due_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            current_epoch=1720000001,
            storage_mode="local",
        )

        self.assertEqual(failed_count, 0)
        mock_report_main.assert_not_called()

    def test_run_due_reports_uploads_to_s3_and_stores_uri(self) -> None:
        """Persist the S3 URI only after a successful report upload."""
        stakeholder = Stakeholder(
            tag="TAG1",
            report_password="password",
            next_scheduled=1,
        )
        report_run = ReportRun(id=42, stakeholder_tag="TAG1", status="running")
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                batch_runner,
                "list_due_stakeholders_for_report",
                return_value=[stakeholder],
            ):
                with patch.object(
                    batch_runner,
                    "create_report_run_for_tag",
                    return_value=report_run,
                ):
                    with patch.object(batch_runner.report_generator, "main"):
                        with patch.object(
                            batch_runner,
                            "upload_report",
                            return_value="s3://reports/was_reports/report.pdf",
                        ) as mock_upload:
                            with patch.object(
                                batch_runner,
                                "complete_report_run_by_id",
                            ) as mock_complete:
                                failed_count = batch_runner.run_due_reports(
                                    resource_root="/WAS_REPORT_RESOURCES",
                                    python_executable="/usr/local/bin/python",
                                    current_epoch=1720000001,
                                    storage_mode="s3",
                                    staging_directory=directory,
                                )

        self.assertEqual(failed_count, 0)
        uploaded_path = mock_upload.call_args.kwargs["report_path"]
        self.assertIsInstance(uploaded_path, Path)
        self.assertFalse(uploaded_path.parent.exists())
        mock_complete.assert_called_once_with(
            42,
            output_path="s3://reports/was_reports/report.pdf",
            artifact_type="pdf",
        )

    def test_run_due_reports_deletes_s3_object_when_completion_fails(self) -> None:
        """Remove an uploaded object when its database completion update fails."""
        stakeholder = Stakeholder(tag="TAG1", report_password="password")
        report_run = ReportRun(id=42, stakeholder_tag="TAG1", status="running")
        report_uri = "s3://reports/was_reports/2026-08-28/TAG1/42/report.pdf"
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                batch_runner,
                "list_due_stakeholders_for_report",
                return_value=[stakeholder],
            ):
                with patch.object(
                    batch_runner,
                    "create_report_run_for_tag",
                    return_value=report_run,
                ):
                    with patch.object(batch_runner.report_generator, "main"):
                        with patch.object(
                            batch_runner,
                            "upload_report",
                            return_value=report_uri,
                        ):
                            with patch.object(
                                batch_runner,
                                "complete_report_run_by_id",
                                side_effect=RuntimeError("database failed"),
                            ):
                                with patch.object(
                                    batch_runner,
                                    "delete_report",
                                ) as mock_delete:
                                    with patch.object(
                                        batch_runner,
                                        "fail_report_run_by_id",
                                    ):
                                        with self.assertRaises(RuntimeError):
                                            batch_runner.run_due_reports(
                                                resource_root=("/WAS_REPORT_RESOURCES"),
                                                python_executable=(
                                                    "/usr/local/bin/python"
                                                ),
                                                current_epoch=1720000001,
                                                storage_mode="s3",
                                                staging_directory=directory,
                                            )

        mock_delete.assert_called_once_with(report_uri)

    @patch("was_reports.commands.batch_runner.send_report_run_email")
    @patch("was_reports.commands.batch_runner.send_ready_report_emails")
    @patch("was_reports.commands.batch_runner.complete_report_run_by_id")
    @patch("was_reports.commands.batch_runner.generate_report_output")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tracker")
    @patch("was_reports.commands.batch_runner.list_ready_report_candidates_from_db")
    def test_run_recent_scan_reports_generates_and_sends_tracker_gap(
        self,
        mock_list_candidates,
        mock_create_run,
        mock_generate_report,
        mock_complete_run,
        mock_send_ready,
        mock_send_report,
    ) -> None:
        """Generate and send one recently scanned tracker row exactly once."""
        mock_list_candidates.return_value = [
            TrackerReportCandidate(
                id=9,
                tag="TAG1",
                data_pull_date=date(2026, 9, 1),
                schedule_id=123,
                assignee_id=3,
            )
        ]
        mock_create_run.return_value = ReportRun(
            id=42,
            stakeholder_tag="TAG1",
            status="running",
        )
        mock_generate_report.return_value = "s3://reports/report.pdf"
        mock_send_ready.return_value = 0
        mock_send_report.return_value = "message-id"

        summary = batch_runner.run_recent_scan_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            stakeholder_tag="TAG1",
            send_email=True,
            source_email="reports@example.gov",
        )

        self.assertEqual(summary.candidates, 1)
        self.assertEqual(summary.generated, 1)
        self.assertEqual(summary.sent, 1)
        self.assertEqual(summary.failed, 0)
        mock_send_ready.assert_called_once_with(
            source_email="reports@example.gov",
            override_recipients=None,
            dry_run=False,
            stakeholder_tag="TAG1",
        )
        mock_create_run.assert_called_once_with(
            stakeholder_tag="TAG1",
            source_tracker_id=9,
        )
        mock_complete_run.assert_called_once_with(
            42,
            output_path="s3://reports/report.pdf",
            artifact_type="pdf",
        )
        mock_send_report.assert_called_once_with(
            report_run_id=42,
            source_email="reports@example.gov",
            override_recipients=None,
            dry_run=False,
        )

    @patch("was_reports.commands.batch_runner.mark_tracker_report_manual_by_id")
    @patch("was_reports.commands.batch_runner.fail_report_run_by_id")
    @patch("was_reports.commands.batch_runner.generate_report_output")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tracker")
    @patch("was_reports.commands.batch_runner.list_ready_report_candidates_from_db")
    def test_run_recent_scan_reports_marks_generation_failure_manual(
        self,
        mock_list_candidates,
        mock_create_run,
        mock_generate_report,
        mock_fail_run,
        mock_mark_manual,
    ) -> None:
        """Mark a tracker row manual when automated generation fails."""
        mock_list_candidates.return_value = [
            TrackerReportCandidate(
                id=9,
                tag="TAG1",
                data_pull_date=date(2026, 9, 1),
                schedule_id=123,
                assignee_id=3,
            )
        ]
        mock_create_run.return_value = ReportRun(
            id=42,
            stakeholder_tag="TAG1",
            status="running",
        )
        mock_generate_report.side_effect = RuntimeError("generation failed")

        summary = batch_runner.run_recent_scan_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            continue_on_error=True,
        )

        self.assertEqual(summary.failed, 1)
        mock_fail_run.assert_called_once_with(
            report_run_id=42,
            error_message="RuntimeError occurred during report generation.",
        )
        mock_mark_manual.assert_called_once_with(9)

    @patch("was_reports.commands.batch_runner.run_recent_scan_reports")
    @patch("was_reports.commands.batch_runner.run_update_tracker")
    def test_main_recent_scans_refreshes_tracker_before_batch(
        self,
        mock_update_tracker,
        mock_run_recent,
    ) -> None:
        """Refresh Qualys tracker data before evaluating report-delivery gaps."""
        mock_run_recent.return_value = batch_runner.BatchExecutionSummary(
            candidates=1,
            generated=1,
            sent=1,
            failed=0,
        )

        exit_code = batch_runner.main(
            [
                "--recent-scans",
                "--tag",
                " TAG1 ",
                "--send-email",
                "--source-email",
                "reports@example.gov",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_update_tracker.assert_called_once_with(
            delete_apps=False,
            stakeholder_tag="TAG1",
        )
        self.assertEqual(mock_run_recent.call_args.kwargs["stakeholder_tag"], "TAG1")


if __name__ == "__main__":
    unittest.main()
