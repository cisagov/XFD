"""Tests for the explicit manual report recovery command."""

# Standard Python Libraries
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import recover_manual_reports


def check(tracker_id: int, eligible: bool = True) -> SimpleNamespace:
    """Return a small recovery-check result."""
    return SimpleNamespace(
        tracker_id=tracker_id,
        eligible=eligible,
        reason="eligible" if eligible else "email is held",
        tag="TAG{}".format(tracker_id),
        report_run_id=tracker_id + 100,
        cause="password-validation",
    )


class RecoverManualReportsTests(unittest.TestCase):
    """Verify previews and deliberate application safeguards."""

    def test_tracker_ids_are_positive_and_unique(self) -> None:
        """Reject ambiguous or duplicated tracker selections."""
        self.assertEqual(recover_manual_reports.tracker_ids("4, 9"), (4, 9))
        for value in ("", "4,", "4,4", "zero", "0"):
            with self.subTest(value=value):
                with self.assertRaises(Exception):
                    recover_manual_reports.tracker_ids(value)

    @patch.object(recover_manual_reports, "check_manual_report_recovery_by_id")
    def test_preview_is_read_only(self, preview) -> None:
        """List eligibility without invoking report generation or delivery."""
        preview.side_effect = [check(4), check(9)]
        output = StringIO()
        with redirect_stdout(output):
            result = recover_manual_reports.main(
                [
                    "--tracker-ids", "4,9",
                    "--cause", "password-validation",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("Preview only", output.getvalue())

    @patch.object(recover_manual_reports, "run_recent_scan_reports")
    @patch.object(recover_manual_reports, "check_manual_report_recovery_by_id")
    def test_blocked_selection_changes_nothing(self, preview, run_batch) -> None:
        """Abort the full explicit set when any selected row is unsafe."""
        preview.side_effect = [check(4), check(9, eligible=False)]
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            result = recover_manual_reports.main(
                [
                    "--tracker-ids", "4,9",
                    "--cause", "password-validation",
                ]
            )
        self.assertEqual(result, 2)
        run_batch.assert_not_called()

    @patch.object(recover_manual_reports, "require_env", return_value="sender@example.gov")
    @patch.object(recover_manual_reports, "run_recent_scan_reports")
    @patch.object(recover_manual_reports, "check_manual_report_recovery_by_id")
    def test_apply_requires_confirmation_and_runs_exact_scope(
        self, preview, run_batch, require_env
    ) -> None:
        """Apply only the confirmed IDs and selected historical cause."""
        preview.side_effect = [check(4), check(9)]
        run_batch.return_value = SimpleNamespace(
            candidates=2, generated=2, sent=2, failed=0
        )
        with redirect_stdout(StringIO()):
            result = recover_manual_reports.main(
                [
                    "--tracker-ids", "4,9",
                    "--cause", "password-validation",
                    "--apply",
                    "--confirm", "RECOVER",
                    "--send-email",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(
            run_batch.call_args.kwargs["recovery_causes"],
            {4: "password-validation", 9: "password-validation"},
        )
        self.assertTrue(run_batch.call_args.kwargs["include_manual"])
        self.assertFalse(run_batch.call_args.kwargs["retry_ready_emails"])
        require_env.assert_called_once_with("WAS_EMAIL_SOURCE")

    def test_apply_requires_typed_confirmation_and_delivery(self) -> None:
        """Prevent state transitions without deliberate complete recovery."""
        for arguments in (
            ["--apply", "--send-email"],
            ["--apply", "--confirm", "RECOVER"],
        ):
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    recover_manual_reports.main(
                        [
                            "--tracker-ids", "4",
                            "--cause", "qualys-read-timeout",
                        ] + arguments
                    )


if __name__ == "__main__":
    unittest.main()
