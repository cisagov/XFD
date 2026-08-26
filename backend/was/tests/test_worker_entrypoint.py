"""Tests for the WAS worker entrypoint shell routing."""

# Standard Python Libraries
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class WorkerEntrypointTests(unittest.TestCase):
    """Validate shell entrypoint command routing."""

    def run_entrypoint(self, arguments, config_exists=False):
        """Run the worker entrypoint with stub commands on PATH."""
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            batch_command = directory_path / "was-report-batch"
            reports_command = directory_path / "was-reports"
            config_path = directory_path / "was_config.txt"

            batch_command.write_text(
                "#!/bin/sh\necho batch \"$@\"\n",
                encoding="utf-8",
            )
            reports_command.write_text(
                "#!/bin/sh\necho reports \"$@\"\n",
                encoding="utf-8",
            )
            batch_command.chmod(0o755)
            reports_command.chmod(0o755)

            if config_exists:
                config_path.write_text("[info]\n", encoding="utf-8")

            environment = os.environ.copy()
            environment["PATH"] = "{}:{}".format(
                str(directory_path),
                environment["PATH"],
            )
            environment["WAS_CONFIG_PATH"] = str(config_path)

            return subprocess.run(
                ["bash", "backend/was/worker/was-report-start.sh"] + arguments,
                check=False,
                capture_output=True,
                env=environment,
                text=True,
            )

    def test_batch_help_does_not_require_config(self) -> None:
        """Route batch help before checking for mounted config."""
        result = self.run_entrypoint(["--help"])

        self.assertEqual(result.returncode, 0)
        self.assertIn("batch --help", result.stdout)

    def test_single_report_help_does_not_require_config(self) -> None:
        """Route single report help before checking for mounted config."""
        result = self.run_entrypoint(["was-reports", "--help"])

        self.assertEqual(result.returncode, 0)
        self.assertIn("reports --help", result.stdout)

    def test_single_report_routes_after_config_check(self) -> None:
        """Route single report commands when config exists."""
        result = self.run_entrypoint(
            ["was-reports", "--tag", "TAG1", "--change-password"],
            config_exists=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("reports --tag TAG1 --change-password", result.stdout)

    def test_missing_config_fails_non_help_commands(self) -> None:
        """Reject report commands when config is missing."""
        result = self.run_entrypoint(["--limit", "1"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("WAS config file not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
