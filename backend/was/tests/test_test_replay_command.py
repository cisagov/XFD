"""Safety regressions for analyst-only replay orchestration."""

import argparse
from contextlib import nullcontext
import unittest
from unittest.mock import patch

from was_reports.commands import test_replay
from was_reports.data.report_runs import ReportRun
from was_reports.data.test_replay import ReplayCandidate


class TestReplayCommandTests(unittest.TestCase):
    """Keep previews read-only and customer execution history untouched."""

    def setUp(self):
        """Build one archived PDF and one explicitly selected manual."""
        self.pdf = ReplayCandidate(
            10, "TEST", "resend", 20, "/output/a.pdf", 30, "Test", None
        )
        self.manual = ReplayCandidate(
            11, "TEST2", "manual", 21, None, 31, "Test2", None
        )
        self.arguments = argparse.Namespace(
            replay_id="00000000-0000-0000-0000-000000000001",
            source_email="sender@example.gov",
            resource_root="/resources",
            python_executable="python",
            output_directory="/output",
            staging_directory="/tmp",
            storage_mode="local",
        )

    @patch.object(test_replay, "execute_candidate")
    @patch.object(test_replay, "list_replay_candidates")
    @patch.object(
        test_replay, "approved_analyst_recipients", return_value=["analyst@example.gov"]
    )
    def test_preview_never_executes(self, approved, candidates, execute):
        """Default preview only validates recipients and reads candidates."""
        candidates.return_value = [self.pdf]
        self.assertEqual(
            test_replay.main(["--test-recipients", "analyst@example.gov"]), 0
        )
        execute.assert_not_called()

    def test_apply_requires_explicit_selection_and_uuid(self):
        """An apply switch alone cannot resend a moving date window."""
        for extra in (
            ["--apply"],
            ["--apply", "--replay-id", self.arguments.replay_id],
        ):
            with self.assertRaises(SystemExit):
                test_replay.parse_args(
                    ["--test-recipients", "analyst@example.gov"] + extra
                )

    @patch.object(test_replay, "execute_candidate")
    @patch.object(test_replay, "list_replay_candidates")
    @patch.object(
        test_replay, "approved_analyst_recipients", return_value=["analyst@example.gov"]
    )
    def test_apply_selects_only_explicit_pdf_ids(self, approved, candidates, execute):
        """An unrelated PDF in the window is never implicitly resent."""
        other = ReplayCandidate(
            12, "OTHER", "resend", 22, "/output/b.pdf", 32, "Other", None
        )
        candidates.return_value = [self.pdf, other]
        result = test_replay.main(
            [
                "--test-recipients",
                "analyst@example.gov",
                "--apply",
                "--replay-id",
                self.arguments.replay_id,
                "--report-run-ids",
                "20",
                "--source-email",
                "sender@example.gov",
            ]
        )
        self.assertEqual(result, 0)
        self.assertEqual(execute.call_count, 1)
        self.assertEqual(execute.call_args.args[0], self.pdf)
        self.assertFalse(candidates.call_args.kwargs["include_all_manual"])

    @patch.object(
        test_replay,
        "execute_candidate",
        side_effect=test_replay.OperationCancelledError(),
    )
    @patch.object(test_replay, "list_replay_candidates")
    @patch.object(
        test_replay, "approved_analyst_recipients", return_value=["analyst@example.gov"]
    )
    def test_cancellation_stops_replay(self, approved, candidates, execute):
        """Cancellation does not silently advance to another replay item."""
        candidates.return_value = [self.pdf]
        with self.assertRaises(test_replay.OperationCancelledError):
            test_replay.main(
                [
                    "--test-recipients",
                    "analyst@example.gov",
                    "--apply",
                    "--replay-id",
                    self.arguments.replay_id,
                    "--report-run-ids",
                    "20",
                    "--source-email",
                    "sender@example.gov",
                ]
            )

    @patch.object(test_replay, "execute_candidate")
    @patch.object(test_replay, "list_replay_candidates")
    @patch.object(
        test_replay, "approved_analyst_recipients", return_value=["analyst@example.gov"]
    )
    def test_ineligible_explicit_ids_fail_before_execution(
        self, approved, candidates, execute
    ):
        """A stale or incorrect selection cannot silently become partial work."""
        candidates.return_value = [self.pdf]
        with self.assertRaises(ValueError):
            test_replay.main(
                [
                    "--test-recipients",
                    "analyst@example.gov",
                    "--manual-tracker-ids",
                    "999",
                ]
            )
        execute.assert_not_called()

    @patch.object(test_replay, "send_report_run_email")
    @patch.object(test_replay, "generate_report_output")
    @patch.object(test_replay, "reserve_replay_run")
    def test_resend_reuses_child_pdf_only(self, reserve, generate, send):
        """Resends neither regenerate nor send the original customer run."""
        reserve.return_value = (ReportRun(99, "TEST", "completed"), True)
        self.assertTrue(
            test_replay.execute_candidate(
                self.pdf, self.arguments, "analyst@example.gov"
            )
        )
        generate.assert_not_called()
        self.assertEqual(send.call_args.kwargs["report_run_id"], 99)
        self.assertEqual(send.call_args.kwargs["delivery_purpose"], "analyst")
        self.assertTrue(send.call_args.kwargs["preserve_customer_template"])
        self.assertEqual(
            send.call_args.kwargs["override_recipients"], "analyst@example.gov"
        )

    @patch.object(test_replay, "send_report_run_email")
    @patch.object(test_replay, "reserve_replay_run")
    def test_reserved_run_is_never_sent_again(self, reserve, send):
        """Reusing the operation UUID cannot retry ambiguous email sends."""
        reserve.return_value = (ReportRun(99, "TEST", "completed"), False)
        self.assertFalse(
            test_replay.execute_candidate(
                self.pdf, self.arguments, "analyst@example.gov"
            )
        )
        send.assert_not_called()

    @patch.object(test_replay, "send_report_run_email")
    @patch.object(test_replay, "complete_report_run_by_id")
    @patch.object(test_replay, "operation_heartbeat", return_value=nullcontext())
    @patch.object(test_replay, "generate_report_output", return_value="/output/new.pdf")
    @patch.object(test_replay, "reserve_replay_run")
    def test_manual_generation_uses_new_claim_only(
        self, reserve, generate, heartbeat, complete, send
    ):
        """Manual retries keep original run and password unchanged."""
        reserve.return_value = (
            ReportRun(99, "TEST2", "running", generation_token="token"),
            True,
        )
        self.assertTrue(
            test_replay.execute_candidate(
                self.manual, self.arguments, "analyst@example.gov"
            )
        )
        self.assertEqual(generate.call_args.kwargs["report_run_id"], 99)
        self.assertFalse(generate.call_args.kwargs["create_missing_password"])
        self.assertFalse(generate.call_args.kwargs["allow_tag_lookup"])
        self.assertEqual(complete.call_args.args, (99,))

    @patch.object(test_replay, "send_report_run_email")
    @patch.object(test_replay, "record_generation_failure")
    @patch.object(test_replay, "operation_heartbeat", return_value=nullcontext())
    @patch.object(test_replay, "generate_report_output", side_effect=TimeoutError())
    @patch.object(test_replay, "reserve_replay_run")
    def test_generation_failure_does_not_send(
        self, reserve, generate, heartbeat, failure, send
    ):
        """Only the isolated child receives generation failure status."""
        child = ReportRun(99, "TEST2", "running", generation_token="token")
        reserve.return_value = (child, True)
        with self.assertRaises(TimeoutError):
            test_replay.execute_candidate(
                self.manual, self.arguments, "analyst@example.gov"
            )
        self.assertEqual(failure.call_args.args[0], child)
        send.assert_not_called()
