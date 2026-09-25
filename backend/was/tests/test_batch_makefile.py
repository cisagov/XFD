"""Verify batch Make targets agree without starting containers or delivery."""

from pathlib import Path
import subprocess
import unittest


class BatchMakefileTests(unittest.TestCase):
    """Keep production, preview, and assignee-test date scopes aligned."""

    def test_production_uses_shared_coordinator_not_shell_worker_loop(self) -> None:
        """Launch production through the same Python workflow as capacity mode."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["make", "-n", "-C", str(directory), "recent-scan-batch"],
            capture_output=True, text=True, check=True, timeout=15,
        )
        self.assertIn("was_reports.commands.batch_coordinator", result.stdout)
        self.assertIn('--workers "30" --worker-backend docker', result.stdout)
        self.assertIn('--worker-image "was-reporting"', result.stdout)
        self.assertIn('--lookback-days "3" --apply', result.stdout)
        self.assertNotIn("worker_pids=", result.stdout)
        self.assertNotIn("--send-assignee-digests", result.stdout)

    def test_assignee_test_inherits_default_and_explicit_windows(self) -> None:
        """Dry-run expansion forwards seven days by default and honors overrides."""
        directory = Path(__file__).resolve().parents[1]
        for override, expected in ((None, "7"), ("30", "30"), ("all", "all")):
            with self.subTest(override=override):
                command = [
                    "make", "-n", "-C", str(directory),
                    "recent-scan-batch-assignee-test",
                    "TEST_RECIPIENTS=preview@example.invalid",
                ]
                if override is not None:
                    command.append("BATCH_DAYS_BACK={}".format(override))
                result = subprocess.run(
                    command, capture_output=True, text=True, check=True, timeout=15
                )
                self.assertIn('BATCH_DAYS_BACK="{}"'.format(expected), result.stdout)
                self.assertIn('--days-back "{}"'.format(expected), result.stdout)
                self.assertNotIn("previous 30 calendar days", result.stdout)

    def test_log_diagnostics_remain_make_only_and_read_batch_files(self) -> None:
        """Expose summary, error, and tag filters without adding menu operations."""
        directory = Path(__file__).resolve().parents[1]
        commands = {
            "logs-latest": ("--latest --mode summary", []),
            "logs-summary": ("--mode summary", ["LOG_BATCH_ID=" + "0" * 36]),
            "logs-errors": ("--mode errors", ["LOG_BATCH_ID=" + "0" * 36]),
            "logs-tag": (
                '--mode tag --tag "TAG1"',
                ["LOG_BATCH_ID=" + "0" * 36, "LOG_TAG=TAG1"],
            ),
        }
        for target, (expected, variables) in commands.items():
            with self.subTest(target=target):
                result = subprocess.run(
                    ["make", "-n", "-C", str(directory), target] + variables,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=15,
                )
                self.assertIn("was_reports.commands.log_diagnostics", result.stdout)
                self.assertIn(expected, result.stdout)

    def test_targets_removed_test_requires_explicit_rows_and_assignee(self) -> None:
        """Route a reviewed Targets Removed test through isolated replay."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "make",
                "-n",
                "-C",
                str(directory),
                "test-targets-removed",
                "TARGETS_REMOVED_TRACKER_IDS=260169,260087",
                "TEST_RECIPIENTS=analyst@example.gov",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

        self.assertIn("test-report-replay", result.stdout)
        self.assertIn(
            '--targets-removed-tracker-ids "260169,260087"',
            result.stdout,
        )
        self.assertIn('--test-recipients "analyst@example.gov"', result.stdout)
