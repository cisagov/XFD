"""Tests for the interactive WAS operator menu."""

# Standard Python Libraries
from datetime import date
import unittest
from unittest.mock import Mock, patch

# First-Party Libraries
from was_reports.commands.menu_cli import WasOperatorMenu
from was_reports.utils.operation_cancellation import (
    raise_if_operation_cancelled,
    request_operation_cancellation,
)


class WasOperatorMenuTests(unittest.TestCase):
    """Validate menu prompts and command delegation."""

    def build_menu(self, responses: list[str]) -> WasOperatorMenu:
        """Return a menu backed by deterministic test input."""
        return WasOperatorMenu(
            input_function=Mock(side_effect=responses),
            output_function=Mock(),
            secret_input_function=Mock(),
        )

    def test_main_menu_quits(self) -> None:
        """Exit cleanly from the numbered main menu."""
        menu = self.build_menu(["5"])

        exit_code = menu.run()

        self.assertEqual(exit_code, 0)

    def test_execute_returns_to_menu_after_safe_cancellation(self) -> None:
        """Handle cooperative cancellation without exiting the menu process."""
        menu = self.build_menu([])

        def cancel_at_checkpoint() -> int:
            """Request cancellation and enter a safe checkpoint."""
            request_operation_cancellation()
            raise_if_operation_cancelled()
            return 0

        exit_code = menu.execute(
            "test operation",
            cancel_at_checkpoint,
            cancellable=True,
        )

        self.assertEqual(exit_code, 130)
        menu.output.assert_any_call(
            "Operation cancelled safely. Returning to the previous menu."
        )

    @patch("was_reports.commands.menu_cli.signal.signal")
    @patch("was_reports.commands.menu_cli.signal.getsignal", return_value=object())
    def test_control_c_requests_safe_cancellation_and_restores_handler(
        self,
        mock_get_signal,
        mock_set_signal,
    ) -> None:
        """Keep Ctrl+C inside the menu during a cancellable operation."""
        menu = self.build_menu([])

        def cancel_from_registered_handler() -> int:
            """Invoke the temporary SIGINT handler and reach a safe checkpoint."""
            interrupt_handler = mock_set_signal.call_args_list[0].args[1]
            interrupt_handler(None, None)
            raise_if_operation_cancelled()
            return 0

        exit_code = menu.execute(
            "test operation",
            cancel_from_registered_handler,
            cancellable=True,
        )

        self.assertEqual(exit_code, 130)
        mock_get_signal.assert_called_once()
        self.assertEqual(mock_set_signal.call_count, 2)
        menu.output.assert_any_call(
            "Operation cancelled safely. Returning to the previous menu."
        )

    def test_keyboard_interrupt_returns_to_previous_menu(self) -> None:
        """Keep an unexpected operation interrupt from terminating the menu."""
        menu = self.build_menu([])

        exit_code = menu.execute(
            "test operation",
            Mock(side_effect=KeyboardInterrupt),
        )

        self.assertEqual(exit_code, 130)
        menu.output.assert_any_call(
            "Operation interrupted. Returning to the previous menu."
        )

    def test_report_menu_uses_five_or_b_to_return(self) -> None:
        """Return to the main menu using either documented report-menu choice."""
        for selection in ("5", "b"):
            with self.subTest(selection=selection):
                menu = self.build_menu([selection])

                menu.report_menu()

                displayed_options = [
                    call.args[0]
                    for call in menu.output.call_args_list
                    if call.args
                ]
                self.assertIn(
                    "4) Generate a new on-demand report (S3, optional email)",
                    displayed_options,
                )
                self.assertIn("5) Back to main menu", displayed_options)

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
    def test_complete_batch_requires_recipient_override(
        self,
        mock_batch_main,
    ) -> None:
        """Route every complete-batch email to the explicit test recipient."""
        menu = self.build_menu(["1", "25", "analyst@example.gov", "y", ""])

        menu.run_daily_batch()

        mock_batch_main.assert_called_once_with(
            [
                "--recent-scans",
                "--create-missing-password",
                "--continue-on-error",
                "--send-email",
                "--send-assignee-digests",
                "--limit",
                "25",
                "--test-recipients",
                "analyst@example.gov",
            ]
        )
        menu.output.assert_any_call(
            "Customer addresses will not be used. Successful tracker rows will be "
            "recorded as sent."
        )
        menu.output.assert_any_call("This batch is limited to 25 reports.")

    @patch("was_reports.commands.menu_cli.batch_runner.main", return_value=0)
    def test_complete_batch_requires_typed_customer_confirmation(
        self,
        mock_batch_main,
    ) -> None:
        """Require an explicit phrase before delivering reports to customers."""
        menu = self.build_menu(["2", "", "SEND CUSTOMER REPORTS", ""])

        menu.run_daily_batch()

        mock_batch_main.assert_called_once_with(
            [
                "--recent-scans",
                "--create-missing-password",
                "--continue-on-error",
                "--send-email",
                "--send-assignee-digests",
            ]
        )
        menu.output.assert_any_call("This batch will process all eligible reports.")

    @patch("was_reports.commands.menu_cli.batch_runner.main", return_value=0)
    def test_complete_batch_cancels_customer_delivery_without_phrase(
        self,
        mock_batch_main,
    ) -> None:
        """Do not start customer delivery without the exact safety phrase."""
        menu = self.build_menu(["2", "", "no"])

        menu.run_daily_batch()

        mock_batch_main.assert_not_called()
        menu.output.assert_any_call("Operation cancelled.")

    @patch("was_reports.commands.menu_cli.batch_runner.main", return_value=0)
    def test_complete_batch_cancel_does_not_prompt_for_limit(
        self,
        mock_batch_main,
    ) -> None:
        """Cancel immediately before collecting batch execution settings."""
        menu = self.build_menu(["3"])

        menu.run_daily_batch()

        mock_batch_main.assert_not_called()
        self.assertEqual(menu.input.call_count, 1)

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

    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli.STAKEHOLDER_EDIT_COLUMNS",
        ("comments", "retired"),
    )
    @patch("was_reports.commands.menu_cli.stakeholders_cli.main", return_value=0)
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli."
        "display_stakeholder_record"
    )
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli."
        "get_stakeholder_record_by_tag"
    )
    def test_stakeholder_row_update_displays_then_updates_selected_fields(
        self,
        mock_get_record,
        mock_display_record,
        mock_stakeholders_main,
    ) -> None:
        """Cycle through current values and apply only changed fields."""
        record = {"comments": "Old comment", "retired": True}
        mock_get_record.return_value = record
        menu = self.build_menu(
            [
                "TAG1",
                "",
                "Updated comment",
                "false",
                "y",
                "",
            ]
        )

        menu.update_stakeholder_row()

        mock_get_record.assert_called_once_with("TAG1")
        mock_display_record.assert_called_once_with(record, output=menu.output)
        mock_stakeholders_main.assert_called_once_with(
            [
                "update",
                "--tag",
                "TAG1",
                "--set",
                "comments=Updated comment",
                "--set",
                "retired=false",
                "--confirm",
            ]
        )

    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli.STAKEHOLDER_EDIT_COLUMNS",
        ("comments", "retired"),
    )
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli."
        "display_stakeholder_record"
    )
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli."
        "get_stakeholder_record_by_tag"
    )
    def test_stakeholder_row_update_keeps_prefilled_values_on_enter(
        self,
        mock_get_record,
        mock_display_record,
    ) -> None:
        """Treat Enter as acceptance of each current stakeholder value."""
        record = {"comments": None, "retired": False}
        mock_get_record.return_value = record
        menu = self.build_menu(["TAG1", "", "", "", ""])

        menu.update_stakeholder_row()

        mock_display_record.assert_called_once_with(record, output=menu.output)
        menu.output.assert_any_call("No stakeholder changes were entered.")

    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli.STAKEHOLDER_EDIT_COLUMNS",
        ("comments",),
    )
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli."
        "display_stakeholder_record"
    )
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli."
        "get_stakeholder_record_by_tag"
    )
    def test_stakeholder_row_update_can_print_complete_field(
        self,
        mock_get_record,
        mock_display_record,
    ) -> None:
        """Print a selected field without the table width truncation."""
        full_comment = "Complete stakeholder comment " * 5
        mock_get_record.return_value = {"comments": full_comment}
        menu = self.build_menu(
            [
                "TAG1",
                "comments",
                "",
                "",
                "",
            ]
        )

        menu.update_stakeholder_row()

        menu.output.assert_any_call("Full value for comments:")
        menu.output.assert_any_call(full_comment)

    @patch("was_reports.commands.menu_cli.stakeholders_cli.main", return_value=0)
    def test_sensitive_export_requires_typed_confirmation(
        self,
        mock_stakeholders_main,
    ) -> None:
        """Require a typed phrase before exporting report passwords."""
        menu = self.build_menu(["1", "", "y", "EXPORT PASSWORDS", ""])

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

    @patch(
        "was_reports.commands.menu_cli.report_generator.rotate_report_password",
        return_value="NewPassword123!",
    )
    def test_password_rotation_displays_new_password(
        self,
        mock_rotate_password,
    ) -> None:
        """Display the generated password only after a successful rotation."""
        menu = self.build_menu(["TAG1", "y", ""])

        menu.rotate_stakeholder_password()

        mock_rotate_password.assert_called_once_with("TAG1")
        menu.output.assert_any_call(
            "Operation completed successfully. The new password is "
            "NewPassword123!"
        )

    @patch(
        "was_reports.commands.menu_cli.report_generator.lookup_report_password",
        return_value="StoredPassword123!",
    )
    def test_password_retrieval_displays_password_after_confirmation(
        self,
        mock_lookup_password,
    ) -> None:
        """Retrieve a stored password by exact stakeholder tag."""
        menu = self.build_menu(["TAG1", "y", ""])

        menu.retrieve_stakeholder_password()

        mock_lookup_password.assert_called_once_with("TAG1")
        menu.output.assert_any_call(
            "The report password for TAG1 is StoredPassword123!"
        )

    @patch(
        "was_reports.commands.menu_cli.report_generator.lookup_report_password",
        return_value=None,
    )
    def test_password_retrieval_reports_missing_password(
        self,
        mock_lookup_password,
    ) -> None:
        """Explain when the selected tag has no configured password."""
        menu = self.build_menu(["TAG1", "y", ""])

        menu.retrieve_stakeholder_password()

        mock_lookup_password.assert_called_once_with("TAG1")
        menu.output.assert_any_call(
            "No report password is configured for stakeholder tag TAG1."
        )

    def test_stakeholder_menu_lists_password_operations_before_back(self) -> None:
        """Expose stored and customer-provided password menu operations."""
        menu = self.build_menu(["9"])

        menu.stakeholder_menu()

        displayed_options = [
            call.args[0] for call in menu.output.call_args_list if call.args
        ]
        self.assertIn(
            "7) Retrieve a stakeholder report password",
            displayed_options,
        )
        self.assertIn(
            "8) Add or replace a customer-provided report password",
            displayed_options,
        )
        self.assertIn("9) Back to main menu", displayed_options)

    def test_stakeholder_menu_routes_password_retrieval(self) -> None:
        """Route stakeholder menu option seven to password retrieval."""
        menu = self.build_menu(["7", "9"])
        menu.retrieve_stakeholder_password = Mock()

        menu.stakeholder_menu()

        menu.retrieve_stakeholder_password.assert_called_once_with()

    def test_stakeholder_menu_routes_customer_password_update(self) -> None:
        """Route stakeholder menu option eight to customer password storage."""
        menu = self.build_menu(["8", "9"])
        menu.set_customer_provided_password = Mock()

        menu.stakeholder_menu()

        menu.set_customer_provided_password.assert_called_once_with()

    @patch(
        "was_reports.commands.menu_cli.report_generator.set_report_password",
        return_value="CustomerPassword123!",
    )
    def test_customer_provided_password_is_hidden_confirmed_and_stored(
        self,
        mock_set_password,
    ) -> None:
        """Store a matching customer password without displaying its value."""
        menu = self.build_menu(["TAG1", "y", ""])
        menu.secret_input.side_effect = [
            "CustomerPassword123!",
            "CustomerPassword123!",
        ]

        menu.set_customer_provided_password()

        mock_set_password.assert_called_once_with("TAG1", "CustomerPassword123!")
        menu.output.assert_any_call(
            "Operation completed successfully. The customer-provided report "
            "password was stored for TAG1."
        )
        displayed_output = "\n".join(
            call.args[0] for call in menu.output.call_args_list if call.args
        )
        self.assertNotIn("CustomerPassword123!", displayed_output)

    @patch("was_reports.commands.menu_cli.report_generator.set_report_password")
    def test_customer_provided_password_mismatch_makes_no_change(
        self,
        mock_set_password,
    ) -> None:
        """Reject mismatched hidden password entries before database access."""
        menu = self.build_menu(["TAG1", ""])
        menu.secret_input.side_effect = ["FirstPassword123!", "SecondPassword123!"]

        menu.set_customer_provided_password()

        mock_set_password.assert_not_called()
        menu.output.assert_any_call("Passwords do not match. No change was made.")

    @patch("was_reports.commands.menu_cli.report_generator.set_report_password")
    def test_customer_provided_password_explains_policy_failure(
        self,
        mock_set_password,
    ) -> None:
        """Give the operator a specific policy error without storing the password."""
        menu = self.build_menu(["TAG1", ""])
        menu.secret_input.side_effect = ["weak", "weak"]

        menu.set_customer_provided_password()

        mock_set_password.assert_not_called()
        menu.output.assert_any_call(
            "Password not accepted: The password must contain at least 16 characters."
        )

    @patch("was_reports.commands.menu_cli.stakeholders_cli.main", return_value=0)
    def test_stakeholder_export_can_use_s3(self, mock_stakeholders_main) -> None:
        """Select direct S3 delivery from the stakeholder export menu."""
        menu = self.build_menu(["2", "n", ""])

        menu.export_stakeholders()

        mock_stakeholders_main.assert_called_once_with(["export-csv", "--s3"])

    @patch("was_reports.commands.menu_cli.stakeholders_cli.main", return_value=0)
    def test_stakeholder_export_can_email_assignee(
        self,
        mock_stakeholders_main,
    ) -> None:
        """Select an approved assignee email destination from the menu."""
        menu = self.build_menu(["3", "analyst@example.gov", "n", ""])

        menu.export_stakeholders()

        mock_stakeholders_main.assert_called_once_with(
            [
                "export-csv",
                "--email-assignee",
                "analyst@example.gov",
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
            "WARNING: The full Qualys stakeholder inventory can take "
            "a long time to finish. Leave this operation running until "
            "the inventory or an error is displayed."
        )

    @patch("was_reports.commands.menu_cli.tracker_cli.main", return_value=0)
    def test_tracker_view_uses_default_row_limit(self, mock_tracker_main) -> None:
        """Display no more than 200 tracker rows when the limit is blank."""
        menu = self.build_menu(["", "", "", "", ""])

        menu.view_tracker()

        mock_tracker_main.assert_called_once_with(
            ["show", "--days-back", "7", "--limit", "200"]
        )

    @patch("was_reports.commands.menu_cli.tracker_cli.main", return_value=0)
    def test_manual_sent_date_displays_manual_rows_before_id(
        self,
        mock_tracker_main,
    ) -> None:
        """Show eligible manual rows before asking the operator for an ID."""
        menu = self.build_menu(
            ["", "Mina Salehi", "", "7", "", "y", ""]
        )

        menu.record_manual_sent_date()

        self.assertEqual(mock_tracker_main.call_count, 2)
        self.assertEqual(
            mock_tracker_main.call_args_list[0].args[0],
            [
                "show",
                "--days-back",
                "30",
                "--report-status",
                "manual",
                "--limit",
                "200",
                "--assignee",
                "Mina Salehi",
            ],
        )
        self.assertEqual(
            mock_tracker_main.call_args_list[1].args[0],
            [
                "mark-sent",
                "--tracker-id",
                "7",
                "--sent-date",
                date.today().isoformat(),
                "--confirm",
            ],
        )

    @patch("was_reports.commands.menu_cli.tracker_cli.main", return_value=0)
    def test_tracker_view_accepts_all_rows(self, mock_tracker_main) -> None:
        """Allow an operator to request every matching tracker row."""
        menu = self.build_menu(["30", "Analyst", "pending", "all", ""])

        menu.view_tracker()

        mock_tracker_main.assert_called_once_with(
            [
                "show",
                "--days-back",
                "30",
                "--limit",
                "all",
                "--assignee",
                "Analyst",
                "--report-status",
                "pending",
            ]
        )


if __name__ == "__main__":
    unittest.main()
