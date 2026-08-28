"""Tests for the WAS report generator CLI boundary."""

# Standard Python Libraries
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import report_generator


class ReportGeneratorTests(unittest.TestCase):
    """Validate legacy command construction and input handling."""

    def test_build_legacy_command_excludes_password(self) -> None:
        """Keep the report password out of child process arguments."""
        command = report_generator.build_legacy_command(
            python_executable="python3",
            script_path=Path("/app/was_report/WAS_report_creator.py"),
            stakeholder_tag="TEST_TAG",
        )

        self.assertEqual(
            command,
            [
                "python3",
                "/app/was_report/WAS_report_creator.py",
                "-t",
                "TEST_TAG",
            ],
        )

    def test_build_legacy_input_answers_encryption_prompts(self) -> None:
        """Provide the password through standard input for the frozen script."""
        legacy_input = report_generator.build_legacy_input("child-password")

        self.assertEqual(legacy_input, "Y\nchild-password\n")

    def test_build_legacy_input_can_skip_encryption(self) -> None:
        """Decline legacy encryption when unencrypted output was approved."""
        legacy_input = report_generator.build_legacy_input("N/A")

        self.assertEqual(legacy_input, "N\n")

    @patch("was_reports.commands.report_generator.subprocess.run")
    def test_run_legacy_report_passes_password_only_through_standard_input(
        self,
        mock_subprocess_run,
    ) -> None:
        """Keep the password out of process arguments and environment."""
        mock_subprocess_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
        )
        with tempfile.TemporaryDirectory() as directory:
            legacy_root = Path(directory)
            script_path = legacy_root / "WAS_report_creator.py"
            script_path.write_text("print('ok')", encoding="utf-8")
            report_generator.run_legacy_report(
                python_executable="python3",
                legacy_root=legacy_root,
                stakeholder_tag="TEST_TAG",
                report_password="child-password",
            )

        command = mock_subprocess_run.call_args.args[0]
        self.assertNotIn("child-password", command)
        self.assertNotIn("--encrypt", command)
        self.assertEqual(
            mock_subprocess_run.call_args.kwargs["input"],
            "Y\nchild-password\n",
        )
        self.assertTrue(mock_subprocess_run.call_args.kwargs["text"])

    def test_parse_args_accepts_legacy_encrypt_alias(self) -> None:
        """Accept the observed legacy password flag at the modern CLI boundary."""
        arguments = report_generator.parse_args(
            ["-t", "TEST_TAG", "--encrypt", "password"]
        )

        self.assertEqual(arguments.tag, "TEST_TAG")
        self.assertEqual(arguments.report_password, "password")

    def test_resolve_report_password_prefers_argument(self) -> None:
        """Use the explicit CLI password before querying Postgres."""
        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password="from-cli",
            allow_unencrypted=False,
        )

        self.assertEqual(password, "from-cli")

    @patch("was_reports.commands.report_generator.lookup_report_password")
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

    @patch("was_reports.commands.report_generator.lookup_report_password")
    def test_resolve_report_password_requires_password(self, mock_password) -> None:
        """Fail closed when no password is available."""
        mock_password.return_value = None

        with self.assertRaises(RuntimeError):
            report_generator.resolve_report_password(
                stakeholder_tag="TEST_TAG",
                report_password=None,
                allow_unencrypted=False,
            )

    @patch("was_reports.commands.report_generator.lookup_report_password")
    def test_resolve_report_password_allows_unencrypted(self, mock_password) -> None:
        """Pass N/A to legacy creator when unencrypted output is allowed."""
        mock_password.return_value = None

        password = report_generator.resolve_report_password(
            stakeholder_tag="TEST_TAG",
            report_password=None,
            allow_unencrypted=True,
        )

        self.assertEqual(password, "N/A")

    @patch("was_reports.commands.report_generator.lookup_report_password")
    @patch("was_reports.commands.report_generator.create_report_password")
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

    @patch("was_reports.commands.report_generator.rotate_report_password")
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

    def test_prepare_legacy_config_can_generate_config_from_environment(self) -> None:
        """Generate a legacy config file from WAS environment constants."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"
            with patch.object(report_generator, "LEGACY_CONFIG_PATH", config_path):
                with patch.dict(
                    os.environ,
                    {
                        "WAS_QUALYS_USERNAME": "user",
                        "WAS_QUALYS_PASSWORD": "secret",
                        "WAS_QUALYS_HOSTNAME": "qualys.example",
                    },
                ):
                    report_generator.prepare_legacy_config(config_path)

            config_text = config_path.read_text(encoding="utf-8")

        self.assertIn("username = user", config_text)
        self.assertIn("hostname = qualys.example", config_text)

    @patch("was_reports.commands.report_generator.run_legacy_report")
    def test_generate_report_verifies_expected_output(self, mock_run_report) -> None:
        """Return the verified output path after legacy generation."""
        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory)
            output_path = output_directory / "TEST_TAG_report_2026-08-25.pdf"
            output_path.write_text("pdf", encoding="utf-8")

            with patch("was_reports.commands.report_generator.prepare_legacy_config"):
                with patch(
                    "was_reports.commands.report_generator.expected_pdf_output_path"
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

    @patch("was_reports.commands.report_generator.generate_report")
    @patch("was_reports.commands.report_generator.generate_extracted_report")
    def test_main_routes_only_explicit_opt_in_to_extracted_pipeline(
        self,
        mock_extracted_report,
        mock_legacy_report,
    ) -> None:
        """Keep legacy default while allowing an explicit extracted test run."""
        exit_code = report_generator.main(
            [
                "-t",
                "TEST_TAG",
                "--encrypt",
                "SecurePassword123!",
                "--use-extracted-pipeline",
                "--config-path",
                "/config/was_config.txt",
                "--legacy-root",
                "/WAS_REPORT_GENERATION",
                "--output-directory",
                "/reports",
                "--workspace-root",
                "/tmp/workspaces",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_legacy_report.assert_not_called()
        mock_extracted_report.assert_called_once_with(
            stakeholder_tag="TEST_TAG",
            config_path=Path("/config/was_config.txt"),
            legacy_root=Path("/WAS_REPORT_GENERATION"),
            workspace_root=Path("/tmp/workspaces"),
            output_directory=Path("/reports"),
            python_executable=report_generator.sys.executable,
            report_password="SecurePassword123!",
        )

    @patch("was_reports.commands.report_generator.generate_report")
    @patch("was_reports.commands.report_generator.generate_extracted_report")
    def test_main_preserves_legacy_default_route(
        self,
        mock_extracted_report,
        mock_legacy_report,
    ) -> None:
        """Continue using the original creator unless the opt-in flag is set."""
        exit_code = report_generator.main(
            ["-t", "TEST_TAG", "--encrypt", "SecurePassword123!"]
        )

        self.assertEqual(exit_code, 0)
        mock_extracted_report.assert_not_called()
        mock_legacy_report.assert_called_once()

    @patch("was_reports.commands.report_generator.generate_extracted_report")
    def test_extracted_pipeline_rejects_unencrypted_mode(
        self,
        mock_extracted_report,
    ) -> None:
        """Fail closed instead of publishing an unencrypted extracted report."""
        with patch(
            "was_reports.commands.report_generator.lookup_report_password",
            return_value=None,
        ):
            with self.assertRaises(ValueError):
                report_generator.main(
                    [
                        "-t",
                        "TEST_TAG",
                        "--allow-unencrypted",
                        "--use-extracted-pipeline",
                    ]
                )

        mock_extracted_report.assert_not_called()


if __name__ == "__main__":
    unittest.main()
