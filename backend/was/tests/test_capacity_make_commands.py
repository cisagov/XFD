"""Verify capacity operator commands without running Docker or database tools."""

from pathlib import Path
import shutil
import subprocess  # nosec B404
import unittest


@unittest.skipUnless(shutil.which("make"), "make is required for command-plan checks")
class CapacityMakeCommandsTests(unittest.TestCase):
    """Keep start, continue, and destructive restart explicit and distinct."""

    def plan(self, target, *arguments):
        """Render Make recipes in dry-run mode, including recursive Make calls."""
        result = subprocess.run(  # nosec B603
            [shutil.which("make"), "--dry-run", target,
             "TEST_RECIPIENTS=test@example.gov", *arguments],
            cwd=Path(__file__).resolve().parents[1], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return result.stdout

    def test_start_defaults_to_auto_count_and_generated_id(self):
        """Operators do not need a UUID or an exact post-refresh count."""
        plan = self.plan("capacity-start", "CAPACITY_RUN_ID=", "APPLY=0")
        self.assertIn('--expected-candidates "auto"', plan)
        self.assertIn('if [ -n "" ]; then set -- "$@" --run-id', plan)
        self.assertIn('case "0"', plan)
        self.assertNotIn("capacity_database_reset", plan)
        self.assertIn('--worker-backend docker --worker-image "was-reporting"', plan)
        self.assertIn('--env-file ".env" --output-root', plan)
        self.assertNotIn('/var/run/docker.sock', plan)

    def test_continue_uses_saved_workload_not_reset(self):
        """Continuation must never reset the test database."""
        plan = self.plan("capacity-continue", "APPLY=1")
        self.assertIn('case "continue"', plan)
        self.assertIn("--continue-latest", plan)
        self.assertNotIn("capacity_database_reset", plan)

    def test_selected_continuation_can_be_specified(self):
        """A caller can choose a previous run rather than accepting latest."""
        parent = "ccce3a43-cd47-4a26-99e9-cadcc1094266"
        plan = self.plan("capacity-continue", "CAPACITY_CONTINUE_RUN_ID=" + parent)
        self.assertIn('--continue-run "{}"'.format(parent), plan)

    def test_start_over_resets_before_new_run(self):
        """Restart is distinct, stops on reset failure, and selects a fresh ID."""
        plan = self.plan("capacity-start-over", "APPLY=1")
        self.assertLess(plan.index("capacity_database_reset"), plan.rindex("commands.capacity_test"))
        self.assertIn("CAPACITY_ACTION=start CAPACITY_RUN_ID=", plan)


if __name__ == "__main__":
    unittest.main()
