"""Tests for WAS .env loading helpers."""

# Standard Python Libraries
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports.utils import env


class EnvTests(unittest.TestCase):
    """Validate local .env loading behavior."""

    def test_load_env_file_sets_missing_values(self) -> None:
        """Load key-value pairs from a specified .env file."""
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "WAS_TEST_VALUE='configured value'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                env.load_env_file(env_path=env_path)
                self.assertEqual(os.environ["WAS_TEST_VALUE"], "configured value")

    def test_load_env_file_does_not_override_existing_values(self) -> None:
        """Preserve process environment values by default."""
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("WAS_TEST_VALUE=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"WAS_TEST_VALUE": "from-process"}):
                env.load_env_file(env_path=env_path)
                self.assertEqual(os.environ["WAS_TEST_VALUE"], "from-process")

    def test_load_env_file_can_override_existing_values(self) -> None:
        """Allow explicit override for controlled test or setup usage."""
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("WAS_TEST_VALUE=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"WAS_TEST_VALUE": "from-process"}):
                env.load_env_file(env_path=env_path, override=True)
                self.assertEqual(os.environ["WAS_TEST_VALUE"], "from-file")

    def test_require_env_raises_for_missing_value(self) -> None:
        """Raise a clear error when a required value is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("was_reports.utils.env.default_env_path") as mock_path:
                mock_path.return_value = Path("/tmp/missing-was-env")
                with self.assertRaises(RuntimeError):
                    env.require_env("WAS_MISSING_VALUE")


if __name__ == "__main__":
    unittest.main()
