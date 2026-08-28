"""Tests for the WAS update tracker CLI."""

# Standard Python Libraries
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import update_tracker_cli


class UpdateTrackerCliTests(unittest.TestCase):
    """Validate update tracker command behavior."""

    def test_default_update_tracker_root_exists(self) -> None:
        """Resolve the bundled legacy tracker from the WAS project root."""
        self.assertTrue(update_tracker_cli.UPDATE_TRACKER_ROOT.is_dir())

    def test_parse_args_defaults_to_non_destructive_mode(self) -> None:
        """Disable Qualys webapp deletion unless explicitly requested."""
        args = update_tracker_cli.parse_args([])

        self.assertFalse(args.delete_apps)
        self.assertIsNone(args.tag)

    def test_parse_args_allows_delete_apps(self) -> None:
        """Allow an operator to request Qualys webapp deletion explicitly."""
        args = update_tracker_cli.parse_args(["--delete-apps"])

        self.assertTrue(args.delete_apps)

    def test_parse_args_accepts_exact_stakeholder_tag(self) -> None:
        """Allow an operator to scope tracker writes to one stakeholder."""
        args = update_tracker_cli.parse_args(["--tag", "CUSTOMER"])

        self.assertEqual(args.tag, "CUSTOMER")

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

        def fake_main(delete_apps=True, stakeholder_tag=None):
            """Capture update tracker execution settings."""
            calls.append((delete_apps, stakeholder_tag))

        fake_module.main = fake_main

        original_module = sys.modules.get("main")
        sys.modules["main"] = fake_module
        try:
            update_tracker_cli.run_update_tracker(
                delete_apps=True,
                stakeholder_tag="CUSTOMER",
            )
        finally:
            if original_module is None:
                del sys.modules["main"]
            else:
                sys.modules["main"] = original_module

        self.assertEqual(calls, [(True, "CUSTOMER")])

    def test_tracker_main_scopes_schedule_discovery(self) -> None:
        """Filter schedules before processing unrelated stakeholder data."""
        calls = []

        schedules_module = types.ModuleType(
            "utils.qualys_api_search.search_schedules"
        )

        def fake_search_schedules(stakeholder_tag=None):
            """Capture the tag supplied to Qualys schedule discovery."""
            calls.append(stakeholder_tag)
            return {"CUSTOMER": object()}

        schedules_module.search_schedules = fake_search_schedules

        scans_module = types.ModuleType(
            "utils.qualys_api_search.search_scans"
        )

        def fake_search_scans(stakeholders):
            """Return the supplied scoped stakeholder mapping."""
            return stakeholders

        scans_module.search_scans = fake_search_scans

        create_module = types.ModuleType(
            "utils.tracker_operations.create_tracker_items"
        )

        def fake_create_tracker_items(scan_groups, stakeholders):
            """Return an empty tracker item list for orchestration testing."""
            return []

        create_module.create_tracker_items = fake_create_tracker_items

        update_module = types.ModuleType(
            "utils.tracker_operations.update_tracker"
        )

        def fake_update_tracker(tracker_items, delete_apps):
            """Accept tracker update inputs without database writes."""

        update_module.update_tracker = fake_update_tracker

        fake_modules = {
            schedules_module.__name__: schedules_module,
            scans_module.__name__: scans_module,
            create_module.__name__: create_module,
            update_module.__name__: update_module,
        }
        main_path = (
            Path(__file__).parents[1]
            / "update_tracker"
            / "update_tracker"
            / "main.py"
        )
        spec = importlib.util.spec_from_file_location(
            "test_update_tracker_main_module",
            main_path,
        )
        module = importlib.util.module_from_spec(spec)

        with patch.dict(sys.modules, fake_modules):
            spec.loader.exec_module(module)
            module.main(delete_apps=False, stakeholder_tag="CUSTOMER")

        self.assertEqual(calls, ["CUSTOMER"])

    @patch("was_reports.commands.update_tracker_cli.run_update_tracker")
    def test_main_runs_update_tracker(self, mock_run_update_tracker) -> None:
        """Run the update tracker from parsed arguments."""
        exit_code = update_tracker_cli.main(
            ["--delete-apps", "--tag", " CUSTOMER "]
        )

        self.assertEqual(exit_code, 0)
        mock_run_update_tracker.assert_called_once_with(
            delete_apps=True,
            stakeholder_tag="CUSTOMER",
        )


if __name__ == "__main__":
    unittest.main()
