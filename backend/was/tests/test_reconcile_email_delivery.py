"""Tests for guarded held-email delivery reconciliation."""

# Standard Python Libraries
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import reconcile_email_delivery
from was_reports.data.report_runs import HeldEmailReconciliationPreview


def eligible_preview() -> HeldEmailReconciliationPreview:
    """Return a representative eligible held customer delivery."""
    return HeldEmailReconciliationPreview(
        report_run_id=3703,
        stakeholder_tag="NEWGI",
        report_status="completed",
        email_status="held",
        delivery_purpose="customer",
        emailed_at=None,
        email_claimed_at=None,
        source_tracker_id=260866,
        tracker_report_sent_date=None,
        eligible=True,
        ineligible_reason=None,
    )


class ReconcileEmailDeliveryTests(unittest.TestCase):
    """Validate explicit reconciliation and retry safety gates."""

    @patch.object(
        reconcile_email_delivery,
        "inspect_held_report_email_reconciliation_by_id",
        return_value=eligible_preview(),
    )
    def test_inspect_is_read_only(self, inspect) -> None:
        """Display eligibility without changing delivery state."""
        output = io.StringIO()

        with redirect_stdout(output):
            result = reconcile_email_delivery.main(
                ["inspect", "--report-run-id", "3703"]
            )

        self.assertEqual(result, 0)
        self.assertIn("Run 3703: eligible", output.getvalue())
        inspect.assert_called_once_with(3703)

    @patch.object(
        reconcile_email_delivery,
        "confirm_held_report_email_delivered_by_id",
    )
    @patch.object(
        reconcile_email_delivery,
        "inspect_held_report_email_reconciliation_by_id",
        return_value=eligible_preview(),
    )
    def test_confirm_delivered_records_state_without_sending(
        self,
        inspect,
        confirm_delivered,
    ) -> None:
        """A delivery confirmation updates state and never invokes SES."""
        result = reconcile_email_delivery.main(
            [
                "confirm-delivered",
                "--report-run-id",
                "3703",
                "--evidence-reference",
                "SES event reference 123",
                "--apply",
                "--confirm",
                reconcile_email_delivery.DELIVERY_CONFIRMED,
            ]
        )

        self.assertEqual(result, 0)
        inspect.assert_called_once_with(3703)
        confirm_delivered.assert_called_once_with(
            report_run_id=3703,
            reconciliation_reference="SES event reference 123",
        )

    @patch.object(reconcile_email_delivery, "send_report_run_email")
    @patch.object(
        reconcile_email_delivery,
        "reconciliation_recipient_scope",
        return_value="test-sha256:" + ("a" * 64),
    )
    @patch.object(
        reconcile_email_delivery,
        "confirm_held_report_email_not_delivered_by_id",
    )
    @patch.object(
        reconcile_email_delivery,
        "approved_analyst_recipients",
        return_value=["analyst@example.gov"],
    )
    @patch.object(
        reconcile_email_delivery,
        "inspect_held_report_email_reconciliation_by_id",
        return_value=eligible_preview(),
    )
    def test_confirmed_non_delivery_retries_only_through_special_claim(
        self,
        inspect,
        approved,
        confirm_not_delivered,
        recipient_scope_builder,
        send_report,
    ) -> None:
        """Authorize and claim one controlled test-recipient retry."""
        send_report.return_value = "message-123"
        confirm_not_delivered.return_value = "authorization-token"

        result = reconcile_email_delivery.main(
            [
                "retry-confirmed-undelivered",
                "--report-run-id",
                "3703",
                "--evidence-reference",
                "SES event confirms no delivery",
                "--test-recipients",
                "analyst@example.gov",
                "--source-email",
                "sender@example.gov",
                "--apply",
                "--confirm",
                reconcile_email_delivery.NONDELIVERY_CONFIRMED_RETRY,
            ]
        )

        self.assertEqual(result, 0)
        inspect.assert_called_once_with(3703)
        approved.assert_called_once_with("analyst@example.gov")
        recipient_scope = "test-sha256:" + ("a" * 64)
        recipient_scope_builder.assert_called_once_with("analyst@example.gov")
        confirm_not_delivered.assert_called_once_with(
            report_run_id=3703,
            reason="SES event confirms no delivery",
            recipient_scope=recipient_scope,
        )
        send_report.assert_called_once_with(
            report_run_id=3703,
            source_email="sender@example.gov",
            override_recipients="analyst@example.gov",
            held_reconciliation_token="authorization-token",
            held_reconciliation_scope=recipient_scope,
            delivery_purpose="customer",
        )

    def test_test_recipient_scope_is_order_independent_and_address_free(self) -> None:
        """Bind retries to recipients without storing their addresses."""
        with patch(
            "was_mailer.email_reports.approved_analyst_recipients",
            side_effect=[
                ["second@example.gov", "first@example.gov"],
                ["first@example.gov", "second@example.gov"],
            ],
        ):
            first_scope = reconcile_email_delivery._recipient_scope(
                "second@example.gov,first@example.gov",
                False,
            )
            second_scope = reconcile_email_delivery._recipient_scope(
                "first@example.gov,second@example.gov",
                False,
            )

        self.assertEqual(first_scope, second_scope)
        self.assertTrue(first_scope.startswith("test-sha256:"))
        self.assertNotIn("example.gov", first_scope)

    @patch.object(reconcile_email_delivery, "send_report_run_email")
    @patch.object(
        reconcile_email_delivery,
        "confirm_held_report_email_not_delivered_by_id",
    )
    @patch.object(
        reconcile_email_delivery,
        "inspect_held_report_email_reconciliation_by_id",
        return_value=eligible_preview(),
    )
    def test_customer_retry_requires_stronger_exact_confirmation(
        self,
        inspect,
        confirm_not_delivered,
        send_report,
    ) -> None:
        """Do not fall through to stored customer recipients accidentally."""
        with self.assertRaises(ValueError) as error_context:
            reconcile_email_delivery.main(
                [
                    "retry-confirmed-undelivered",
                    "--report-run-id",
                    "3703",
                    "--evidence-reference",
                    "SES event confirms no delivery",
                    "--use-stored-customer-recipients",
                    "--apply",
                    "--confirm",
                    reconcile_email_delivery.NONDELIVERY_CONFIRMED_RETRY,
                ]
            )

        self.assertIn(
            reconcile_email_delivery.NONDELIVERY_CONFIRMED_RETRY_CUSTOMERS,
            str(error_context.exception),
        )
        inspect.assert_called_once_with(3703)
        confirm_not_delivered.assert_not_called()
        send_report.assert_not_called()

    @patch.object(
        reconcile_email_delivery,
        "confirm_held_report_email_delivered_by_id",
    )
    @patch.object(
        reconcile_email_delivery,
        "inspect_held_report_email_reconciliation_by_id",
    )
    def test_blocked_preview_prevents_mutation(self, inspect, confirm) -> None:
        """A changed or already sent state cannot be reconciled."""
        preview = eligible_preview()
        inspect.return_value = HeldEmailReconciliationPreview(
            **{
                **preview.__dict__,
                "eligible": False,
                "ineligible_reason": "Email delivery is already recorded.",
            }
        )

        result = reconcile_email_delivery.main(
            [
                "confirm-delivered",
                "--report-run-id",
                "3703",
                "--evidence-reference",
                "mailbox evidence",
                "--apply",
                "--confirm",
                reconcile_email_delivery.DELIVERY_CONFIRMED,
            ]
        )

        self.assertEqual(result, 2)
        confirm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
