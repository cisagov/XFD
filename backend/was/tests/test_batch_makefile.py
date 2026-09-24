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
