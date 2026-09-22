"""Verify batch Make targets agree without starting containers or delivery."""

from pathlib import Path
import subprocess
import unittest


class BatchMakefileTests(unittest.TestCase):
    """Keep production, preview, and assignee-test date scopes aligned."""

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
