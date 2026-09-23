"""Combined analyst-summary orchestration without database or SES access."""

from contextlib import ExitStack, nullcontext
from datetime import date
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from was_reports.commands import batch_runner, update_tracker_cli
from was_reports.data.daily_report_tracker import TrackerReportCandidate
from was_reports.data.report_runs import ReportRun
from was_reports import reporting


class BatchSummaryOrchestrationTests(unittest.TestCase):
    """Validate shared identity, failure accounting, and notification suppression."""

    def setUp(self) -> None:
        """Replace only external services and the new reporting persistence boundary."""
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.summaries = MagicMock()
        self.stack.enter_context(patch.dict(
            sys.modules, {"was_reports.reporting.analyst_summaries": self.summaries}
        ))
        self.stack.enter_context(patch.object(
            reporting, "analyst_summaries", self.summaries, create=True
        ))
        self.stack.enter_context(patch.dict(os.environ, {}, clear=False))
        os.environ.pop("WAS_ANALYST_BATCH_ID", None)

    def prepare_report(self, failure: bool = False) -> None:
        """Prepare a claimed report with deterministic mocked external boundaries."""
        candidate = TrackerReportCandidate(9, "TAG", date(2026, 9, 23), 1, 1,
                                           template="Results")
        mocked = {
            "list_ready_report_candidates_from_db": [candidate],
            "create_report_run_for_tracker": ReportRun(7, "TAG", "running", "token"),
            "generate_report_output": "/output/TAG_report_2026-09-23.pdf",
            "complete_report_run_by_id": None,
            "record_generation_failure": None,
            "send_report_run_email": "ses-message",
            "operation_heartbeat": nullcontext(),
        }
        for name, value in mocked.items():
            handle = self.stack.enter_context(patch.object(batch_runner, name, return_value=value))
            if name == "generate_report_output" and failure:
                handle.side_effect = RuntimeError("private payload must not reach summaries")

    def run_reports(self, **options):
        """Run an isolated single-worker batch using approved summary recipients."""
        arguments = dict(
            resource_root="/resources", python_executable="python", storage_mode="local",
            send_email=True, send_assignee_digests=True, source_email="reports@example.gov",
            test_recipients="analyst@example.gov", retry_ready_emails=False,
            analyst_batch_id="shared-batch",
        )
        arguments.update(options)
        return batch_runner.run_recent_scan_reports(**arguments)

    def test_direct_batch_sends_two_combined_summaries_and_one_attempt(self) -> None:
        """Both phases share ID and test-recipient override, with one attempt record."""
        self.prepare_report()
        result = self.run_reports()
        self.assertEqual((result.generated, result.sent), (1, 1))
        self.summaries.send_tracker_summary.assert_called_once_with(
            "shared-batch", candidate_ids=[9], source_email="reports@example.gov",
            override_recipients="analyst@example.gov",
        )
        self.summaries.send_batch_summary.assert_called_once_with(
            "shared-batch", source_email="reports@example.gov",
            override_recipients="analyst@example.gov",
        )
        arguments = self.summaries.record_report_attempt.call_args
        self.assertEqual(arguments.args, ("shared-batch", 9))
        self.assertTrue(arguments.kwargs["generated"])
        self.assertTrue(arguments.kwargs["sent"])
        self.assertIsNone(arguments.kwargs["error"])

    def test_generation_failure_is_recorded_before_final_summary(self) -> None:
        """A failed attempt remains visible even when stop-on-error aborts the batch."""
        self.prepare_report(failure=True)
        with self.assertRaises(RuntimeError):
            self.run_reports(continue_on_error=False)
        attempt = self.summaries.record_report_attempt.call_args.kwargs
        self.assertEqual(attempt["error"], "RuntimeError")
        self.assertFalse(attempt["generated"])
        self.assertFalse(attempt["sent"])
        self.summaries.send_batch_summary.assert_called_once()

    def test_worker_records_attempt_without_sending_summary(self) -> None:
        """Parallel workers leave both notification phases to the coordinator."""
        self.prepare_report()
        self.run_reports(send_assignee_digests=False)
        self.summaries.record_report_attempt.assert_called_once()
        self.summaries.send_tracker_summary.assert_not_called()
        self.summaries.send_batch_summary.assert_not_called()

    def test_email_failure_keeps_generated_result_and_safe_error(self) -> None:
        """Generated PDFs remain counted when email delivery fails afterward."""
        self.prepare_report()
        with patch.object(batch_runner, "send_report_run_email",
                          side_effect=ValueError("private delivery payload")):
            result = self.run_reports()
        self.assertEqual((result.generated, result.sent, result.failed), (1, 0, 1))
        attempt = self.summaries.record_report_attempt.call_args.kwargs
        self.assertTrue(attempt["generated"])
        self.assertFalse(attempt["sent"])
        self.assertEqual(attempt["error"], "ValueError")

    def test_lost_claim_does_not_create_attempt(self) -> None:
        """A candidate claimed by another worker is not this worker's attempt."""
        self.prepare_report()
        with patch.object(batch_runner, "create_report_run_for_tracker", return_value=None):
            self.run_reports(send_assignee_digests=False)
        self.summaries.record_report_attempt.assert_not_called()

    def test_dry_run_never_records_or_sends_summary(self) -> None:
        """Dry-run email mode does not mutate summary telemetry or send notifications."""
        self.prepare_report()
        self.run_reports(dry_run_email=True)
        self.assertEqual(self.summaries.mock_calls, [])

    def test_tracker_logged_errors_are_counted_without_message_capture(self) -> None:
        """Record elapsed tracker work and nonfatal errors without sensitive content."""
        def refresh(**arguments):
            """Simulate a nonfatal refresh error with confidential log content."""
            logging.getLogger("was_reports.tracker.service").error("private tracker payload")
            return 3

        with patch.object(update_tracker_cli, "create_qualys_client"), \
                patch.object(update_tracker_cli, "refresh_daily_tracker", side_effect=refresh):
            update_tracker_cli.run_update_tracker(False, analyst_batch_id="shared-batch")
        self.summaries.record_tracker_result.assert_called_once()
        self.assertEqual(self.summaries.record_tracker_result.call_args.kwargs["error"],
                         "TrackerLoggedErrors_1")
        self.assertEqual(self.summaries.record_tracker_result.call_args.kwargs["rows_updated"], 3)
        self.assertNotIn("private tracker payload", str(self.summaries.mock_calls))

    def test_tracker_preflight_does_not_start_or_record_batch(self) -> None:
        """An ambient batch ID never changes read-only diagnostic behavior."""
        with patch.object(update_tracker_cli, "create_qualys_client"), \
                patch.object(update_tracker_cli, "refresh_daily_tracker"):
            update_tracker_cli.run_update_tracker(
                False, preflight_only=True, analyst_batch_id="shared-batch"
            )
        self.assertEqual(self.summaries.mock_calls, [])

    def test_tracker_fatal_error_is_recorded_and_reraised(self) -> None:
        """Tracker failures retain safe phase context and cannot begin generation."""
        with patch.object(update_tracker_cli, "create_qualys_client"), \
                patch.object(update_tracker_cli, "refresh_daily_tracker",
                             side_effect=RuntimeError("private tracker response")):
            with self.assertRaises(RuntimeError):
                update_tracker_cli.run_update_tracker(False, analyst_batch_id="shared-batch")
        self.assertEqual(self.summaries.record_tracker_result.call_args.kwargs["error"],
                         "RuntimeError")
        self.assertIsNone(self.summaries.record_tracker_result.call_args.kwargs["rows_updated"])


if __name__ == "__main__":
    unittest.main()
