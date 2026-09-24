"""Keep capacity subprocesses inside their recorded tracker workload."""

import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from was_mailer import email_reports
from was_reports.commands import batch_runner
from was_reports.data import report_runs
from test_report_runs import FakeConnection
from was_reports.utils.capacity_scope import capacity_tracker_ids


class CapacityScopeTests(unittest.TestCase):
    """Validate scope parsing and generation/delivery boundaries."""

    def setUp(self) -> None:
        """Isolate each test from operator environment settings."""
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def enable_scope(self, encoded_ids: str = "[4]") -> None:
        """Configure a capacity child process with an explicit workload."""
        os.environ.update(
            {
                "WAS_RUN_MODE": "capacity",
                "WAS_DB_NAME": "was_capacity_test",
                "WAS_CAPACITY_TRACKER_IDS": encoded_ids,
            }
        )

    def test_parsing_and_ordinary_mode(self) -> None:
        """Ordinary batches ignore the override, while capacity validates IDs."""
        self.assertIsNone(capacity_tracker_ids())
        os.environ["WAS_CAPACITY_TRACKER_IDS"] = "invalid"
        with self.assertRaises(ValueError):
            capacity_tracker_ids()
        self.enable_scope("[4, 4, 9]")
        self.assertEqual(capacity_tracker_ids(), frozenset({4, 9}))
        self.enable_scope("[]")
        self.assertEqual(capacity_tracker_ids(), frozenset())

    def test_malformed_scope_and_operational_database_rejected(self) -> None:
        """Invalid types and operational targets fail before workload queries."""
        for invalid in ("bad", "null", "{}", "[true]", "[0]", '["4"]', "[-1]"):
            with self.subTest(invalid=invalid):
                self.enable_scope(invalid)
                with self.assertRaises(ValueError):
                    capacity_tracker_ids()
        self.enable_scope()
        del os.environ["WAS_CAPACITY_TRACKER_IDS"]
        with self.assertRaises(ValueError):
            capacity_tracker_ids()
        self.enable_scope()
        os.environ["WAS_DB_NAME"] = "was"
        with self.assertRaises(ValueError):
            capacity_tracker_ids()

    def test_production_saved_scope_requires_batch_identity(self) -> None:
        """Production snapshots require their coordinator UUID, not test settings."""
        os.environ.update({"WAS_RUN_MODE": "production", "WAS_DB_NAME": "was",
                           "WAS_BATCH_TRACKER_IDS": "[4, 9]"})
        with self.assertRaises(ValueError):
            capacity_tracker_ids()
        os.environ["WAS_ANALYST_BATCH_ID"] = "00000000-0000-0000-0000-000000000001"
        self.assertEqual(capacity_tracker_ids(), frozenset({4, 9}))
        for invalid in ("[true]", "[-1]", "null", "bad"):
            os.environ["WAS_BATCH_TRACKER_IDS"] = invalid
            with self.assertRaises(ValueError):
                capacity_tracker_ids()
        os.environ["WAS_BATCH_TRACKER_IDS"] = "[]"
        self.assertEqual(capacity_tracker_ids(), frozenset())

    def test_cross_mode_scopes_are_rejected(self) -> None:
        """Neither scope variable may be used to bypass the other mode's fence."""
        self.enable_scope()
        os.environ["WAS_BATCH_TRACKER_IDS"] = "[9]"
        with self.assertRaises(ValueError):
            capacity_tracker_ids()
        os.environ["WAS_RUN_MODE"] = "production"
        with self.assertRaises(ValueError):
            capacity_tracker_ids()

    def test_generation_excludes_outside_workload(self) -> None:
        """Normally eligible rows outside the manifest cannot be generated."""
        self.enable_scope()
        with patch.object(
            batch_runner,
            "list_ready_report_candidates_from_db",
            return_value=[SimpleNamespace(id=9)],
        ), patch.object(batch_runner, "create_report_run_for_tracker") as create:
            result = batch_runner.run_recent_scan_reports(
                resource_root="/unused",
                python_executable="python",
                retry_ready_emails=False,
            )
        self.assertEqual(result.candidates, 0)
        create.assert_not_called()

    def test_delivery_excludes_outside_and_standalone_runs(self) -> None:
        """Delivery keeps its normal claim policy and only sends manifest rows."""
        self.enable_scope()
        ready = [
            SimpleNamespace(id=8, source_tracker_id=4, delivery_purpose="customer"),
            SimpleNamespace(id=9, source_tracker_id=5, delivery_purpose="customer"),
            SimpleNamespace(id=10, source_tracker_id=4, delivery_purpose="standalone"),
        ]
        with patch.object(
            email_reports,
            "list_report_runs_ready_for_email_from_db",
            return_value=ready,
        ), patch.object(
            email_reports, "send_report_run_email", return_value="receipt"
        ) as send:
            self.assertEqual(
                email_reports.send_ready_report_emails("sender@example.gov"), 1
            )
        send.assert_called_once_with(
            report_run_id=8,
            source_email="sender@example.gov",
            override_recipients=None,
            dry_run=False,
            include_previous_failure=False,
        )

    def test_delivery_race_keeps_unsuccessful_claim_unsent(self) -> None:
        """An atomic claim rejecting sent or held state is never counted as sent."""
        self.enable_scope()
        with patch.object(
            email_reports,
            "list_report_runs_ready_for_email_from_db",
            return_value=[SimpleNamespace(id=8, source_tracker_id=4)],
        ), patch.object(
            email_reports, "send_report_run_email", return_value=None
        ) as send:
            self.assertEqual(
                email_reports.send_ready_report_emails("sender@example.gov"), 0
            )
        self.assertNotIn("allow_held", send.call_args.kwargs)

    def test_safe_retry_fences_uncertain_and_delivered_states_atomically(self) -> None:
        """Apply safety conditions in the retry UPDATE, not a stale prior read."""
        for returned_row in (None, (8, "TAG", "running")):
            with self.subTest(claimed=returned_row is not None):
                connection = FakeConnection(row=returned_row)
                result = report_runs.retry_failed_report_run_for_tracker(
                    4, connection, safe_only=True,
                )
                query = connection.cursor_instance.query
                self.assertIn("emailed_at IS NULL", query)
                self.assertIn("IN ('pending', 'failed')", query)
                self.assertIn("QualysReportCreationUncertainError", query)
                self.assertIn("creation outcome is uncertain", query)
                self.assertIs(connection.cursor_instance.parameters[-1], True)
                self.assertEqual(result is not None, returned_row is not None)

    def test_capacity_entrypoints_do_not_recover_unrelated_operations(self) -> None:
        """Coordinator safety checks must not be bypassed by global stale recovery."""
        self.enable_scope()
        with patch.object(email_reports, "configure_logging"), patch.object(
            email_reports, "recover_stale_report_operations_in_db",
        ) as recover, patch.object(email_reports, "send_ready_report_emails"):
            email_reports.main(["--all-ready", "--source-email", "sender@example.gov"])
            recover.assert_not_called()
        with patch.object(batch_runner, "configure_logging"), patch.object(
            batch_runner, "recover_stale_report_operations_in_db",
        ) as recover, patch.object(
            batch_runner, "run_recent_scan_reports",
            return_value=batch_runner.BatchExecutionSummary(0, 0, 0, 0),
        ):
            self.assertEqual(batch_runner.main(["--recent-scans", "--skip-tracker-refresh"]), 0)
            recover.assert_not_called()

    def test_continuation_retries_only_scoped_failed_generation(self) -> None:
        """Never retry unrelated manual rows or create a second report run."""
        self.enable_scope()
        os.environ["WAS_CAPACITY_CONTINUATION"] = "1"
        failed = SimpleNamespace(id=4, tag="TAG", report_run_status="failed", report_run_id=8)
        outside = SimpleNamespace(id=9, tag="OUTSIDE", report_run_status="failed")
        manual = SimpleNamespace(id=5, tag="MANUAL", report_run_status=None)
        with patch.object(
            batch_runner, "list_ready_report_candidates_from_db",
            side_effect=[[], [failed, outside, manual]],
        ), patch.object(batch_runner, "create_report_run_for_tracker") as create, patch.object(
            batch_runner, "retry_failed_report_run_for_tracker_by_id", return_value=None,
        ) as retry, patch.object(batch_runner, "summarize_candidates"), patch.object(
            batch_runner, "log_preflight_summary",
        ):
            result = batch_runner.run_recent_scan_reports(
                resource_root="/unused", python_executable="python", retry_ready_emails=False,
            )
        retry.assert_called_once_with(4, safe_only=True)
        create.assert_not_called()
        self.assertEqual(result.candidates, 1)
