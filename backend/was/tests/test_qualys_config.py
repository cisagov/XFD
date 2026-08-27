"""Tests for Qualys configuration validation."""

# Standard Python Libraries
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports.utils.qualys_config import (
    ensure_qualys_config_file,
    load_qualys_credentials,
    load_qualys_credentials_from_environment,
    load_was_file_paths_from_environment,
    missing_required_options,
    read_qualys_config,
    validate_qualys_config,
    write_qualys_config_file,
    QualysCredentials,
)


class QualysConfigTests(unittest.TestCase):
    """Validate Qualys config parsing behavior."""

    def test_read_qualys_config_rejects_missing_file(self) -> None:
        """Reject a missing Qualys config file."""
        with self.assertRaises(FileNotFoundError):
            read_qualys_config(Path("/tmp/missing-was-config.txt"))

    def test_missing_required_options_finds_missing_section(self) -> None:
        """Treat a missing config section as missing all required options."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"
            config_path.write_text("[other]\nvalue = test\n", encoding="utf-8")
            parser = read_qualys_config(config_path)

        missing_options = missing_required_options(
            parser=parser,
            section_name="info",
            required_options=("username", "password", "hostname"),
        )

        self.assertEqual(missing_options, ["username", "password", "hostname"])

    def test_validate_qualys_config_accepts_required_info_fields(self) -> None:
        """Accept a Qualys config with required credential fields."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"
            config_path.write_text(
                "[info]\n"
                "username = user\n"
                "password = secret\n"
                "hostname = qualys.example\n",
                encoding="utf-8",
            )

            validate_qualys_config(config_path)

    def test_validate_qualys_config_rejects_blank_password(self) -> None:
        """Reject blank required credential values."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"
            config_path.write_text(
                "[info]\nusername = user\npassword = \n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError) as context:
                validate_qualys_config(config_path)

        self.assertIn("password", str(context.exception))
        self.assertNotIn("secret", str(context.exception))

    def test_load_qualys_credentials_reads_required_fields(self) -> None:
        """Load Qualys credentials from the expected config section."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"
            config_path.write_text(
                "[info]\n"
                "username = user\n"
                "password = secret\n"
                "hostname = qualys.example\n",
                encoding="utf-8",
            )

            credentials = load_qualys_credentials(config_path)

        self.assertEqual(credentials.username, "user")
        self.assertEqual(credentials.password, "secret")
        self.assertEqual(credentials.hostname, "qualys.example")

    def test_load_qualys_credentials_from_environment(self) -> None:
        """Load Qualys credentials from WAS environment constants."""
        with patch.dict(
            os.environ,
            {
                "WAS_QUALYS_USERNAME": "user",
                "WAS_QUALYS_PASSWORD": "secret",
                "WAS_QUALYS_HOSTNAME": "qualys.example",
                "WAS_DAILY_WAS_LOG": "/reports/dailywas.log",
            },
        ):
            credentials = load_qualys_credentials_from_environment()
            was_file_paths = load_was_file_paths_from_environment()

        self.assertEqual(credentials.username, "user")
        self.assertEqual(credentials.password, "secret")
        self.assertEqual(credentials.hostname, "qualys.example")
        self.assertEqual(was_file_paths["dailywaslog"], "/reports/dailywas.log")

    def test_write_qualys_config_file_creates_legacy_config(self) -> None:
        """Write a legacy-compatible config file from env credentials."""
        credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"

            write_qualys_config_file(
                config_path=config_path,
                credentials=credentials,
                was_file_paths={"dailyReportsFilePath": "/reports/daily.xlsx"},
            )

            parser = read_qualys_config(config_path)

        self.assertEqual(parser.get("info", "username"), "user")
        self.assertEqual(parser.get("info", "password"), "secret")
        self.assertEqual(parser.get("info", "hostname"), "qualys.example")
        self.assertEqual(
            parser.get("was_files", "dailyReportsFilePath"),
            "/reports/daily.xlsx",
        )

    def test_ensure_qualys_config_file_creates_missing_config(self) -> None:
        """Create a missing legacy config file from environment constants."""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "was_config.txt"
            with patch.dict(
                os.environ,
                {
                    "WAS_QUALYS_USERNAME": "user",
                    "WAS_QUALYS_PASSWORD": "secret",
                    "WAS_QUALYS_HOSTNAME": "qualys.example",
                    "WAS_DAILY_WAS_LOG": "/reports/dailywas.log",
                },
            ):
                ensured_path = ensure_qualys_config_file(config_path)

            parser = read_qualys_config(ensured_path)

        self.assertEqual(ensured_path, config_path)
        self.assertEqual(parser.get("info", "username"), "user")
        self.assertEqual(
            parser.get("was_files", "dailywaslog"),
            "/reports/dailywas.log",
        )


if __name__ == "__main__":
    unittest.main()
