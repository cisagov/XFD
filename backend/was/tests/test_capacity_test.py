"""Isolation and orchestration regression tests without external services."""

import os
import json
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from was_reports.commands import capacity_test


class CapacityTestTests(unittest.TestCase):
    """Verify unsafe identities and previews cannot start report work."""

    def test_start_defaults_to_new_identity_and_auto_count(self):
        """A normal start needs no hand-crafted run ID or workload count."""
        first = capacity_test.parse_args(["--test-recipients", "analyst@example.gov"])
        second = capacity_test.parse_args(["--test-recipients", "analyst@example.gov",
                                           "--expected-candidates", "auto"])
        self.assertNotEqual(first.run_id, second.run_id)
        self.assertIsNone(first.expected_candidates)
        self.assertIsNone(second.expected_candidates)

    def test_continuation_selection_validates_database_and_manifest(self):
        """Latest selection uses the database and checks saved tracker identity."""
        arguments = self.arguments()
        arguments.continue_latest = True
        parent_id = "ccce3a43-cd47-4a26-99e9-cadcc1094266"
        cursor = MagicMock()
        cursor.fetchone.return_value = (parent_id,)
        cursor.fetchall.return_value = [(1, "test")]
        with TemporaryDirectory() as directory:
            manifest_directory = Path(directory) / parent_id
            manifest_directory.mkdir()
            manifest_directory.joinpath("workload.json").write_text(json.dumps({
                "run_id": parent_id, "candidate_count": 1, "candidate_ids": [1],
                "candidates": [{"tracker_id": 1, "tag": "test", "template": "Standard"}],
            }))
            self.assertEqual(capacity_test.load_continuation(cursor, arguments, Path(directory)), [1])
            self.assertIn("ORDER BY started_at", cursor.execute.call_args_list[0].args[0])
            self.assertEqual(arguments.continuation_manifest["parent_run_id"], parent_id)
            cursor.fetchall.return_value = [(1, "other")]
            with self.assertRaisesRegex(ValueError, "does not match"):
                capacity_test.load_continuation(cursor, arguments, Path(directory))

    def test_continuation_rejects_missing_manifest(self):
        """A trial interrupted before selection cannot be continued blindly."""
        arguments = self.arguments()
        arguments.continue_latest = True
        cursor = MagicMock()
        cursor.fetchone.return_value = ("ccce3a43-cd47-4a26-99e9-cadcc1094266",)
        with TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "no workload manifest"):
            capacity_test.load_continuation(cursor, arguments, Path(directory))

    def test_empty_auto_workload_is_successful_noop(self):
        """An empty refreshed workload is not an aborted run or a capacity proof."""
        arguments = self.arguments(apply=True)
        with TemporaryDirectory() as directory, patch(
            "was_reports.utils.capacity_telemetry.resource_monitor", return_value=nullcontext()
        ), patch("was_reports.reporting.analyst_summaries.start_batch"), patch(
            "was_reports.reporting.analyst_summaries.finish_batch"
        ), patch.object(capacity_test, "list_ready_report_candidates_from_db", return_value=[]), patch.object(
            capacity_test, "run_phase", return_value=SimpleNamespace(returncode=0)
        ) as phases, patch.object(capacity_test.subprocess, "Popen") as workers:
            self.assertEqual(capacity_test.execute_trial(arguments, "analyst@example.gov", Path(directory)), 0)
            workers.assert_not_called()
            self.assertFalse(any(call.args[0][0] == "was-mailer" for call in phases.call_args_list))
            result = json.loads(Path(directory, "result.json").read_text())
            self.assertFalse(result["capacity_pass"])
            self.assertTrue(result["workflow_completed"])

    def test_continuation_completes_without_new_capacity_proof(self):
        """Cumulative inherited results can complete a continuation, never a benchmark."""
        result, status = self.execute_mock_trial(sent=1, continuing=True)
        self.assertEqual(status, 0)
        self.assertFalse(result["capacity_pass"])
        self.assertEqual(result["inherited_sent"], 1)

    def test_partial_failure_still_reports_persisted_delivery_counts(self):
        """An interrupted phase must retain successful sends already in the database."""
        result, status = self.execute_mock_trial(sent=1, delivery_error=True)
        self.assertEqual(status, -1)
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["remaining"], 0)
        self.assertTrue(result["counts_available"])
        self.assertEqual(result["execution_error"], "TimeoutError")

    def test_continuation_counts_held_and_uncertain_as_blocked(self):
        """Safe failed work is retryable, while uncertain sends/creates remain held."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            (1, 11, "failed", "pending", None, None, "RenderFailure"),
            (2, 12, "failed", "pending", None, None, "creation outcome is uncertain"),
            (3, 13, "completed", "held", "pdf", None, None),
            (4, 14, "completed", "sent", "notification", "original-time", None),
        ]
        with patch.object(capacity_test, "connect", return_value=connection), patch(
            "was_reports.reporting.analyst_summaries.record_report_attempt"
        ) as record:
            counts = capacity_test.continuation_status([1, 2, 3, 4], "new-batch")
        self.assertEqual(counts["blocked"], 2)
        self.assertEqual(counts["remaining"], 3)
        self.assertEqual(counts["sent"], 1)
        self.assertEqual(record.call_args_list[0].kwargs["error"], None)
        self.assertIn("sent_recorded_at=runs.emailed_at", cursor.execute.call_args.args[0])

    @patch.dict(os.environ, {"WAS_DB_NAME": "was_capacity_trial",
                             "WAS_DB_USERNAME": "was_capacity_runner"})
    def test_continue_guard_allows_only_manifest_pending_reports(self):
        """Continuation's pending-report exception remains bounded to saved IDs."""
        arguments = self.arguments()
        arguments.continue_latest = True
        connection = self.connection()
        with patch.object(capacity_test, "connect", return_value=connection), patch.object(
            capacity_test, "load_continuation", return_value=[1, 2]
        ):
            self.assertIs(capacity_test.guard_database(arguments), connection)
        query = connection.cursor.return_value.__enter__.return_value.execute.call_args
        self.assertIn("source_tracker_id,0)=ANY", query.args[0])
        self.assertEqual(query.args[1], ([1, 2],))

    def test_test_settings_are_exclusive_and_restored(self):
        """Map all settings for child inheritance without changing normal settings."""
        suffixes = ("HOST", "NAME", "USERNAME", "PASSWORD", "PORT", "SSLMODE",
                    "CONNECT_TIMEOUT_SECONDS")
        environment = {"TEST_WAS_DB_" + suffix: "test-" + suffix for suffix in suffixes}
        environment["WAS_DB_NAME"] = "operational"
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(ValueError):
                with capacity_test.capacity_database_environment():
                    for suffix in suffixes:
                        self.assertEqual(os.environ["WAS_DB_" + suffix], "test-" + suffix)
                    raise ValueError("Simulated trial failure")
            self.assertEqual(dict(os.environ), environment)

    def test_missing_test_setting_never_falls_back(self):
        """Reject each absent test field even when operational fields exist."""
        suffixes = ("HOST", "NAME", "USERNAME", "PASSWORD", "PORT", "SSLMODE",
                    "CONNECT_TIMEOUT_SECONDS")
        for missing in suffixes:
            environment = {"WAS_DB_" + suffix: "operational" for suffix in suffixes}
            environment.update({"TEST_WAS_DB_" + suffix: "test" for suffix in suffixes
                                if suffix != missing})
            with self.subTest(missing=missing), patch.dict(os.environ, environment, clear=True):
                with self.assertRaises(RuntimeError):
                    with capacity_test.capacity_database_environment():
                        self.fail("Incomplete test settings must not execute")
                self.assertEqual(dict(os.environ), environment)

    def test_main_selects_test_database_before_any_trial_work(self):
        """Select test settings before guards, recipient queries, or workers."""
        suffixes = ("HOST", "NAME", "USERNAME", "PASSWORD", "PORT", "SSLMODE",
                    "CONNECT_TIMEOUT_SECONDS")
        environment = {"TEST_WAS_DB_" + suffix: "test-" + suffix for suffix in suffixes}
        environment["WAS_DB_NAME"] = "operational"

        def inspect_environment(arguments):
            """Check the environment visible to the entire trial."""
            self.assertEqual(os.environ["WAS_DB_NAME"], "test-NAME")
            return 0

        with patch.dict(os.environ, environment, clear=True), patch.object(
            capacity_test, "load_env_file"
        ), patch.object(capacity_test, "parse_args", return_value=self.arguments()), patch.object(
            capacity_test, "run_capacity", side_effect=inspect_environment
        ):
            self.assertEqual(capacity_test.main([]), 0)
            self.assertEqual(os.environ["WAS_DB_NAME"], "operational")

    def arguments(self, apply=False):
        """Return a deliberate trial with an explicit workload and recipient."""
        values = ["--run-id", "213459b4-6390-4f10-ae39-b9b183320e96",
                  "--workload-label", "baseline-600", "--test-recipients",
                  "analyst@example.gov"]
        if apply:
            values.append("--apply")
        return capacity_test.parse_args(values)

    def connection(self, identity=None, existing=False, pending=False):
        """Build read-only cursor results for a valid isolated clone."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            identity or ("was_capacity_trial", "was_capacity_runner", False, False, False),
            (existing,), (pending,),
        ]
        return connection

    @patch.dict(os.environ, {"WAS_DB_NAME": "production", "WAS_DB_USERNAME": "production"})
    @patch.object(capacity_test, "connect")
    def test_production_configuration_rejected_before_connection(self, connect):
        """Reject production configuration before any database access."""
        with self.assertRaises(ValueError):
            capacity_test.guard_database(self.arguments())
        connect.assert_not_called()

    @patch.dict(os.environ, {"WAS_DB_NAME": "was_capacity_trial",
                             "WAS_DB_USERNAME": "was_capacity_runner"})
    def test_live_identity_privileges_and_prior_work_rejected(self):
        """Check the actual endpoint, unsafe privileges, and leftover deliveries."""
        cases = [
            self.connection(identity=("production", "was_capacity_runner", False, False, False)),
            self.connection(identity=("was_capacity_trial", "was_capacity_runner", True, False, False)),
            self.connection(existing=True),
            self.connection(pending=True),
        ]
        for connection in cases:
            with self.subTest(connection=connection), patch.object(
                capacity_test, "connect", return_value=connection
            ):
                with self.assertRaises(ValueError):
                    capacity_test.guard_database(self.arguments())
                connection.close.assert_called_once()

    @patch.object(capacity_test, "execute_trial")
    @patch.object(capacity_test, "approved_analyst_recipients", return_value=["analyst@example.gov"])
    @patch.object(capacity_test, "guard_database")
    def test_default_preflight_never_executes_trial(self, guard, recipients, execute):
        """Read-only preflight validates recipients but never refreshes or sends."""
        arguments = self.arguments()
        with patch.object(capacity_test, "parse_args", return_value=arguments), patch.object(
            capacity_test, "capacity_database_environment", return_value=nullcontext()
        ):
            self.assertEqual(capacity_test.main([]), 0)
        execute.assert_not_called()
        guard.return_value.close.assert_called_once()

    @patch.dict(os.environ, {"WAS_DB_NAME": "was_capacity_trial",
                             "WAS_DB_USERNAME": "was_capacity_runner"})
    def test_concurrent_apply_rejected(self):
        """A second applied trial cannot share the same workload clone."""
        connection = self.connection()
        with patch.object(capacity_test, "connect", return_value=connection):
            with self.assertRaisesRegex(ValueError, "Another capacity"):
                capacity_test.guard_database(self.arguments(apply=True))

    def test_worker_boundaries(self):
        """Disallow invalid worker counts without launching any subprocesses."""
        for worker_count in (0, 31):
            with self.assertRaises(SystemExit):
                capacity_test.parse_args([
                    "--run-id", "213459b4-6390-4f10-ae39-b9b183320e96",
                    "--workload-label", "baseline", "--test-recipients", "test@example.gov",
                    "--workers", str(worker_count),
                ])

    def test_workload_mismatch_prevents_workers_and_marks_failed(self):
        """A refresh count mismatch must not generate or deliver customer reports."""
        arguments = self.arguments(apply=True)
        arguments.expected_candidates = 600
        with TemporaryDirectory() as directory, patch(
            "was_reports.utils.capacity_telemetry.resource_monitor", return_value=nullcontext()
        ), patch("was_reports.reporting.analyst_summaries.start_batch"), patch(
            "was_reports.reporting.analyst_summaries.finish_batch"
        ) as finish, patch.object(capacity_test, "list_ready_report_candidates_from_db",
                                  return_value=[]), patch.object(
            capacity_test, "run_phase", return_value=SimpleNamespace(returncode=0)
        ), patch.object(capacity_test.subprocess, "Popen") as workers:
            with self.assertRaisesRegex(ValueError, "candidate count"):
                capacity_test.execute_trial(arguments, "analyst@example.gov", Path(directory))
            workers.assert_not_called()
            finish.assert_called_once_with(arguments.run_id, "failed")
            self.assertTrue((Path(directory) / "result.json").exists())

    def test_success_requires_complete_durable_deliveries(self):
        """Exit-zero workers alone cannot pass a capacity trial with missing sends."""
        result, status = self.execute_mock_trial(sent=0)
        self.assertEqual(status, 1)
        self.assertFalse(result["capacity_pass"])

    def test_recovered_worker_error_passes_capacity(self):
        """A retry that completes every delivery still satisfies capacity."""
        result, status = self.execute_mock_trial(sent=1, worker_status=1)
        self.assertEqual(status, 0)
        self.assertTrue(result["capacity_pass"])
        self.assertFalse(result["workflow_clean"])

    def test_summary_failure_does_not_change_capacity(self):
        """Administrative summary failure is separate from report completion."""
        result, status = self.execute_mock_trial(sent=1, summary_status=1)
        self.assertEqual(status, 1)
        self.assertTrue(result["capacity_pass"])
        self.assertFalse(result["summary_succeeded"])

    def test_wrong_workload_ids_cannot_pass(self):
        """Equal counts from different trackers cannot satisfy the snapshot."""
        result, status = self.execute_mock_trial(sent=1, tracker_ids=[2])
        self.assertEqual(status, 1)
        self.assertFalse(result["capacity_pass"])

    @patch.object(capacity_test.os, "killpg", side_effect=ProcessLookupError)
    def test_cleanup_tolerates_process_exit_race(self, killpg):
        """A child exiting before group termination must not mask trial results."""
        process = MagicMock()
        capacity_test.stop_process(process)
        process.wait.assert_called_once_with(timeout=30)

    @patch.object(capacity_test, "stop_process")
    @patch.object(capacity_test.subprocess, "Popen")
    def test_phase_cancellation_stops_descendants(self, popen, stop):
        """Cancelled refresh and delivery phases terminate their process groups."""
        popen.return_value.wait.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            capacity_test.run_phase(["example"], check=True, timeout=1)
        stop.assert_called_once_with(popen.return_value)

    def execute_mock_trial(self, sent, worker_status=0, summary_status=0,
                           tracker_ids=None, continuing=False, delivery_error=False):
        """Exercise real orchestration with bounded process and database mocks."""
        arguments = self.arguments(apply=True)
        arguments.workers = 1
        arguments.expected_candidates = 1
        if continuing:
            arguments.continuation_manifest = {
                "run_id": "ccce3a43-cd47-4a26-99e9-cadcc1094266", "candidate_count": 1,
                "candidate_ids": [1], "candidates": [{"tracker_id": 1, "tag": "test"}],
                "parent_run_id": "ccce3a43-cd47-4a26-99e9-cadcc1094266",
            }
        worker = MagicMock()
        worker.wait.return_value = worker_status
        worker.poll.return_value = 0
        candidate = SimpleNamespace(id=1, tag="test", template="Standard")
        counts = {"attempted": 1, "pdfs_generated": 1,
                  "notifications_generated": 0, "sent": sent,
                  "tracker_ids": [1] if tracker_ids is None else tracker_ids}
        phase_results = [SimpleNamespace(returncode=0)] * (2 if continuing else 3)
        phase_results.append(SimpleNamespace(returncode=summary_status))
        if delivery_error:
            phase_results[-2] = TimeoutError("Simulated delivery interruption")
        with TemporaryDirectory() as directory, patch(
            "was_reports.utils.capacity_telemetry.resource_monitor", return_value=nullcontext()
        ), patch("was_reports.reporting.analyst_summaries.start_batch"), patch(
            "was_reports.reporting.analyst_summaries.finish_batch"
        ), patch.object(capacity_test, "list_ready_report_candidates_from_db",
                        return_value=[candidate]), patch.object(
            capacity_test, "trial_counts", return_value=counts
        ), patch.object(capacity_test, "continuation_status", return_value=counts), patch.object(
            capacity_test, "run_phase", side_effect=phase_results
        ) as phases, patch.object(
            capacity_test.subprocess, "Popen", return_value=worker
        ) as workers:
            try:
                status = capacity_test.execute_trial(
                    arguments, "analyst@example.gov", Path(directory))
            except TimeoutError:
                if not delivery_error:
                    raise
                status = -1
            self.assertIn("--test-recipients", workers.call_args.args[0])
            if continuing:
                self.assertFalse(any("was_reports.commands.update_tracker_cli" in call.args[0]
                                     for call in phases.call_args_list))
            result = json.loads((Path(directory) / "result.json").read_text())
            return result, status


if __name__ == "__main__":
    unittest.main()
