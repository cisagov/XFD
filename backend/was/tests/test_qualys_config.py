"""Tests for environment-backed Qualys configuration."""

# Standard Python Libraries
import os
from pathlib import Path
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.utils.qualys_config import (
    load_qualys_credentials_from_environment,
)


class QualysConfigTests(unittest.TestCase):
    """Validate loading Qualys credentials without filesystem configuration."""

    def test_load_qualys_credentials_from_environment(self) -> None:
        """Load every required Qualys credential from environment variables."""
        with patch.dict(
            os.environ,
            {
                "WAS_QUALYS_USERNAME": "user",
                "WAS_QUALYS_PASSWORD": "secret",
                "WAS_QUALYS_HOSTNAME": "qualys.example",
            },
            clear=False,
        ):
            credentials = load_qualys_credentials_from_environment()

        self.assertEqual(credentials.username, "user")
        self.assertEqual(credentials.password, "secret")
        self.assertEqual(credentials.hostname, "qualys.example")

    def test_missing_qualys_environment_value_fails_closed(self) -> None:
        """Reject a missing password instead of creating a config file."""
        environment = {
            "WAS_QUALYS_USERNAME": "user",
            "WAS_QUALYS_HOSTNAME": "qualys.example",
        }
        with patch(
            "was_reports.utils.env.default_env_path",
            return_value=Path("/missing/was.env"),
        ):
            with patch.dict(os.environ, environment, clear=True):
                with self.assertRaises(RuntimeError):
                    load_qualys_credentials_from_environment()


if __name__ == "__main__":
    unittest.main()
