"""Tests for the WAS-owned update tracker CLI."""

# Standard Python Libraries
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import update_tracker_cli


class UpdateTrackerCliTests(unittest.TestCase):
    """Validate tracker command parsing and service delegation."""

    def test_parse_args_defaults_to_non_destructive_mode(self) -> None:
        """Disable Qualys webapp deletion unless explicitly requested."""
        arguments = update_tracker_cli.parse_args([])

        self.assertFalse(arguments.delete_apps)
        self.assertIsNone(arguments.tag)

    def test_parse_args_allows_delete_apps(self) -> None:
        """Allow an operator to explicitly request webapp deletion."""
        arguments = update_tracker_cli.parse_args(["--delete-apps"])

        self.assertTrue(arguments.delete_apps)

    @patch("was_reports.commands.update_tracker_cli.refresh_daily_tracker")
    @patch("was_reports.commands.update_tracker_cli.create_qualys_client")
    def test_run_update_tracker_uses_was_owned_service(
        self,
        mock_create_client,
        mock_refresh_tracker,
    ) -> None:
        """Call the production tracker service with the production client."""
        client = object()
        mock_create_client.return_value = client

        update_tracker_cli.run_update_tracker(
            delete_apps=True,
            stakeholder_tag="CUSTOMER",
        )

        mock_refresh_tracker.assert_called_once_with(
            client=client,
            delete_apps=True,
            stakeholder_tag="CUSTOMER",
        )

    @patch("was_reports.commands.update_tracker_cli.run_update_tracker")
    def test_main_normalizes_stakeholder_tag(
        self,
        mock_run_update_tracker,
    ) -> None:
        """Trim the optional stakeholder tag before service execution."""
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
