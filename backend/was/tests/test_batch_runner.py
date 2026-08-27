"""Tests for the scheduled WAS batch runner."""

# Standard Python Libraries
import subprocess
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import batch_runner
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
            config_path="/app/was_config.txt",
            legacy_root="/WAS_REPORT_GENERATION",
            output_directory="/WAS_REPORT_GENERATION/docs",
            python_executable="/usr/local/bin/python",
            create_missing_password=True,
            allow_unencrypted=False,
        )

        self.assertEqual(
            arguments,
            [
                "--tag",
                "TAG1",
                "--config-path",
                "/app/was_config.txt",
                "--legacy-root",
                "/WAS_REPORT_GENERATION",
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
            config_path="/app/was_config.txt",
            legacy_root="/WAS_REPORT_GENERATION",
            python_executable="/usr/local/bin/python",
            current_epoch=1720000001,
            create_missing_password=True,
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
            config_path="/app/was_config.txt",
            legacy_root="/WAS_REPORT_GENERATION",
            python_executable="/usr/local/bin/python",
            current_epoch=1720000001,
            continue_on_error=True,
        )

        self.assertEqual(failed_count, 1)
        self.assertEqual(mock_report_main.call_count, 2)
        self.assertEqual(mock_logger_exception.call_count, 1)
        self.assertEqual(mock_complete_run.call_count, 1)
        mock_fail_run.assert_called_once_with(
            report_run_id=1,
            error_message="Report generation failed with exit code 2.",
        )


if __name__ == "__main__":
    unittest.main()
