"""Tests for the production WAS report generator CLI."""

# Standard Python Libraries
from pathlib import Path
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import report_generator


class ReportGeneratorTests(unittest.TestCase):
    """Validate production report arguments and password handling."""

    def test_parse_args_accepts_encrypt_alias(self) -> None:
        """Accept the established encrypt alias at the production boundary."""
        arguments = report_generator.parse_args(
            ["-t", "TEST_TAG", "--encrypt", "password"]
        )

        self.assertEqual(arguments.tag, "TEST_TAG")
        self.assertEqual(arguments.report_password, "password")

    def test_parse_args_rejects_removed_legacy_pipeline(self) -> None:
        """Reject attempts to execute the frozen legacy report pipeline."""
        with self.assertRaises(SystemExit):
            report_generator.parse_args(
                ["-t", "TEST_TAG", "--use-legacy-pipeline"]
            )

    def test_resolve_report_password_prefers_argument(self) -> None:
        """Use an explicit password before querying Postgres."""
        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password="from-cli",
        )

        self.assertEqual(password, "from-cli")

    @patch("was_reports.commands.report_generator.lookup_report_password")
    def test_resolve_report_password_reads_postgres(
        self,
        mock_password,
    ) -> None:
        """Read the stored password when no CLI password is supplied."""
        mock_password.return_value = "from-db"

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
        )

        self.assertEqual(password, "from-db")
        mock_password.assert_called_once_with("TEST_TAG")

    @patch("was_reports.commands.report_generator.lookup_report_password")
    def test_resolve_report_password_requires_password(
        self,
        mock_password,
    ) -> None:
        """Fail closed when no report password is available."""
        mock_password.return_value = None

        with self.assertRaises(RuntimeError):
            report_generator.resolve_report_password(
                stakeholder_tag="TEST_TAG",
                report_password=None,
            )

    @patch("was_reports.commands.report_generator.lookup_report_password")
    @patch("was_reports.commands.report_generator.create_report_password")
    def test_resolve_report_password_can_create_missing_password(
        self,
        mock_create_password,
        mock_lookup_password,
    ) -> None:
        """Create a missing stakeholder password when requested."""
        mock_lookup_password.return_value = None
        mock_create_password.return_value = "created-password"

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
            create_missing_password=True,
        )

        self.assertEqual(password, "created-password")
        mock_create_password.assert_called_once_with("TEST_TAG")

    @patch("was_reports.commands.report_generator.rotate_report_password")
    def test_main_can_rotate_password_without_running_report(
        self,
        mock_rotate_password,
    ) -> None:
        """Rotate a stored password without generating a report."""
        exit_code = report_generator.main(
            ["--tag", "TEST_TAG", "--change-password"]
        )

        self.assertEqual(exit_code, 0)
        mock_rotate_password.assert_called_once_with("TEST_TAG")

    def test_validate_stakeholder_tag_rejects_empty_tag(self) -> None:
        """Reject an empty stakeholder tag before external calls."""
        with self.assertRaises(ValueError):
            report_generator.validate_stakeholder_tag(" ")

    @patch("was_reports.commands.report_generator.generate_production_report")
    def test_main_uses_production_pipeline(
        self,
        mock_production_report,
    ) -> None:
        """Always route report generation through the WAS-owned pipeline."""
        exit_code = report_generator.main(
            [
                "-t",
                "TEST_TAG",
                "--encrypt",
                "SecurePassword123!",
                "--resource-root",
                "/WAS_REPORT_RESOURCES",
                "--output-directory",
                "/reports",
                "--workspace-root",
                "/tmp/workspaces",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_production_report.assert_called_once_with(
            stakeholder_tag="TEST_TAG",
            resource_root=Path("/WAS_REPORT_RESOURCES"),
            workspace_root=Path("/tmp/workspaces"),
            output_directory=Path("/reports"),
            python_executable=report_generator.sys.executable,
            report_password="SecurePassword123!",
        )


if __name__ == "__main__":
    unittest.main()
