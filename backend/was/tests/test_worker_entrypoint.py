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
            xml_export_command = directory_path / "was-export-xml"
            inventory_command = directory_path / "was-inventory"
            admin_command = directory_path / "was-admin"
            special_cases_command = directory_path / "was-special-cases"
            tracker_command = directory_path / "was-tracker"
            update_tracker_command = directory_path / "was-update-tracker"
            config_path = directory_path / "was_config.txt"

            batch_command.write_text(
                "#!/bin/sh\necho batch \"$@\"\n",
                encoding="utf-8",
            )
            reports_command.write_text(
                "#!/bin/sh\necho reports \"$@\"\n",
                encoding="utf-8",
            )
            xml_export_command.write_text(
                "#!/bin/sh\necho export-xml \"$@\"\n",
                encoding="utf-8",
            )
            inventory_command.write_text(
                "#!/bin/sh\necho inventory \"$@\"\n",
                encoding="utf-8",
            )
            admin_command.write_text(
                "#!/bin/sh\necho admin \"$@\"\n",
                encoding="utf-8",
            )
            special_cases_command.write_text(
                "#!/bin/sh\necho special-cases \"$@\"\n",
                encoding="utf-8",
            )
            tracker_command.write_text(
                "#!/bin/sh\necho tracker \"$@\"\n",
                encoding="utf-8",
            )
            update_tracker_command.write_text(
                "#!/bin/sh\necho update-tracker \"$@\"\n",
                encoding="utf-8",
            )
            batch_command.chmod(0o755)
            reports_command.chmod(0o755)
            xml_export_command.chmod(0o755)
            inventory_command.chmod(0o755)
            admin_command.chmod(0o755)
            special_cases_command.chmod(0o755)
            tracker_command.chmod(0o755)
            update_tracker_command.chmod(0o755)

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

    def test_single_report_routes_to_single_report_command(self) -> None:
        """Route single report commands to the single report CLI."""
        result = self.run_entrypoint(
            ["was-reports", "--tag", "TAG1", "--change-password"],
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("reports --tag TAG1 --change-password", result.stdout)

    def test_batch_command_routes_without_config_file(self) -> None:
        """Route batch commands because config can be generated from .env."""
        result = self.run_entrypoint(["--limit", "1"])

        self.assertEqual(result.returncode, 0)
        self.assertIn("batch --limit 1", result.stdout)

    def test_xml_export_routes_to_xml_export_command(self) -> None:
        """Route XML export arguments to the XML export CLI."""
        result = self.run_entrypoint(
            ["was-export-xml", "--tag", "TAG1", "--filename", "tag1.xml"],
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "export-xml --tag TAG1 --filename tag1.xml",
            result.stdout,
        )

    def test_inventory_routes_to_inventory_command(self) -> None:
        """Route inventory arguments to the inventory CLI."""
        result = self.run_entrypoint(["was-inventory"])

        self.assertEqual(result.returncode, 0)
        self.assertIn("inventory", result.stdout)

    def test_admin_routes_to_admin_command(self) -> None:
        """Route guarded Qualys administration commands to their CLI."""
        result = self.run_entrypoint(
            [
                "was-admin",
                "add-tag",
                "--url",
                "https://example.gov",
                "--tag",
                "TAG1",
                "--confirm",
            ]
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn(
            "admin add-tag --url https://example.gov --tag TAG1 --confirm",
            result.stdout,
        )

    def test_special_cases_routes_to_special_cases_command(self) -> None:
        """Route special case commands to the special case CLI."""
        result = self.run_entrypoint(["was-special-cases", "list"])

        self.assertEqual(result.returncode, 0)
        self.assertIn("special-cases list", result.stdout)

    def test_tracker_routes_to_tracker_command(self) -> None:
        """Route tracker commands to the tracker CLI."""
        result = self.run_entrypoint(
            ["was-tracker", "export-csv", "--output", "/tmp/tracker.csv"],
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("tracker export-csv --output /tmp/tracker.csv", result.stdout)

    def test_update_tracker_routes_to_update_tracker_command(self) -> None:
        """Route update tracker commands to the update tracker CLI."""
        result = self.run_entrypoint(["was-update-tracker", "--delete-apps"])

        self.assertEqual(result.returncode, 0)
        self.assertIn("update-tracker --delete-apps", result.stdout)


if __name__ == "__main__":
    unittest.main()
