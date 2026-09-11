"""Tests for the scheduled WAS batch runner."""

# Standard Python Libraries
from contextlib import ExitStack
from datetime import date, datetime, timezone
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import batch_runner
from was_reports.data.daily_report_tracker import TrackerReportCandidate
from was_reports.data.report_runs import ReportRun
from was_reports.data.stakeholders import Stakeholder, list_due_stakeholders
from was_reports.storage import s3_reports


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

    def setUp(self) -> None:
        """Keep database lease refreshes at the external test boundary."""
        self.touch_patch = patch.object(
            batch_runner, "touch_report_run_by_id", return_value=True
        )
        self.touch_report = self.touch_patch.start()
        self.addCleanup(self.touch_patch.stop)

    def write_report(self, arguments, *, current_time: datetime) -> None:
        """Write an output artifact at the mocked generation boundary."""
        output_directory = Path(arguments[arguments.index("--output-directory") + 1])
        output_directory.mkdir(parents=True, exist_ok=True)
        batch_runner.expected_pdf_output_path(
            stakeholder_tag="TAG1",
            output_directory=str(output_directory),
            report_date=current_time.date(),
        ).write_bytes(b"encrypted-test-pdf")

    def test_output_and_s3_use_the_same_captured_utc_date(self) -> None:
        """Keep output discovery and S3 keys stable across midnight and timezones."""
        captured = datetime(2026, 9, 12, 0, 0, 1, tzinfo=timezone.utc)
        generated_times = []

        def generate(**arguments) -> Path:
            """Write the output using the timestamp forwarded through the real CLI."""
            generated_times.append(arguments["current_time"])
            directory = arguments["output_directory"]
            directory.mkdir(parents=True, exist_ok=True)
            output = batch_runner.expected_pdf_output_path(
                "TAG1", str(directory), arguments["current_time"].date()
            )
            output.write_bytes(b"encrypted-test-pdf")
            return output

        for mode in ("s3", "local"):
            with self.subTest(
                mode=mode
            ), tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
                clock = stack.enter_context(patch.object(batch_runner, "datetime"))
                clock.now.side_effect = [
                    captured,
                    datetime(2026, 9, 13, tzinfo=timezone.utc),
                ]
                stack.enter_context(
                    patch(
                        "was_reports.data.report_runs.touch_report_run_by_id",
                        return_value=True,
                    )
                )
                stack.enter_context(
                    patch.object(
                        batch_runner.report_generator,
                        "resolve_report_password",
                        return_value="test-password",
                    )
                )
                stack.enter_context(
                    patch.object(
                        batch_runner.report_generator,
                        "generate_production_report",
                        side_effect=generate,
                    )
                )
                upload = stack.enter_context(
                    patch.object(
                        batch_runner,
                        "upload_report",
                        return_value="s3://reports/report.pdf",
                    )
                )
                output = batch_runner.generate_report_output(
                    report_run_id=42,
                    generation_token="token",
                    stakeholder_tag="TAG1",
                    resource_root="/resources",
                    python_executable="python3",
                    create_missing_password=False,
                    output_directory=directory,
                    storage_mode=mode,
                    staging_directory=directory,
                )
                clock.now.assert_called_once_with(timezone.utc)
                self.assertEqual(generated_times[-1], captured)
                if mode == "s3":
                    self.assertEqual(
                        upload.call_args.kwargs["report_date"], captured.date()
                    )
                    self.assertIn(
                        "2026-09-12",
                        upload.call_args.kwargs["report_path"].name,
                    )
                else:
                    self.assertTrue(Path(output).is_file())
                    self.assertIn("2026-09-12", Path(output).name)
                    upload.assert_not_called()

    def test_lost_lease_prevents_s3_upload(self) -> None:
        """Reject a worker reclaimed while its PDF was being generated."""

        def generate(arguments, *, current_time: datetime) -> None:
            """Produce the PDF then simulate the lease being reclaimed."""
            self.write_report(arguments, current_time=current_time)
            self.touch_report.return_value = False

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                batch_runner.report_generator, "main", side_effect=generate
            ):
                with patch.object(batch_runner, "upload_report") as upload:
                    with self.assertRaises(batch_runner.OperationLeaseLostError):
                        batch_runner.generate_report_output(
                            report_run_id=42,
                            generation_token="token",
                            stakeholder_tag="TAG1",
                            resource_root="/resources",
                            python_executable="python3",
                            create_missing_password=False,
                            output_directory=directory,
                            storage_mode="s3",
                            staging_directory=directory,
                        )
                    upload.assert_not_called()

    def test_recent_batch_retains_artifact_after_commit_acknowledgment_loss(
        self,
    ) -> None:
        """Do not fail, delete, or email a run with uncertain commit results."""
        candidate = TrackerReportCandidate(
            id=9,
            tag="TAG1",
            data_pull_date=date.today(),
            schedule_id=123,
            assignee_id=3,
        )
        report_run = ReportRun(42, "TAG1", "running", generation_token="token")
        durable_state = {}

        def commit_then_disconnect(*arguments, **keywords) -> None:
            """Simulate a durable commit followed by a lost database response."""
            durable_state.update(keywords)
            raise OSError("commit acknowledgment lost")

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "list_ready_report_candidates_from_db",
                    return_value=[candidate],
                )
            )
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "create_report_run_for_tracker",
                    return_value=report_run,
                )
            )
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "generate_report_output",
                    return_value="s3://reports/run-token.pdf",
                )
            )
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "complete_report_run_by_id",
                    side_effect=commit_then_disconnect,
                )
            )
            fail = stack.enter_context(
                patch.object(batch_runner, "fail_report_run_by_id")
            )
            delete = stack.enter_context(patch.object(s3_reports, "delete_report"))
            send = stack.enter_context(
                patch.object(batch_runner, "send_report_run_email")
            )
            summary = batch_runner.run_recent_scan_reports(
                resource_root="/resources",
                python_executable="python3",
                continue_on_error=True,
            )
        self.assertEqual(summary.failed, 1)
        self.assertEqual(summary.generated, 0)
        self.assertEqual(durable_state["output_path"], "s3://reports/run-token.pdf")
        self.assertEqual(durable_state["generation_token"], "token")
        fail.assert_not_called()
        delete.assert_not_called()
        send.assert_not_called()

    def test_lost_lease_failure_does_not_mutate_new_owner(self) -> None:
        """Leave a reclaimed run and tracker untouched by the former worker."""
        report_run = ReportRun(42, "TAG1", "running", generation_token="old")
        with patch.object(batch_runner, "fail_report_run_by_id") as fail:
            batch_runner.record_generation_failure(
                report_run,
                "lost",
                batch_runner.OperationLeaseLostError("lost"),
            )
        fail.assert_not_called()

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
            report_run_id=17,
            generation_token="token",
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
                "--report-run-id",
                "17",
                "--generation-token",
                "token",
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

    def test_summarize_report_failure_preserves_safe_qualys_stage(
        self,
    ) -> None:
        """Store actionable reconciliation context without request details."""
        exception = batch_runner.QualysReportCreationUncertainError(
            "Qualys XML report creation timed out."
        )

        message = batch_runner.summarize_report_failure(exception)

        self.assertIn("reconcile before retrying", message)
        self.assertIn("QualysReportCreationUncertainError", message)
        self.assertNotIn("--encrypt", message)

    def test_summarize_failure_excludes_qualys_exception_payload(self) -> None:
        """Never persist Qualys payloads even for uncertain-create errors."""
        error = batch_runner.QualysReportCreationUncertainError(
            "password=private-password token=private-token"
        )
        message = batch_runner.summarize_report_failure(error)
        self.assertNotIn("private-password", message)
        self.assertNotIn("private-token", message)

    def test_summarize_failure_uses_safe_exception_details(self) -> None:
        """Preserve safe diagnostics without formatting the exception text."""
        error = RuntimeError("private-password")
        with patch.object(
            batch_runner,
            "exception_details",
            return_value="RuntimeError sqlstate=42703",
        ) as details:
            message = batch_runner.summarize_report_failure(error)
        details.assert_called_once_with(error)
        self.assertIn("sqlstate=42703", message)
        self.assertNotIn("private-password", message)

    def test_summarize_failure_preserves_metadata_without_payload(
        self,
    ) -> None:
        """Exercise the real diagnostic helper with database and HTTP metadata."""
        error = RuntimeError("private-password private-token")
        setattr(error, "pgcode", "42703")
        setattr(
            error,
            "diag",
            SimpleNamespace(
                table_name="was_report_runs",
                column_name="generation_token",
                constraint_name=None,
            ),
        )
        setattr(
            error, "response", SimpleNamespace(status_code=503, text="private-body")
        )
        message = batch_runner.summarize_report_failure(error)
        for detail in (
            "SQLSTATE=42703",
            "table_name=was_report_runs",
            "column_name=generation_token",
            "HTTP=503",
        ):
            self.assertIn(detail, message)
        for sensitive in ("private-password", "private-token", "private-body"):
            self.assertNotIn(sensitive, message)

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
            ReportRun(
                id=1,
                stakeholder_tag="TAG1",
                status="running",
                generation_token="token",
            ),
            ReportRun(
                id=2,
                stakeholder_tag="TAG2",
                status="running",
                generation_token="token",
            ),
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
    @patch("was_reports.commands.batch_runner.LOGGER.error")
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
            ReportRun(
                id=1,
                stakeholder_tag="TAG1",
                status="running",
                generation_token="token",
            ),
            ReportRun(
                id=2,
                stakeholder_tag="TAG2",
                status="running",
                generation_token="token",
            ),
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
            generation_token="token",
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
        report_run = ReportRun(
            id=42,
            stakeholder_tag="TAG1",
            status="running",
            generation_token="token",
        )
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
                    with patch.object(
                        batch_runner.report_generator,
                        "main",
                        side_effect=self.write_report,
                    ):
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
        self.assertTrue(uploaded_path.name.endswith("-token.pdf"))
        self.assertFalse(uploaded_path.parent.exists())
        mock_complete.assert_called_once_with(
            42,
            output_path="s3://reports/was_reports/report.pdf",
            artifact_type="pdf",
            generation_token="token",
        )

    def test_run_due_reports_retains_s3_object_when_completion_fails(
        self,
    ) -> None:
        """Retain an uploaded object after an uncertain database commit."""
        stakeholder = Stakeholder(tag="TAG1", report_password="password")
        report_run = ReportRun(
            id=42,
            stakeholder_tag="TAG1",
            status="running",
            generation_token="token",
        )
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
                    with patch.object(
                        batch_runner.report_generator,
                        "main",
                        side_effect=self.write_report,
                    ):
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
                                    s3_reports,
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

        mock_delete.assert_not_called()

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
            generation_token="token",
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
            generation_token="token",
        )
        mock_send_report.assert_called_once_with(
            report_run_id=42,
            source_email="reports@example.gov",
            override_recipients=None,
            dry_run=False,
        )

    @patch("was_reports.commands.batch_runner.send_report_run_email")
    @patch("was_reports.commands.batch_runner.send_ready_report_emails")
    @patch("was_reports.commands.batch_runner.complete_report_run_by_id")
    @patch("was_reports.commands.batch_runner.generate_report_output")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tracker")
    @patch("was_reports.commands.batch_runner.list_ready_report_candidates_from_db")
    def test_all_nws_sends_notification_without_generating_pdf(
        self,
        mock_list_candidates,
        mock_create_run,
        mock_generate_report,
        mock_complete_run,
        mock_send_ready,
        mock_send_report,
    ) -> None:
        """Complete and send an All NWS notification without creating a PDF."""
        mock_list_candidates.return_value = [
            TrackerReportCandidate(
                id=9,
                tag="TAG1",
                data_pull_date=date(2026, 9, 1),
                schedule_id=123,
                assignee_id=3,
                template="All NWS",
            )
        ]
        mock_create_run.return_value = ReportRun(
            id=42,
            stakeholder_tag="TAG1",
            status="running",
            generation_token="token",
        )
        mock_send_ready.return_value = 0
        mock_send_report.return_value = "message-id"

        summary = batch_runner.run_recent_scan_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            stakeholder_tag="TAG1",
            send_email=True,
            source_email="reports@example.gov",
        )

        self.assertEqual(summary.generated, 0)
        self.assertEqual(summary.sent, 1)
        mock_generate_report.assert_not_called()
        mock_complete_run.assert_called_once_with(
            42,
            artifact_type="notification",
            generation_token="token",
        )
        mock_send_report.assert_called_once()

    @patch("was_reports.data.daily_report_tracker.mark_tracker_report_manual_by_id")
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
            generation_token="token",
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
            generation_token="token",
        )
        mock_mark_manual.assert_not_called()

    @patch("was_reports.commands.batch_runner.send_report_run_email")
    @patch("was_reports.commands.batch_runner.send_ready_report_emails")
    @patch("was_reports.commands.batch_runner.complete_report_run_by_id")
    @patch("was_reports.commands.batch_runner.generate_report_output")
    @patch(
        "was_reports.commands.batch_runner." "retry_failed_report_run_for_tracker_by_id"
    )
    @patch("was_reports.commands.batch_runner.create_report_run_for_tracker")
    @patch("was_reports.commands.batch_runner.list_ready_report_candidates_from_db")
    def test_manual_report_retries_failed_tracker_run_and_sends(
        self,
        mock_list_candidates,
        mock_create_run,
        mock_retry_run,
        mock_generate_report,
        mock_complete_run,
        mock_send_ready,
        mock_send_report,
    ) -> None:
        """Run a manual report through storage, delivery, and tracking."""
        mock_list_candidates.return_value = [
            TrackerReportCandidate(
                id=9,
                tag="TAG1",
                data_pull_date=date(2026, 9, 1),
                schedule_id=123,
                assignee_id=3,
            )
        ]
        mock_create_run.return_value = None
        mock_retry_run.return_value = ReportRun(
            id=42,
            stakeholder_tag="TAG1",
            status="running",
            generation_token="token",
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
            include_manual=True,
        )

        self.assertEqual(summary.generated, 1)
        self.assertEqual(summary.sent, 1)
        mock_list_candidates.assert_called_once_with(
            stakeholder_tag="TAG1",
            limit=None,
            include_manual=True,
        )
        mock_retry_run.assert_called_once_with(9)
        mock_send_ready.assert_not_called()
        mock_complete_run.assert_called_once_with(
            42,
            output_path="s3://reports/report.pdf",
            artifact_type="pdf",
            generation_token="token",
        )

    def test_main_requires_tag_for_manual_recent_scan_report(self) -> None:
        """Prevent an accidental manual report run across all stakeholders."""
        with self.assertRaisesRegex(
            ValueError,
            "Manual report generation requires --tag.",
        ):
            batch_runner.main(["--recent-scans", "--include-manual"])

    @patch("was_reports.commands.batch_runner.send_report_run_email")
    @patch("was_reports.commands.batch_runner.send_ready_report_emails")
    @patch("was_reports.commands.batch_runner.generate_report_output")
    @patch("was_reports.commands.batch_runner.create_report_run_for_tracker")
    @patch("was_reports.commands.batch_runner.list_ready_report_candidates_from_db")
    def test_manual_report_retries_only_its_completed_email(
        self,
        mock_list_candidates,
        mock_create_run,
        mock_generate_report,
        mock_send_ready,
        mock_send_report,
    ) -> None:
        """Retry one linked email without sending unrelated tag reports."""
        mock_list_candidates.return_value = [
            TrackerReportCandidate(
                id=9,
                tag="TAG1",
                data_pull_date=date(2026, 9, 1),
                schedule_id=123,
                assignee_id=3,
                report_run_id=42,
                report_run_status="completed",
                report_email_status="failed",
            )
        ]
        mock_send_report.return_value = "message-id"

        summary = batch_runner.run_recent_scan_reports(
            resource_root="/WAS_REPORT_RESOURCES",
            python_executable="/usr/local/bin/python",
            stakeholder_tag="TAG1",
            send_email=True,
            source_email="reports@example.gov",
            include_manual=True,
        )

        self.assertEqual(summary.generated, 0)
        self.assertEqual(summary.sent, 1)
        mock_send_ready.assert_not_called()
        mock_create_run.assert_not_called()
        mock_generate_report.assert_not_called()
        mock_send_report.assert_called_once_with(
            report_run_id=42,
            source_email="reports@example.gov",
            override_recipients=None,
            dry_run=False,
            include_previous_failure=True,
        )

    def test_main_requires_email_for_manual_recent_scan_report(self) -> None:
        """Require delivery so a tracked manual report can be stamped sent."""
        with self.assertRaisesRegex(
            ValueError,
            "Manual report generation requires --send-email.",
        ):
            batch_runner.main(["--recent-scans", "--include-manual", "--tag", "TAG1"])

    @patch("was_reports.commands.batch_runner.recover_stale_report_operations_in_db")
    @patch("was_reports.commands.batch_runner.run_recent_scan_reports")
    @patch("was_reports.commands.batch_runner.run_update_tracker")
    def test_main_recent_scans_refreshes_tracker_before_batch(
        self,
        mock_update_tracker,
        mock_run_recent,
        mock_recover_stale,
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
        mock_recover_stale.assert_called_once_with()
        mock_update_tracker.assert_called_once_with(
            delete_apps=False,
            stakeholder_tag="TAG1",
        )
        self.assertEqual(mock_run_recent.call_args.kwargs["stakeholder_tag"], "TAG1")

    @patch("was_reports.commands.batch_runner.recover_stale_report_operations_in_db")
    @patch("was_reports.commands.batch_runner.run_recent_scan_reports")
    @patch("was_reports.commands.batch_runner.run_update_tracker")
    @patch("was_reports.commands.batch_runner.approved_analyst_recipients")
    def test_main_validates_batch_test_recipient_before_processing(
        self,
        mock_approved_recipients,
        mock_update_tracker,
        mock_run_recent,
        mock_recover_stale,
    ) -> None:
        """Validate and normalize a batch recipient override before processing."""
        mock_approved_recipients.return_value = [
            "first@example.gov",
            "second@example.gov",
        ]
        mock_run_recent.return_value = batch_runner.BatchExecutionSummary(
            candidates=1,
            generated=1,
            sent=1,
            failed=0,
        )

        exit_code = batch_runner.main(
            [
                "--recent-scans",
                "--send-email",
                "--test-recipients",
                "first@example.gov; second@example.gov",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_approved_recipients.assert_called_once_with(
            "first@example.gov; second@example.gov"
        )
        self.assertEqual(
            mock_run_recent.call_args.kwargs["test_recipients"],
            "first@example.gov,second@example.gov",
        )
        mock_update_tracker.assert_called_once_with(
            delete_apps=False,
            stakeholder_tag=None,
        )
        mock_recover_stale.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
