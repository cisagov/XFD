"""Tests for the WAS report generator CLI boundary."""

# Standard Python Libraries
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports import report_generator


class ReportGeneratorTests(unittest.TestCase):
    """Validate legacy command construction and input handling."""

    def test_build_legacy_command_includes_tag_and_password(self) -> None:
        """Build the legacy creator command without shell interpolation."""
        command = report_generator.build_legacy_command(
            python_executable="python3",
            script_path=Path("/app/was_report/WAS_report_creator.py"),
            stakeholder_tag="TEST_TAG",
            report_password="password",
        )

        self.assertEqual(
            command,
            [
                "python3",
                "/app/was_report/WAS_report_creator.py",
                "-t",
                "TEST_TAG",
                "--encrypt",
                "password",
            ],
        )

    def test_resolve_report_password_prefers_argument(self) -> None:
        """Use the explicit CLI password before querying Postgres."""
        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password="from-cli",
            allow_unencrypted=False,
        )

        self.assertEqual(password, "from-cli")

    @patch("was_reports.report_generator.lookup_report_password")
    def test_resolve_report_password_reads_postgres(self, mock_password) -> None:
        """Read report password from Postgres when no CLI password is supplied."""
        mock_password.return_value = "from-db"

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
            allow_unencrypted=False,
        )

        self.assertEqual(password, "from-db")
        mock_password.assert_called_once_with("TEST_TAG")

    @patch("was_reports.report_generator.lookup_report_password")
    def test_resolve_report_password_requires_password(self, mock_password) -> None:
        """Fail closed when no password is available."""
        mock_password.return_value = None

        with self.assertRaises(RuntimeError):
            report_generator.resolve_report_password(
                stakeholder_tag="TEST_TAG",
                report_password=None,
                allow_unencrypted=False,
            )

    @patch("was_reports.report_generator.lookup_report_password")
    def test_resolve_report_password_allows_unencrypted(self, mock_password) -> None:
        """Pass N/A to legacy creator when unencrypted output is allowed."""
        mock_password.return_value = None

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
            allow_unencrypted=True,
        )

        self.assertEqual(password, "N/A")

    @patch("was_reports.report_generator.lookup_report_password")
    @patch("was_reports.report_generator.create_report_password")
    def test_resolve_report_password_can_create_missing_password(
        self, mock_create_password, mock_lookup_password
    ) -> None:
        """Create a missing password when explicitly requested."""
        mock_lookup_password.return_value = None
        mock_create_password.return_value = "created-password"

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
            allow_unencrypted=False,
            create_missing_password=True,
        )

        self.assertEqual(password, "created-password")
        mock_create_password.assert_called_once_with("TEST_TAG")

    @patch("was_reports.report_generator.rotate_report_password")
    def test_main_can_rotate_password_without_running_report(
        self, mock_rotate_password
    ) -> None:
        """Generate a new stored password without calling the legacy generator."""
        exit_code = report_generator.main(
            [
                "--tag",
                "TEST_TAG",
                "--change-password",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_rotate_password.assert_called_once_with("TEST_TAG")

    def test_validate_stakeholder_tag_rejects_empty_tag(self) -> None:
        """Reject empty stakeholder tags before calling Qualys."""
        with self.assertRaises(ValueError):
            report_generator.validate_stakeholder_tag(" ")

    def test_run_legacy_report_uses_expected_working_directory(self) -> None:
        """Execute the legacy report from its own asset directory."""
        with tempfile.TemporaryDirectory() as directory:
            legacy_root = Path(directory)
            script_path = legacy_root / "WAS_report_creator.py"
            script_path.write_text("print('ok')", encoding="utf-8")

            result = report_generator.run_legacy_report(
                python_executable="python3",
                legacy_root=legacy_root,
                stakeholder_tag="TEST_TAG",
                report_password="password",
            )

        self.assertEqual(result.returncode, 0)
        self.assertIsInstance(result, subprocess.CompletedProcess)

    @patch("was_reports.report_generator.run_legacy_report")
    def test_generate_report_verifies_expected_output(self, mock_run_report) -> None:
        """Return the verified output path after legacy generation."""
        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory)
            output_path = output_directory / "TEST_TAG_report_2026-08-25.pdf"
            output_path.write_text("pdf", encoding="utf-8")

            with patch("was_reports.report_generator.prepare_legacy_config"):
                with patch(
                    "was_reports.report_generator.expected_pdf_output_path"
                ) as mock_expected:
                    mock_expected.return_value = output_path
                    result = report_generator.generate_report(
                        stakeholder_tag="TEST_TAG",
                        config_path=output_path,
                        legacy_root=output_directory,
                        output_directory=str(output_directory),
                        python_executable="python3",
                        report_password="password",
                    )

        self.assertEqual(result, output_path)
        self.assertEqual(mock_run_report.call_count, 1)


if __name__ == "__main__":
    unittest.main()
