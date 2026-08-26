"""Tests for the top-level WAS reporting compatibility wrapper."""

# Standard Python Libraries
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


def load_reporting_module():
    """Load reporting.py without requiring package installation."""
    reporting_path = Path("backend/was/reporting.py")
    spec = importlib.util.spec_from_file_location(
        "was_reporting_wrapper",
        reporting_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReportingWrapperTests(unittest.TestCase):
    """Validate top-level reporting compatibility behavior."""

    @patch("was_reports.batch_runner.main")
    def test_reporting_main_delegates_to_batch_runner(self, mock_batch_main) -> None:
        """Delegate scheduled report execution to the package batch runner."""
        mock_batch_main.return_value = 0
        reporting = load_reporting_module()

        exit_code = reporting.main(["--limit", "1"])

        self.assertEqual(exit_code, 0)
        mock_batch_main.assert_called_once_with(["--limit", "1"])


if __name__ == "__main__":
    unittest.main()
