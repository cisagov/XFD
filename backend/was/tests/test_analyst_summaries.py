"""Offline regression tests for combined, secret-safe analyst summaries."""

import unittest
from unittest.mock import patch

from was_reports.reporting import analyst_summaries as summaries


class AnalystSummaryTests(unittest.TestCase):
    """Exercise content, persistence and duplicate delivery boundaries."""

    @patch.object(summaries, "list_functional_test_recipient_emails_from_db", return_value=[])
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute")
    def test_no_enabled_analysts_skips_delivery_without_claim(self, execute, client, recipients):
        """Disabling every analyst email must not prevent customer report work."""
        self.assertFalse(summaries._deliver(
            "batch", "final", "from@example.gov", None, "body", [], False
        ))
        execute.assert_not_called()
        client.assert_not_called()

    def test_counts_distinguish_unknown_from_zero(self):
        """Structured NWS and HTML target lists provide exact known counts."""
        counts = summaries.preflight_counts(
            [
                {
                    "template": "Action Required",
                    "nws": "10, 2, 1",
                    "qualys_error": "<ul><li>one</li><li>two</li></ul>",
                },
                {"template": "All NWS", "nws": "unknown", "qualys_error": "opaque"},
                {"template": "Results", "nws": "10"},
            ]
        )
        self.assertEqual(counts["reports"], 3)
        self.assertEqual(counts["nws_webapps"], 3)
        self.assertEqual(counts["nws_unknown"], 1)
        self.assertEqual(counts["error_webapps"], 2)
        self.assertEqual(counts["error_unknown"], 1)
        self.assertEqual(summaries.target_count("one<br>two<br>"), 2)
        self.assertEqual(summaries.target_count("<br>one<br>two<br>"), 2)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows", return_value=[])
    @patch.object(summaries, "_execute", return_value=[(8, None, 12)])
    def test_preflight_includes_tracker_duration_and_updated_count(
        self, execute, rows, deliver
    ):
        """Tracker outcomes are visible before any report workers begin."""
        summaries.send_tracker_summary("batch", [], "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertIn("Tracker time: 8 seconds; rows updated: 12; error: none", body)
        self.assertIn("reports: 0", body)

    @patch("was_mailer.email_reports.send_message", return_value="message-id")
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute", return_value=[("batch",)])
    @patch.object(summaries, "_recipients", return_value=["analyst@example.gov"])
    def test_success_sends_one_csv_message_and_finishes_claim(
        self, recipients, execute, client, send
    ):
        """One SES call contains the combined CSV without legacy secrets."""
        summaries._deliver(
            "batch",
            "final",
            "from@example.gov",
            None,
            "body",
            [{"id": 1, "legacy_password": "secret"}],
            False,
        )
        message = send.call_args.args[1]
        self.assertEqual(send.call_count, 1)
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertNotIn(b"secret", attachments[0].get_payload(decode=True))
        self.assertIn("summary_status='sent'", execute.call_args.args[0])

    def test_csv_deduplicates_and_excludes_passwords(self):
        """Allowlisted exports exclude secrets and neutralize spreadsheet formulas."""
        row = {"id": 1, "tag": "=formula", "legacy_password": "secret"}
        result = summaries.summary_csv([row, row])
        self.assertNotIn("secret", result)
        self.assertNotIn("legacy_password", result)
        self.assertIn("'=formula", result)
        self.assertEqual(len(result.splitlines()), 2)

    @patch.object(summaries, "_execute")
    def test_attempt_merge_preserves_generation_and_sanitizes_errors(self, execute):
        """Delivery-only outcomes cannot erase generation metrics or expose payloads."""
        summaries.record_report_attempt("batch", 1, 0, error=ValueError("secret"))
        query, parameters = execute.call_args.args
        self.assertIn("GREATEST", query)
        self.assertIn("generated OR", query)
        self.assertEqual(parameters[5], "ValueError")
        self.assertNotIn("secret", str(parameters))
        with self.assertRaises(ValueError):
            summaries.record_report_attempt("batch", 1, float("nan"))

    @patch.object(summaries, "approved_analyst_recipients")
    @patch.object(summaries, "list_functional_test_recipient_emails_from_db")
    def test_all_enabled_recipients_use_existing_resolver(self, configured, approved):
        """Use enabled recipients including inactive functional-test accounts."""
        configured.return_value = ["inactive@example.gov", "active@example.gov"]
        approved.return_value = configured.return_value
        self.assertEqual(len(summaries._recipients(None)), 2)
        approved.assert_called_once_with("inactive@example.gov;active@example.gov")
        approved.return_value = [
            "recipient{}@example.gov".format(index) for index in range(51)
        ]
        with self.assertRaises(ValueError):
            summaries._recipients(None)

    @patch("was_mailer.email_reports.send_message")
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute")
    @patch.object(summaries, "_recipients", return_value=["analyst@example.gov"])
    def test_claimed_or_held_phase_never_sends_again(
        self, recipients, execute, client, send
    ):
        """A pending-only database claim controls delivery concurrency."""
        execute.return_value = []
        self.assertFalse(
            summaries._deliver(
                "batch", "final", "from@example.gov", None, "body", [], False
            )
        )
        send.assert_not_called()
        self.assertIn("summary_status='pending'", execute.call_args.args[0])

    @patch("was_mailer.email_reports.send_message", side_effect=RuntimeError("secret"))
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute", return_value=[("batch",)])
    @patch.object(summaries, "_recipients", return_value=["analyst@example.gov"])
    def test_uncertain_send_is_held_without_payload(
        self, recipients, execute, client, send
    ):
        """SES failures never silently retry and never disclose exception messages."""
        with self.assertRaisesRegex(RuntimeError, "held for review: RuntimeError"):
            summaries._deliver(
                "batch", "final", "from@example.gov", None, "body", [], False
            )
        self.assertIn("summary_status='held'", execute.call_args.args[0])
        self.assertEqual(send.call_count, 1)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows")
    @patch.object(summaries, "_execute")
    def test_final_body_lists_only_open_manuals_and_csv_has_all(
        self, execute, rows, deliver
    ):
        """Ordinary report details stay in the CSV, not the final email body."""
        execute.side_effect = [[(90, 10, None)], [(12, True, True, None)]]
        rows.return_value = [
            {"id": 1, "tag": "ORDINARY", "open_manual": False},
            {
                "id": 2,
                "tag": "MANUAL",
                "assignee": "Analyst",
                "status": "ERROR",
                "open_manual": True,
            },
        ]
        summaries.send_batch_summary("batch", "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertNotIn("ORDINARY", body)
        self.assertIn("Analyst: tracker 2; tag MANUAL", body)
        self.assertIn("sent: 1; unsent: 0", body)
        self.assertEqual(len(deliver.call_args.args[5]), 2)

    @patch.object(summaries, "_execute", return_value=[])
    def test_manual_query_includes_unassigned_and_open_historical_rows(self, execute):
        """Final manual work is not restricted to this batch's generation window."""
        summaries._tracker_rows(batch_id="batch")
        query = execute.call_args.args[0]
        self.assertIn("LEFT JOIN was_stakeholders", query)
        self.assertIn("report_sent_date IS NULL", query)
        self.assertNotIn("legacy_password", query)
        self.assertNotIn("active IS TRUE", query)


if __name__ == "__main__":
    unittest.main()
