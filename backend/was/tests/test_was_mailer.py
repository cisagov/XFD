"""Tests for WAS mailer message and SES delivery helpers."""

# Standard Python Libraries
from contextlib import contextmanager
from datetime import date
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_mailer import email_reports
from was_mailer.message import (
    approved_analyst_recipients,
    build_assignee_digest_email,
    build_report_email,
    parse_email_addresses,
    recipient_addresses,
)
from was_reports.data.daily_report_tracker import AssigneeDigest, DailyReportTrackerRow
from was_reports.data.report_runs import ReportRunEmail


class WasMailerTests(unittest.TestCase):
    """Validate WAS mailer behavior."""

    def setUp(self) -> None:
        """Keep lease checks isolated from the database."""
        heartbeat = patch(
            "was_mailer.email_reports.touch_report_email_claim_by_id",
            return_value=True,
        )
        heartbeat.start()
        self.addCleanup(heartbeat.stop)

    def test_parse_email_addresses_accepts_semicolon_and_comma(self) -> None:
        """Parse recipient lists from common stakeholder formats."""
        addresses = parse_email_addresses(
            "one@example.gov; two@example.gov,three@example.gov"
        )

        self.assertEqual(
            addresses,
            ["one@example.gov", "two@example.gov", "three@example.gov"],
        )

    def test_recipient_addresses_uses_override_recipients(self) -> None:
        """Use test recipients instead of stakeholder recipients when supplied."""
        report_email = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path="/tmp/report.pdf",
            report_password=None,
            distro_email="real@example.gov",
            tech_poc_email="tech@example.gov",
            was_report_poc=None,
        )

        recipients = recipient_addresses(
            report_run_email=report_email,
            override_recipients="test@example.gov",
        )

        self.assertEqual(recipients, ["test@example.gov"])

    def test_recipient_addresses_combines_stakeholder_contacts(self) -> None:
        """Include both technical and distribution stakeholder recipients."""
        report_email = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path="/tmp/report.pdf",
            report_password=None,
            distro_email="team@example.gov",
            tech_poc_email="tech@example.gov",
            was_report_poc=None,
        )

        recipients = recipient_addresses(report_run_email=report_email)

        self.assertEqual(
            recipients,
            ["tech@example.gov", "team@example.gov"],
        )

    def test_build_report_email_attaches_pdf_without_password(self) -> None:
        """Build the report email without exposing the stakeholder password."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
            )

        self.assertEqual(message["From"], "sender@example.gov")
        self.assertEqual(message["To"], "recipient@example.gov")
        self.assertEqual(message["Subject"], "TAG1 WAS Results")
        self.assertNotIn("password123", message.as_string())
        self.assertIn("TAG1_report_2026-08-26.pdf", message.as_string())

    def test_build_all_nws_email_has_no_attachment(self) -> None:
        """Send an All NWS notice without inventing a PDF attachment."""
        message = build_report_email(
            source_email="sender@example.gov",
            recipients=["recipient@example.gov"],
            stakeholder_tag="TAG1",
            report_path=None,
            template="All NWS",
            assignee_name="Analyst Name",
            recent_nws="<br>https://example.gov",
        )

        self.assertEqual(len(list(message.iter_attachments())), 0)
        self.assertIn("No PDF report was generated", message.as_string())
        self.assertIn("Analyst Name", message.as_string())

    def test_build_report_email_lists_qualys_error_webapps(self) -> None:
        """Tell customers which applications lack updated Qualys results."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                qualys_error="https://error.example.gov<br>",
            )

        self.assertIn("do not have updated results", message.as_string())
        self.assertIn("https://error.example.gov", message.as_string())

    def test_build_report_email_requires_recipient(self) -> None:
        """Reject messages without recipients."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")

            with self.assertRaises(ValueError):
                build_report_email(
                    source_email="sender@example.gov",
                    recipients=[],
                    stakeholder_tag="TAG1",
                    report_path=report_path,
                )

    def test_build_assignee_digest_email_lists_tracker_rows(self) -> None:
        """Build a plain text assignee assignment digest."""
        digest = AssigneeDigest(
            assignee_id=3,
            assignee="Analyst",
            email="analyst@example.gov",
            rows=[
                DailyReportTrackerRow(
                    data_pull_date=date(2026, 8, 26),
                    tag="TAG1",
                    scan_name="Scan 1",
                    status="Finished",
                    result="Successful",
                    template="Results",
                    next_scan_date=date(2026, 9, 25),
                )
            ],
        )

        message = build_assignee_digest_email(
            source_email="sender@example.gov",
            recipients=["analyst@example.gov"],
            assignee_digest=digest,
        )

        self.assertEqual(message["To"], "analyst@example.gov")
        self.assertEqual(
            message["Subject"],
            "WAS Daily Tracker Assignments for Analyst",
        )
        body = message.get_body(preferencelist=("plain",)).get_content()

        self.assertIn("TAG1", body)
        self.assertIn("Total assigned rows: 1", body)
        self.assertIn("Reports sent: 0", body)
        self.assertIn("Manual reports: 0", body)
        self.assertIn("Reports pending: 1", body)
        self.assertNotIn("password123", body)
        self.assertIn("was-daily-tracker-analyst.csv", message.as_string())

    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_send_report_run_email_sends_with_ses(
        self,
        mock_claim_report_run_email,
        mock_mark_emailed,
    ) -> None:
        """Send a completed report through SES."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")
            mock_claim_report_run_email.return_value = ReportRunEmail(
                id=1,
                stakeholder_tag="TAG1",
                output_path=str(report_path),
                report_password="secret",
                distro_email="recipient@example.gov",
                tech_poc_email=None,
                was_report_poc=None,
            )
            ses_client = Mock()
            ses_client.send_raw_email.return_value = {"MessageId": "message-id"}

            message_id = email_reports.send_report_run_email(
                report_run_id=1,
                source_email="sender@example.gov",
                ses_client=ses_client,
                storage_mode="local",
                local_output_directory=directory,
            )

        self.assertEqual(message_id, "message-id")
        self.assertEqual(ses_client.send_raw_email.call_count, 1)
        mock_mark_emailed.assert_called_once_with(
            1, "message-id", email_claim_token=None
        )

    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_send_report_run_email_downloads_s3_report_temporarily(
        self,
        mock_claim_report_run_email,
        mock_mark_emailed,
    ) -> None:
        """Download an S3 report for SES and remove the temporary file."""
        mock_claim_report_run_email.return_value = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path="s3://reports/was_reports/2026-08-28/TAG1/1/report.pdf",
            report_password="secret",
            distro_email="recipient@example.gov",
            tech_poc_email=None,
            was_report_poc=None,
        )
        downloaded_paths = []
        s3_client = Mock()

        def download_file(bucket, key, destination):
            downloaded_path = Path(destination)
            downloaded_path.write_bytes(b"%PDF")
            downloaded_paths.append(downloaded_path)

        s3_client.download_file.side_effect = download_file
        ses_client = Mock()
        ses_client.send_raw_email.return_value = {"MessageId": "message-id"}

        with patch.dict(
            os.environ,
            {
                "WAS_REPORTS_BUCKET_NAME": "reports",
                "WAS_REPORTS_PREFIX": "was_reports",
            },
        ):
            message_id = email_reports.send_report_run_email(
                report_run_id=1,
                source_email="sender@example.gov",
                ses_client=ses_client,
                s3_client=s3_client,
            )

        self.assertEqual(message_id, "message-id")
        self.assertFalse(downloaded_paths[0].exists())
        mock_mark_emailed.assert_called_once_with(
            1, "message-id", email_claim_token=None
        )

    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_send_report_run_email_records_s3_download_failure(
        self,
        mock_claim_report_run_email,
        mock_mark_failed,
    ) -> None:
        """Record an email failure when the report cannot be read from S3."""
        mock_claim_report_run_email.return_value = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path="s3://reports/was_reports/2026-08-28/TAG1/1/report.pdf",
            report_password="secret",
            distro_email="recipient@example.gov",
            tech_poc_email=None,
            was_report_poc=None,
        )
        s3_client = Mock()
        s3_client.download_file.side_effect = RuntimeError("download failed")

        with patch.dict(
            os.environ,
            {
                "WAS_REPORTS_BUCKET_NAME": "reports",
                "WAS_REPORTS_PREFIX": "was_reports",
            },
        ):
            with self.assertRaises(RuntimeError):
                email_reports.send_report_run_email(
                    report_run_id=1,
                    source_email="sender@example.gov",
                    ses_client=Mock(),
                    s3_client=s3_client,
                )

        mock_mark_failed.assert_called_once_with(
            report_run_id=1,
            error_message="WAS report email delivery failed.",
            hold_for_manual_retry=False,
            email_claim_token=None,
        )

    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.LOGGER.info")
    @patch("was_mailer.email_reports.get_report_run_email_by_id")
    def test_send_report_run_email_dry_run_does_not_send(
        self,
        mock_get_report_run_email,
        mock_logger_info,
        mock_mark_emailed,
    ) -> None:
        """Build but do not send when dry-run is enabled."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")
            mock_get_report_run_email.return_value = ReportRunEmail(
                id=1,
                stakeholder_tag="TAG1",
                output_path=str(report_path),
                report_password="secret",
                distro_email="recipient@example.gov",
                tech_poc_email=None,
                was_report_poc=None,
            )
            ses_client = Mock()

            message_id = email_reports.send_report_run_email(
                report_run_id=1,
                source_email="sender@example.gov",
                dry_run=True,
                ses_client=ses_client,
                storage_mode="local",
                local_output_directory=directory,
            )

        self.assertIsNone(message_id)
        ses_client.send_raw_email.assert_not_called()
        mock_mark_emailed.assert_not_called()
        self.assertEqual(mock_logger_info.call_count, 1)

    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.LOGGER.error")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_send_report_run_email_records_failure(
        self,
        mock_claim_report_run_email,
        mock_logger_exception,
        mock_mark_failed,
    ) -> None:
        """Record a delivery failure when SES send fails."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")
            mock_claim_report_run_email.return_value = ReportRunEmail(
                id=1,
                stakeholder_tag="TAG1",
                output_path=str(report_path),
                report_password="secret",
                distro_email="recipient@example.gov",
                tech_poc_email=None,
                was_report_poc=None,
            )
            ses_client = Mock()
            ses_client.send_raw_email.side_effect = RuntimeError("send failed")

            with self.assertRaises(RuntimeError):
                email_reports.send_report_run_email(
                    report_run_id=1,
                    source_email="sender@example.gov",
                    ses_client=ses_client,
                    storage_mode="local",
                    local_output_directory=directory,
                )

        mock_mark_failed.assert_called_once_with(
            report_run_id=1,
            error_message="WAS report email delivery failed.",
            hold_for_manual_retry=True,
            email_claim_token=None,
        )
        self.assertEqual(mock_logger_exception.call_count, 1)

    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_send_report_run_email_does_not_retry_after_ses_acceptance(
        self,
        mock_claim_report_run_email,
        mock_mark_emailed,
        mock_mark_failed,
    ) -> None:
        """Leave an uncertain claim for manual review after SES accepts email."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")
            mock_claim_report_run_email.return_value = ReportRunEmail(
                id=1,
                stakeholder_tag="TAG1",
                output_path=str(report_path),
                report_password="secret",
                distro_email="recipient@example.gov",
                tech_poc_email=None,
                was_report_poc=None,
            )
            mock_mark_emailed.side_effect = RuntimeError("database failed")
            ses_client = Mock()
            ses_client.send_raw_email.return_value = {"MessageId": "message-id"}

            with self.assertRaises(RuntimeError):
                email_reports.send_report_run_email(
                    report_run_id=1,
                    source_email="sender@example.gov",
                    ses_client=ses_client,
                    storage_mode="local",
                    local_output_directory=directory,
                )

        self.assertTrue(mock_mark_failed.call_args.kwargs["hold_for_manual_retry"])

    @patch("was_mailer.email_reports.send_report_run_email")
    @patch("was_mailer.email_reports.list_report_runs_ready_for_email_from_db")
    def test_send_ready_report_emails_sends_each_ready_run(
        self,
        mock_list_ready,
        mock_send_email,
    ) -> None:
        """Send one email for each ready completed report run."""
        mock_list_ready.return_value = [
            ReportRunEmail(
                id=1,
                stakeholder_tag="TAG1",
                output_path="/tmp/report1.pdf",
                report_password=None,
                distro_email="one@example.gov",
                tech_poc_email=None,
                was_report_poc=None,
            ),
            ReportRunEmail(
                id=2,
                stakeholder_tag="TAG2",
                output_path="/tmp/report2.pdf",
                report_password=None,
                distro_email="two@example.gov",
                tech_poc_email=None,
                was_report_poc=None,
            ),
        ]
        mock_send_email.side_effect = ["message-1", "message-2"]

        sent_count = email_reports.send_ready_report_emails(
            source_email="sender@example.gov",
            limit=2,
        )

        self.assertEqual(sent_count, 2)
        self.assertEqual(mock_send_email.call_count, 2)
        mock_list_ready.assert_called_once_with(
            limit=2,
            include_previous_failures=False,
            stakeholder_tag=None,
        )

    @patch("was_mailer.email_reports.recover_stale_report_operations_in_db")
    @patch("was_mailer.email_reports.send_ready_report_emails")
    def test_main_all_ready_uses_batch_mode(
        self,
        mock_send_ready,
        mock_recover_stale,
    ) -> None:
        """Route all-ready CLI mode to the batch mailer."""
        exit_code = email_reports.main(
            [
                "--all-ready",
                "--source-email",
                "sender@example.gov",
                "--test-recipients",
                "test@example.gov",
                "--dry-run",
                "--limit",
                "1",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_recover_stale.assert_called_once_with()
        mock_send_ready.assert_called_once_with(
            source_email="sender@example.gov",
            override_recipients="test@example.gov",
            dry_run=True,
            limit=1,
            include_previous_failures=False,
        )

    @patch("was_mailer.email_reports.recover_stale_report_operations_in_db")
    @patch("was_mailer.email_reports.send_ready_assignee_digests")
    def test_main_assignee_digests_routes_to_digest_mode(
        self,
        mock_send_digests,
        mock_recover_stale,
    ) -> None:
        """Route assignee digest CLI mode to the digest mailer."""
        exit_code = email_reports.main(
            [
                "--assignee-digests",
                "--source-email",
                "sender@example.gov",
                "--test-recipients",
                "test@example.gov",
                "--dry-run",
                "--data-pull-date",
                "2026-08-26",
                "--limit",
                "5",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_recover_stale.assert_called_once_with()
        mock_send_digests.assert_called_once_with(
            source_email="sender@example.gov",
            override_recipients="test@example.gov",
            dry_run=True,
            data_pull_date=date(2026, 8, 26),
            limit=5,
            include_previous_failures=False,
        )

    @patch("was_mailer.email_reports.approved_analyst_recipients")
    @patch("was_mailer.email_reports.finish_assignee_digest_rows")
    @patch("was_mailer.email_reports.claim_assignee_digest_rows", return_value=True)
    def test_send_assignee_digest_email_sends_with_ses(
        self, mock_claim, mock_finish, mock_recipients
    ) -> None:
        """Finish only the exact claimed snapshot using its ownership token."""
        mock_recipients.return_value = ["analyst@example.gov"]
        digest = AssigneeDigest(
            assignee_id=3,
            assignee="Analyst",
            email="analyst@example.gov",
            rows=[DailyReportTrackerRow(id=81, data_pull_date=date(2026, 8, 26))],
        )
        ses_client = Mock()
        ses_client.send_raw_email.return_value = {"MessageId": "message-id"}
        result = email_reports.send_assignee_digest_email(
            digest, "sender@example.gov", ses_client=ses_client
        )
        self.assertEqual(result, "message-id")
        row_ids, token = mock_claim.call_args.args
        self.assertEqual(row_ids, [81])
        mock_finish.assert_called_once_with(row_ids, token, message_id="message-id")


class DeliveryPolicyTests(unittest.TestCase):
    """Cover purpose enforcement and snapshot claim failure boundaries."""

    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_completion_follows_heartbeat_shutdown(self, claim, finish, failed):
        """Terminal status must not invalidate a still-running heartbeat."""
        claim.return_value = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path=None,
            report_password=None,
            distro_email="customer@example.gov",
            tech_poc_email=None,
            was_report_poc=None,
            template="All NWS",
            email_claim_token="token",
        )
        events = []

        @contextmanager
        def heartbeat_context(**kwargs):
            """Assert final status has not changed at the last heartbeat tick."""
            events.append("heartbeat-start")
            yield
            finish.assert_not_called()
            events.append("heartbeat-stop")

        def finish_delivery(*args, **kwargs):
            """Verify the heartbeat is stopped before terminal persistence."""
            self.assertEqual(events[-1], "heartbeat-stop")
            events.append("sent")

        finish.side_effect = finish_delivery
        client = Mock()
        client.send_raw_email.return_value = {"MessageId": "message"}
        with patch.object(email_reports, "operation_heartbeat", heartbeat_context):
            self.assertEqual(
                email_reports.send_report_run_email(
                    1, "sender@example.gov", ses_client=client
                ),
                "message",
            )
        self.assertEqual(events, ["heartbeat-start", "heartbeat-stop", "sent"])
        failed.assert_not_called()

    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_post_send_heartbeat_loss_is_held(self, claim, finish, failed):
        """Lease uncertainty after SES acceptance must not become retryable."""
        claim.return_value = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path=None,
            report_password=None,
            distro_email="customer@example.gov",
            tech_poc_email=None,
            was_report_poc=None,
            template="All NWS",
            email_claim_token="token",
        )

        @contextmanager
        def lost_heartbeat(**kwargs):
            """Simulate ownership loss while waiting for SES completion."""
            yield
            raise RuntimeError("lease lost")

        client = Mock()
        client.send_raw_email.return_value = {"MessageId": "message"}
        with patch.object(email_reports, "operation_heartbeat", lost_heartbeat):
            with self.assertRaises(RuntimeError):
                email_reports.send_report_run_email(
                    1, "sender@example.gov", ses_client=client
                )
        finish.assert_not_called()
        self.assertTrue(failed.call_args.kwargs["hold_for_manual_retry"])
        self.assertEqual(failed.call_args.kwargs["email_claim_token"], "token")

    @patch("was_mailer.message.list_active_assignee_emails_from_db")
    def test_analyst_policy_rejects_missing_and_unapproved_recipients(self, active):
        """Never fall back to customer contacts for an analyst report."""
        active.return_value = ["analyst@example.gov"]
        report = SimpleNamespace(delivery_purpose="analyst")
        for recipients in (None, "", "customer@example.gov", "not-an-email"):
            with self.subTest(recipients=recipients), self.assertRaises(ValueError):
                recipient_addresses(report, recipients)
        self.assertEqual(
            approved_analyst_recipients("ANALYST@example.gov;analyst@example.gov"),
            ["ANALYST@example.gov"],
        )

    def test_unknown_purpose_fails_closed(self):
        """Reject unrecognized persisted policy rather than defaulting to customers."""
        with self.assertRaises(ValueError):
            recipient_addresses(SimpleNamespace(delivery_purpose="unknown"), "a@b.gov")

    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.touch_report_email_claim_by_id", return_value=True)
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_held_customer_preserves_customer_template(self, claim, touch, finish):
        """Claim permission does not change the persisted delivery purpose."""
        claim.return_value = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path=None,
            report_password=None,
            distro_email="customer@example.gov",
            tech_poc_email=None,
            was_report_poc=None,
            template="All NWS",
            delivery_purpose="customer",
            email_claim_token="token",
        )
        client = Mock()
        client.send_raw_email.return_value = {"MessageId": "message"}
        email_reports.send_report_run_email(
            1, "sender@example.gov", allow_held=True, ses_client=client
        )
        message_bytes = client.send_raw_email.call_args.kwargs["RawMessage"]["Data"]
        self.assertIn(b"No PDF report was generated", message_bytes)
        self.assertNotIn(b"Analyst Copy", message_bytes)
        finish.assert_called_once_with(1, "message", email_claim_token="token")

    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_direct_analyst_delivery_requires_explicit_recipients(self, claim, failed):
        """Direct mailer callers cannot bypass analyst authorization."""
        claim.return_value = SimpleNamespace(
            delivery_purpose="analyst", email_claim_token="token"
        )
        client = Mock()
        with self.assertRaises(ValueError):
            email_reports.send_report_run_email(
                1, "sender@example.gov", ses_client=client
            )
        client.send_raw_email.assert_not_called()
        self.assertTrue(failed.call_args.kwargs["hold_for_manual_retry"])

    def digest(self):
        """Return a minimal persisted snapshot for lifecycle tests."""
        return SimpleNamespace(
            assignee_id=3,
            email="analyst@example.gov",
            rows=[
                SimpleNamespace(id=81, digest_revision=0),
                SimpleNamespace(id=82, digest_revision=0),
            ],
        )

    @patch("was_mailer.email_reports.claim_assignee_digest_rows", return_value=False)
    @patch("was_mailer.email_reports.finish_assignee_digest_rows")
    def test_digest_claim_conflict_does_not_send_or_finish(self, finish, claim):
        """A competing sender cannot finish or send an unowned snapshot."""
        client = Mock()
        self.assertIsNone(
            email_reports.send_assignee_digest_email(
                self.digest(), "sender@example.gov", ses_client=client
            )
        )
        client.send_raw_email.assert_not_called()
        finish.assert_not_called()

    @patch("was_mailer.email_reports.claim_assignee_digest_rows", return_value=True)
    @patch("was_mailer.email_reports.finish_assignee_digest_rows")
    @patch(
        "was_mailer.email_reports.approved_analyst_recipients",
        return_value=["analyst@example.gov"],
    )
    @patch("was_mailer.email_reports.build_assignee_digest_email")
    def test_digest_transport_uncertainty_is_held(
        self, build, recipients, finish, claim
    ):
        """A timeout after send begins must not enter automatic retries."""
        client = Mock()
        client.send_raw_email.side_effect = TimeoutError("sensitive detail")
        with self.assertRaises(TimeoutError):
            email_reports.send_assignee_digest_email(
                self.digest(), "sender@example.gov", ses_client=client
            )
        row_ids, token = claim.call_args.args
        finish.assert_called_once_with(
            row_ids,
            token,
            error_message="WAS assignee digest email delivery failed.",
            uncertain=True,
        )

    @patch("was_mailer.email_reports.claim_assignee_digest_rows", return_value=True)
    @patch("was_mailer.email_reports.finish_assignee_digest_rows")
    @patch(
        "was_mailer.email_reports.approved_analyst_recipients",
        return_value=["analyst@example.gov"],
    )
    @patch("was_mailer.email_reports.build_assignee_digest_email")
    def test_digest_completion_failure_is_uncertain(
        self, build, recipients, finish, claim
    ):
        """An accepted delivery with a failed write stays out of automatic retries."""
        client = Mock()
        client.send_raw_email.return_value = {"MessageId": "message"}
        finish.side_effect = [RuntimeError(), None]
        with self.assertRaises(RuntimeError):
            email_reports.send_assignee_digest_email(
                self.digest(), "sender@example.gov", ses_client=client
            )
        self.assertTrue(finish.call_args.kwargs["uncertain"])
        self.assertEqual(client.send_raw_email.call_count, 1)

    @patch("was_mailer.email_reports.claim_assignee_digest_rows", return_value=True)
    @patch("was_mailer.email_reports.finish_assignee_digest_rows")
    @patch(
        "was_mailer.email_reports.approved_analyst_recipients", side_effect=ValueError()
    )
    def test_digest_pre_send_failure_is_retryable(self, recipients, finish, claim):
        """Persist known pre-send failure without marking uncertainty."""
        with self.assertRaises(ValueError):
            email_reports.send_assignee_digest_email(
                self.digest(), "sender@example.gov"
            )
        self.assertFalse(finish.call_args.kwargs["uncertain"])

    @patch("was_mailer.email_reports.list_ready_assignee_digests_from_db")
    @patch("was_mailer.email_reports.send_assignee_digest_email")
    def test_digest_batch_continues_and_retries_are_explicit(self, send, listing):
        """One failed item does not prevent delivery to the next assignee."""
        listing.return_value = [self.digest(), self.digest()]
        send.side_effect = [RuntimeError(), "message"]
        self.assertEqual(
            email_reports.send_ready_assignee_digests(
                "sender@example.gov", include_previous_failures=True
            ),
            1,
        )
        self.assertTrue(listing.call_args.kwargs["include_previous_failures"])
        self.assertEqual(send.call_count, 2)

    @patch("was_mailer.email_reports.list_report_runs_ready_for_email_from_db")
    @patch("was_mailer.email_reports.send_report_run_email")
    def test_report_batch_continues_after_item_error(self, send, listing):
        """A failed run does not stop unrelated report deliveries."""
        listing.return_value = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        send.side_effect = [RuntimeError(), "message"]
        self.assertEqual(
            email_reports.send_ready_report_emails("sender@example.gov"), 1
        )
        self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
