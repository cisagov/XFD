"""Tests for the interactive WAS operator menu."""

# Standard Python Libraries
import unittest
from unittest.mock import Mock, patch

# First-Party Libraries
from was_reports.commands.menu_cli import WasOperatorMenu


class WasOperatorMenuTests(unittest.TestCase):
    """Validate menu prompts and command delegation."""

    def build_menu(self, responses: list[str]) -> WasOperatorMenu:
        """Return a menu backed by deterministic test input."""
        return WasOperatorMenu(
            input_function=Mock(side_effect=responses),
            output_function=Mock(),
        )

    def test_main_menu_quits(self) -> None:
        """Exit cleanly from the numbered main menu."""
        menu = self.build_menu(["5"])

        exit_code = menu.run()

        self.assertEqual(exit_code, 0)

    @patch("was_reports.commands.menu_cli.Figlet")
    def test_main_menu_displays_figlet_banner(self, mock_figlet) -> None:
        """Display the application banner once when the menu starts."""
        mock_figlet.return_value.renderText.return_value = "WAS BANNER\n"
        menu = self.build_menu(["5"])

        menu.run()

        mock_figlet.assert_called_once_with(font="small", width=100)
        mock_figlet.return_value.renderText.assert_called_once_with(
            "WAS REPORTING"
        )
        self.assertEqual(menu.output.call_args_list[0].args[0], "WAS BANNER")

    @patch("was_reports.commands.menu_cli.batch_runner.main", return_value=0)
    def test_manual_report_delegates_to_tracked_batch_command(
        self,
        mock_batch_main,
    ) -> None:
        """Invoke the existing tracked manual report workflow."""
        menu = self.build_menu(["TAG1", "y", ""])

        menu.run_single_report(manual=True)

        mock_batch_main.assert_called_once_with(
            [
                "--recent-scans",
                "--tag",
                "TAG1",
                "--create-missing-password",
                "--send-email",
                "--skip-tracker-refresh",
                "--include-manual",
                "--continue-on-error",
                "--limit",
                "1",
            ]
        )

    @patch("was_reports.commands.menu_cli.stakeholders_cli.main", return_value=0)
    def test_contact_menu_supports_updates_and_clearing(
        self,
        mock_stakeholders_main,
    ) -> None:
        """Translate guided contact answers into stable CLI arguments."""
        menu = self.build_menu(
            [
                "TAG1",
                "Analyst Name",
                "",
                "CLEAR",
                "y",
                "",
            ]
        )

        menu.update_stakeholder_contacts()

        mock_stakeholders_main.assert_called_once_with(
            [
                "update-contacts",
                "--tag",
                "TAG1",
                "--was-report-poc",
                "Analyst Name",
                "--clear-distro-email",
                "--confirm",
            ]
        )

    @patch("was_reports.commands.menu_cli.stakeholders_cli.main", return_value=0)
    def test_sensitive_export_requires_typed_confirmation(
        self,
        mock_stakeholders_main,
    ) -> None:
        """Require a typed phrase before exporting report passwords."""
        menu = self.build_menu(["", "y", "EXPORT PASSWORDS", ""])

        menu.export_stakeholders()

        mock_stakeholders_main.assert_called_once_with(
            [
                "export-csv",
                "--output",
                "/output/was-stakeholders.csv",
                "--include-report-passwords",
                "--confirm-sensitive-export",
            ]
        )

    @patch("was_reports.commands.menu_cli.inventory_cli.main", return_value=0)
    def test_inventory_displays_wait_message_before_qualys_call(
        self,
        mock_inventory_main,
    ) -> None:
        """Tell the operator that the Qualys inventory request is active."""
        output = Mock()
        menu = WasOperatorMenu(
            input_function=Mock(side_effect=["1", "", "3"]),
            output_function=output,
        )

        menu.qualys_menu()

        mock_inventory_main.assert_called_once_with([])
        output.assert_any_call(
            "Querying Qualys for stakeholder inventory. "
            "This may take several minutes; please wait..."
        )


if __name__ == "__main__":
    unittest.main()
