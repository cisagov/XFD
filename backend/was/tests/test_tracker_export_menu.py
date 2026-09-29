"""Regression tests for tracker export date-window prompts."""

# Standard Python Libraries
import unittest
from unittest.mock import call, Mock, patch

# First-Party Libraries
from was_reports.commands.menu_cli import WasOperatorMenu


class TrackerExportMenuTests(unittest.TestCase):
    """Validate bounded and full-table tracker export selections."""

    def menu(self, answers: list[str]) -> WasOperatorMenu:
        """Return an operator menu with deterministic input and no pause."""
        menu = WasOperatorMenu(
            input_function=Mock(side_effect=answers),
            output_function=Mock(),
            secret_input_function=Mock(),
        )
        menu.pause = Mock()
        return menu

    @patch("was_reports.commands.menu_cli.tracker_cli.main", return_value=0)
    def test_export_all_omits_date_filter(self, run: Mock) -> None:
        """Export the entire tracker table when the operator enters all."""
        menu = self.menu(["1", "", "all", "", "y"])

        menu.export_tracker()

        run.assert_called_once_with(
            [
                "export-csv",
                "--output",
                "/output/was-daily-tracker.csv",
            ]
        )

    @patch("was_reports.commands.menu_cli.tracker_cli.main", return_value=0)
    def test_export_numeric_days_preserves_date_filter(self, run: Mock) -> None:
        """Continue forwarding nonnegative numeric lookback values."""
        menu = self.menu(["1", "", "0", "", "y"])

        menu.export_tracker()

        arguments = run.call_args.args[0]
        self.assertEqual(arguments[arguments.index("--days-back") + 1], "0")

    def test_days_back_reprompts_for_invalid_values(self) -> None:
        """Explain invalid input before accepting the full-table option."""
        menu = self.menu(["invalid", "-1", "ALL"])

        days_back = menu.prompt_days_back_or_all(
            "Days back [7, or all]: ",
            default=7,
        )

        self.assertIsNone(days_back)
        self.assertEqual(
            menu.output.call_args_list,
            [
                call(
                    "Enter a whole number of zero or greater, or all."
                ),
                call(
                    "Enter a whole number of zero or greater, or all."
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
