"""Tests for the WAS update tracker CLI."""

# Standard Python Libraries
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports import update_tracker_cli


class UpdateTrackerCliTests(unittest.TestCase):
    """Validate update tracker command behavior."""

    def test_parse_args_defaults_to_non_destructive_mode(self) -> None:
        """Disable Qualys webapp deletion unless explicitly requested."""
        args = update_tracker_cli.parse_args([])

        self.assertFalse(args.delete_apps)

    def test_parse_args_allows_delete_apps(self) -> None:
        """Allow an operator to request Qualys webapp deletion explicitly."""
        args = update_tracker_cli.parse_args(["--delete-apps"])

        self.assertTrue(args.delete_apps)

    def test_ensure_update_tracker_path_adds_path_once(self) -> None:
        """Add the legacy update tracker root to sys.path once."""
        with patch.object(
            update_tracker_cli,
            "UPDATE_TRACKER_ROOT",
            Path("/tmp/was-update-tracker"),
        ):
            original_path = list(sys.path)
            try:
                sys.path = [
                    path
                    for path in sys.path
                    if path != "/tmp/was-update-tracker"
                ]

                update_tracker_cli.ensure_update_tracker_path()
                update_tracker_cli.ensure_update_tracker_path()

                self.assertEqual(sys.path.count("/tmp/was-update-tracker"), 1)
                self.assertEqual(sys.path[0], "/tmp/was-update-tracker")
            finally:
                sys.path = original_path

    def test_run_update_tracker_calls_legacy_main(self) -> None:
        """Call the legacy update tracker main function with delete setting."""
        calls = []
        fake_module = types.ModuleType("main")

        def fake_main(delete_apps=True):
            """Capture update tracker delete-apps setting."""
            calls.append(delete_apps)

        fake_module.main = fake_main

        original_module = sys.modules.get("main")
        sys.modules["main"] = fake_module
        try:
            update_tracker_cli.run_update_tracker(delete_apps=True)
        finally:
            if original_module is None:
                del sys.modules["main"]
            else:
                sys.modules["main"] = original_module

        self.assertEqual(calls, [True])

    @patch("was_reports.update_tracker_cli.run_update_tracker")
    def test_main_runs_update_tracker(self, mock_run_update_tracker) -> None:
        """Run the update tracker from parsed arguments."""
        exit_code = update_tracker_cli.main(["--delete-apps"])

        self.assertEqual(exit_code, 0)
        mock_run_update_tracker.assert_called_once_with(delete_apps=True)


if __name__ == "__main__":
    unittest.main()
