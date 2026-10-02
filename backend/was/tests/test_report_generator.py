"""Tests for the production WAS report generator CLI."""

# Standard Python Libraries
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import report_generator
from was_reports.utils import operation_lease


class ReportGeneratorTests(unittest.TestCase):
    """Validate production report arguments and password handling."""

    def test_generation_forwards_token_to_all_polling_callbacks(self) -> None:
        """Keep persisted Qualys state bound to the generation owner."""
        # Third-Party Libraries
        from was_reports.data import report_runs
        from was_reports.qualys import qualys_client
        from was_reports.reporting import report_service
        from was_reports.utils import qualys_config

        captured = datetime(2026, 9, 11, 19, 30, tzinfo=timezone(timedelta(hours=-5)))
        with ExitStack() as stack:
            clock = stack.enter_context(patch.object(report_generator, "datetime"))
            clock.now.side_effect = AssertionError(
                "A supplied report time must not be recaptured."
            )
            intent = stack.enter_context(
                patch.object(
                    report_runs,
                    "claim_qualys_report_creation_by_run_id",
                    return_value=True,
                )
            )
            stack.enter_context(
                patch.object(qualys_config, "load_qualys_credentials_from_environment")
            )
            stack.enter_context(patch.object(qualys_client, "create_qualys_client"))
            stack.enter_context(
                patch.object(
                    report_runs,
                    "get_qualys_report_polling_state_by_id",
                    return_value=report_runs.QualysReportPollingState(),
                )
            )
            touch = stack.enter_context(
                patch.object(report_runs, "touch_report_run_by_id", return_value=True)
            )
            recorder = stack.enter_context(
                patch.object(report_runs, "record_qualys_report_id_by_run_id")
            )
            clearer = stack.enter_context(
                patch.object(report_runs, "clear_qualys_report_id_by_run_id")
            )
            status = stack.enter_context(
                patch.object(report_runs, "record_qualys_report_status_by_run_id")
            )
            generate = stack.enter_context(
                patch.object(
                    report_service,
                    "generate_encrypted_report",
                    return_value=Path("/output/report.pdf"),
                )
            )
            report_generator.generate_production_report(
                stakeholder_tag="TAG",
                resource_root=Path("/resources"),
                workspace_root=Path("/workspace"),
                output_directory=Path("/output"),
                python_executable="python3",
                report_password="test-password",
                report_run_id=7,
                generation_token="owner",
                current_time=captured,
            )
            arguments = generate.call_args.kwargs
            arguments["report_id_recorder"]("xml", "xml-id")
            arguments["report_id_clearer"]("xml", "xml-id")
            arguments["report_status_recorder"]("xml", "COMPLETE")
            self.assertIs(arguments["report_creation_intent_claim"]("xml"), True)
            self.assertEqual(
                arguments["current_time"],
                datetime(2026, 9, 12, 0, 30, tzinfo=timezone.utc),
            )
        intent.assert_called_once_with(7, "xml", generation_token="owner")
        touch.assert_called_once_with(7, generation_token="owner")
        recorder.assert_called_once_with(7, "xml", "xml-id", generation_token="owner")
        clearer.assert_called_once_with(7, "xml", "xml-id", generation_token="owner")
        status.assert_called_once_with(7, "xml", "COMPLETE", generation_token="owner")

    def test_untracked_generation_has_no_database_intent(self) -> None:
        """Keep standalone generation independent of persistent run tracking."""
        # Third-Party Libraries
        from was_reports.qualys import qualys_client
        from was_reports.reporting import report_service
        from was_reports.utils import database, qualys_config

        with ExitStack() as stack:
            connect = stack.enter_context(
                patch.object(
                    database,
                    "connect",
                    side_effect=AssertionError(
                        "No database claim for standalone generation."
                    ),
                )
            )
            stack.enter_context(
                patch.object(qualys_config, "load_qualys_credentials_from_environment")
            )
            stack.enter_context(patch.object(qualys_client, "create_qualys_client"))
            generate = stack.enter_context(
                patch.object(report_service, "generate_encrypted_report")
            )
            report_generator.generate_production_report(
                stakeholder_tag="TAG",
                resource_root=Path("/resources"),
                workspace_root=Path("/workspace"),
                output_directory=Path("/output"),
                python_executable="python3",
                report_password="test-password",
            )
        self.assertIsNone(generate.call_args.kwargs["report_request_key"])
        self.assertIsNone(generate.call_args.kwargs["report_creation_intent_claim"])
        connect.assert_not_called()

    @patch("was_reports.commands.report_generator.resolve_report_password")
    def test_tracked_generation_requires_token_before_password_mutation(
        self, password
    ) -> None:
        """Reject an unfenced tracked invocation before any password write."""
        with self.assertRaises(ValueError):
            report_generator.main(["--tag", "TAG", "--report-run-id", "7"])
        password.assert_not_called()

    @patch("was_reports.commands.report_generator.resolve_report_password")
    @patch(
        "was_reports.data.report_runs.touch_report_run_by_id",
        return_value=False,
    )
    def test_stale_generation_stops_before_password_resolution(
        self, touch, password
    ) -> None:
        """Check the supplied token before generating or changing credentials."""
        with self.assertRaises(operation_lease.OperationLeaseLostError):
            report_generator.main(
                [
                    "--tag",
                    "TAG",
                    "--report-run-id",
                    "7",
                    "--generation-token",
                    "old-token",
                ]
            )
        touch.assert_called_once_with(7, generation_token="old-token")
        password.assert_not_called()

    def test_parse_args_accepts_encrypt_alias(self) -> None:
        """Accept the established encrypt alias at the production boundary."""
        arguments = report_generator.parse_args(
            ["-t", "TEST_TAG", "--encrypt", "password"]
        )

        self.assertEqual(arguments.tag, "TEST_TAG")
        self.assertEqual(arguments.report_password, "password")

    def test_parse_args_accepts_report_run_id(self) -> None:
        """Accept the database run ID used in unique Qualys report names."""
        arguments = report_generator.parse_args(
            ["-t", "TEST_TAG", "--report-run-id", "17"]
        )

        self.assertEqual(arguments.report_run_id, 17)

    def test_parse_args_rejects_removed_legacy_pipeline(self) -> None:
        """Reject attempts to execute the frozen legacy report pipeline."""
        with self.assertRaises(SystemExit):
            report_generator.parse_args(["-t", "TEST_TAG", "--use-legacy-pipeline"])

    def test_resolve_report_password_prefers_argument(self) -> None:
        """Use an explicit password before querying Postgres."""
        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password="from-cli",
        )

        self.assertEqual(password, "from-cli")

    @patch("was_reports.commands.report_generator.lookup_report_password")
    def test_resolve_report_password_reads_postgres(
        self,
        mock_password,
    ) -> None:
        """Read the stored password when no CLI password is supplied."""
        mock_password.return_value = "from-db"

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
        )

        self.assertEqual(password, "from-db")
        mock_password.assert_called_once_with("TEST_TAG")

    @patch("was_reports.commands.report_generator.lookup_report_password")
    def test_resolve_report_password_requires_password(
        self,
        mock_password,
    ) -> None:
        """Fail closed when no report password is available."""
        mock_password.return_value = None

        with self.assertRaises(RuntimeError):
            report_generator.resolve_report_password(
                stakeholder_tag="TEST_TAG",
                report_password=None,
            )

    @patch("was_reports.commands.report_generator.lookup_report_password")
    @patch("was_reports.commands.report_generator.create_report_password")
    def test_resolve_report_password_can_create_missing_password(
        self,
        mock_create_password,
        mock_lookup_password,
    ) -> None:
        """Create a missing stakeholder password when requested."""
        mock_lookup_password.return_value = None
        mock_create_password.return_value = "created-password"

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
            create_missing_password=True,
        )

        self.assertEqual(password, "created-password")
        mock_create_password.assert_called_once_with("TEST_TAG")

    @patch("was_reports.commands.report_generator.rotate_report_password")
    def test_main_can_rotate_password_without_running_report(
        self,
        mock_rotate_password,
    ) -> None:
        """Rotate a stored password without generating a report."""
        exit_code = report_generator.main(["--tag", "TEST_TAG", "--change-password"])

        self.assertEqual(exit_code, 0)
        mock_rotate_password.assert_called_once_with("TEST_TAG")

    def test_validate_stakeholder_tag_rejects_empty_tag(self) -> None:
        """Reject an empty stakeholder tag before external calls."""
        with self.assertRaises(ValueError):
            report_generator.validate_stakeholder_tag(" ")

    @patch("was_reports.commands.report_generator.generate_production_report")
    def test_main_uses_production_pipeline(
        self,
        mock_production_report,
    ) -> None:
        """Always route report generation through the WAS-owned pipeline."""
        exit_code = report_generator.main(
            [
                "-t",
                "TEST_TAG",
                "--encrypt",
                "SecurePassword123!",
                "--resource-root",
                "/WAS_REPORT_RESOURCES",
                "--output-directory",
                "/reports",
                "--workspace-root",
                "/tmp/workspaces",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_production_report.assert_called_once_with(
            stakeholder_tag="TEST_TAG",
            resource_root=Path("/WAS_REPORT_RESOURCES"),
            workspace_root=Path("/tmp/workspaces"),
            output_directory=Path("/reports"),
            python_executable=report_generator.sys.executable,
            report_password="SecurePassword123!",
            report_run_id=None,
            generation_token=None,
            current_time=None,
        )


class OperationLeaseTests(unittest.TestCase):
    """Verify that heartbeat failures stop side effects on the worker thread."""

    def test_initial_ownership_loss_never_enters_operation(self) -> None:
        """Reject a lease that has already been reclaimed."""
        side_effect = Mock()
        with self.assertRaises(operation_lease.OperationLeaseLostError):
            with operation_lease.operation_heartbeat(lambda: False, "test"):
                side_effect()
        side_effect.assert_not_called()

    def test_refresh_exception_is_sticky_and_fail_closed(self) -> None:
        """Do not resume side effects after a transient heartbeat exception."""
        heartbeat = Mock(side_effect=[True, OSError("database unavailable"), True])
        with self.assertRaises(operation_lease.OperationLeaseLostError):
            with operation_lease.operation_heartbeat(heartbeat, "test"):
                with self.assertRaises(operation_lease.OperationLeaseLostError):
                    operation_lease.check_operation_ownership()
                operation_lease.check_operation_ownership()
        self.assertEqual(heartbeat.call_count, 2)
        self.assertIsNone(operation_lease.CURRENT_OWNERSHIP_CHECK.get())

    @patch.object(operation_lease, "heartbeat_seconds", return_value=0.01)
    def test_background_loss_reaches_worker_at_exit(self, interval) -> None:
        """Propagate background rejection rather than merely logging it."""
        rejected = Event()
        calls = []

        def heartbeat() -> bool:
            """Accept acquisition then signal rejection from the heartbeat thread."""
            calls.append(True)
            if len(calls) == 1:
                return True
            rejected.set()
            return False

        with self.assertRaises(operation_lease.OperationLeaseLostError):
            with operation_lease.operation_heartbeat(heartbeat, "test"):
                self.assertTrue(rejected.wait(timeout=2))
        self.assertIsNone(operation_lease.CURRENT_OWNERSHIP_CHECK.get())


if __name__ == "__main__":
    unittest.main()
