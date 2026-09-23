"""Tests for WAS mailer message and SES delivery helpers."""

# Standard Python Libraries
from contextlib import contextmanager
from datetime import date
from email import policy
from email.parser import BytesParser
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
    AnalystRecipientError,
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
        self.assertEqual(message["Subject"], "TAG1 - WAS Results")
        self.assertNotIn("password123", message.as_string())
        self.assertIn("TAG1_WAS_report_2026-08-26.pdf", message.as_string())
        html_body = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn('src="cid:cisa-logo"', html_body)
        inline_images = [
            part
            for part in message.walk()
            if part.get_content_type() == "image/png"
        ]
        self.assertEqual(len(inline_images), 1)
        self.assertEqual(
            inline_images[0].get_filename(),
            "CISA_logo_email.png",
        )

    def test_build_report_email_greets_customer_poc(self) -> None:
        """Address a customer report email to the configured WAS report POC."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                poc_name="Customer Name",
            )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertTrue(body.startswith("WAS Results for TAG1\n\nCustomer Name,\n"))

    def test_test_delivery_notice_keeps_original_recipients_out_of_headers(self):
        """Expose intended customer addresses only in redirected test bodies."""
        message = build_report_email(
            source_email="sender@example.gov", recipients=["tester@example.gov"],
            stakeholder_tag="TAG1", template="All NWS", report_path=None,
            test_original_recipients=["poc@example.gov", "team@example.gov"],
        )
        for content_type in ("plain", "html"):
            body = message.get_body(preferencelist=(content_type,)).get_content()
            self.assertIn("TEST DELIVERY ONLY", body)
            self.assertIn("Original customer recipient(s):", body)
            self.assertIn("poc@example.gov; team@example.gov", body)
        self.assertEqual(message["To"], "tester@example.gov")
        self.assertIsNone(message["Cc"])
        self.assertIsNone(message["Bcc"])
        headers = str(list(message.items()))
        self.assertNotIn("poc@example.gov", headers)
        self.assertNotIn("team@example.gov", headers)

    def test_test_delivery_notice_escapes_html_and_handles_missing_contacts(self):
        """Treat preview addresses as text and label unavailable customer contacts."""
        for originals, expected in (([], "Not available"), (["<unsafe>&"], "&lt;unsafe&gt;&amp;")):
            message = build_report_email(
                source_email="sender@example.gov", recipients=["tester@example.gov"],
                stakeholder_tag="TAG1", template="All NWS", report_path=None,
                test_original_recipients=originals,
            )
            body = message.get_body(preferencelist=("html",)).get_content()
            self.assertIn(expected, body)
            self.assertNotIn("<unsafe>", body)

    def test_production_email_has_no_test_delivery_notice(self):
        """Leave approved customer template bodies unchanged without test metadata."""
        message = build_report_email(
            source_email="sender@example.gov", recipients=["customer@example.gov"],
            stakeholder_tag="TAG1", template="All NWS", report_path=None,
        )
        for content_type in ("plain", "html"):
            body = message.get_body(preferencelist=(content_type,)).get_content()
            self.assertNotIn("TEST DELIVERY ONLY", body)
            self.assertNotIn("Original customer recipient(s):", body)

    @patch("was_mailer.message.approved_analyst_recipients")
    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_customer_override_displays_original_contacts_only_in_test_body(
        self, claim, finish, approved
    ):
        """Only redirected customer mail gets deduplicated original-recipient metadata."""
        approved.return_value = ["tester@example.gov"]
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")
            for purpose in ("customer", "analyst"):
                with self.subTest(purpose=purpose):
                    claim.return_value = ReportRunEmail(
                        id=1, stakeholder_tag="TAG1", output_path=str(report_path),
                        report_password=None, was_report_poc="Customer",
                        tech_poc_email="poc@example.gov; shared@example.gov",
                        distro_email="shared@example.gov, team@example.gov",
                        delivery_purpose=purpose,
                    )
                    client = Mock()
                    client.send_raw_email.return_value = {"MessageId": "message"}
                    email_reports.send_report_run_email(
                        1, "sender@example.gov", override_recipients="tester@example.gov",
                        ses_client=client, storage_mode="local",
                        local_output_directory=directory, delivery_purpose=purpose,
                    )
                    message = BytesParser(policy=policy.default).parsebytes(
                        client.send_raw_email.call_args.kwargs["RawMessage"]["Data"]
                    )
                    body = message.get_body(preferencelist=("plain",)).get_content()
                    if purpose == "customer":
                        self.assertIn("TEST DELIVERY ONLY", body)
                        self.assertIn(
                            "poc@example.gov; shared@example.gov; team@example.gov", body
                        )
                        self.assertEqual(body.count("shared@example.gov"), 1)
                    else:
                        self.assertNotIn("TEST DELIVERY ONLY", body)
                        self.assertNotIn("poc@example.gov", body)
                    self.assertEqual(message["To"], "tester@example.gov")
                    self.assertIsNone(message["Cc"])
                    self.assertIsNone(message["Bcc"])

    def test_build_report_email_uses_generic_analyst_salutation(self) -> None:
        """Do not address an analyst-only delivery to the customer POC."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["analyst@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                poc_name="Customer Name",
                analyst_delivery=True,
            )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertTrue(body.startswith("Hello,\n"))

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
        self.assertIn("could not be generated", message.as_string())
        self.assertIn("Analyst Name", message.as_string())
        self.assertIn("Web Application Scanning (WAS)", message.as_string())
        self.assertIn("reports@cyber.dhs.gov", message.as_string())

    def test_build_report_email_lists_qualys_error_webapps(self) -> None:
        """Tell customers which applications lack updated Qualys results."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                qualys_error="https://error.example.gov<br>",
            )

        self.assertIn("experienced an internal error", message.as_string())
        self.assertIn("https://error.example.gov", message.as_string())
        self.assertIn("date and time for an ad hoc scan", message.as_string())

    def test_results_email_uses_supplied_template_sections(self) -> None:
        """Compose a Results email from the supplied customer template sections."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                template="Results",
                next_scheduled=1790985600,
            )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertNotIn("review and revise your allowlist", body)
        self.assertIn("Attached is a report containing the results", body)
        self.assertIn("Appendix C: Attachments", body)
        self.assertNotIn("update your WAS report password", body)
        self.assertIn("If you have questions, please email at vulnerability@cisa.dhs.gov.", body)
        self.assertNotIn("If you have questions, please email at reports@cisa.dhs.gov.", body)
        self.assertIn("reports@cyber.dhs.gov", body)
        self.assertLess(
            body.index("Important Note:"),
            body.index(
                "If you have questions, please email at vulnerability@cisa.dhs.gov"
            ),
        )
        self.assertIn("Your next scan is scheduled for", body)
        self.assertNotIn("This may be due to:", body)

        html_body = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn('style="background-color:#ffff00"', html_body)
        self.assertIn("<strong>Important Note:</strong>", html_body)
        self.assertIn("<em>Attachment 7", html_body)
        self.assertIn("<u><em>will not</em></u>", html_body)
        self.assertIn("<strong>Additional details", html_body)
        self.assertIn("<u>double-click on the paper clip icon</u>", html_body)
        self.assertNotIn("scanner IP's have recently changed", html_body)
        self.assertIn(
            'href="https://www.cisa.gov/cyber-hygiene-services">',
            html_body,
        )

    def test_action_required_email_uses_conditional_nws_sections(self) -> None:
        """Add supplied inaccessible-target sections only when NWS data exists."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                template="Action Required",
                recent_nws="https://one.example.gov<br>https://two.example.gov<br>",
                nws_summary="5, 2, 0",
            )

        body = message.get_body(preferencelist=("plain",)).get_content()
        html_body = message.get_body(preferencelist=("html",)).get_content()
        self.assertIn("2 out of 5 web applications", body)
        self.assertNotIn("NWS means No Web Service", body)
        self.assertIn("https://one.example.gov", body)
        self.assertIn("This may be due to:", body)
        self.assertIn("two consecutive scans", body)
        self.assertIn(
            "<strong>2 </strong>out of " "<strong>5</strong> web applications",
            html_body,
        )
        self.assertNotIn(
            "<strong>Results indicate that",
            html_body,
        )

    def test_targets_removed_extends_action_required_sections(self) -> None:
        """Add removed targets and instructions for requesting replacements."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                template="Targets Removed",
                recent_nws="https://nws.example.gov<br>",
                nws_summary="5, 1, 1",
                remove_nws="https://removed.example.gov<br>",
            )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("https://nws.example.gov", body)
        self.assertIn("This may be due to:", body)
        self.assertIn("two consecutive times, and have been removed", body)
        self.assertIn("https://removed.example.gov", body)
        self.assertIn(
            "Please provide an updated list of targets to vulnerability@cisa.dhs.gov",
            body,
        )

    def test_all_nws_email_omits_report_only_sections(self) -> None:
        """Do not include attachment guidance when an All NWS run has no PDF."""
        message = build_report_email(
            source_email="sender@example.gov",
            recipients=["recipient@example.gov"],
            stakeholder_tag="TAG1",
            report_path=None,
            template="All NWS",
            recent_nws="https://example.gov<br>",
            nws_summary="1, 1, 0",
        )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertIn("could not be generated", body)
        self.assertIn("two consecutive scans", body)
        self.assertNotIn("Attached is a report", body)
        self.assertNotIn("Appendix C: Attachments", body)
        self.assertNotIn("review and revise your allowlist", body)

    def test_fceb_action_email_uses_retention_section(self) -> None:
        """Follow the flowchart by omitting the removal section for FCEB."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                template="FCEB Action Required",
                recent_nws="https://example.gov<br>",
                nws_summary="2, 1, 0",
            )

        body = message.get_body(preferencelist=("plain",)).get_content()
        self.assertNotIn("removed only at the customer's request", body)
        self.assertNotIn("two consecutive scans", body)
        self.assertNotIn("3 consecutive scans", body)

    def test_customer_signature_uses_assignee_and_team_identity(self) -> None:
        """Include one assignee plus the complete customer-facing team identity."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
            report_path.write_bytes(b"%PDF")

            message = build_report_email(
                source_email="sender@example.gov",
                recipients=["recipient@example.gov"],
                stakeholder_tag="TAG1",
                report_path=report_path,
                assignee_name="Individual Analyst",
            )

        plain_body = message.get_body(preferencelist=("plain",)).get_content()
        html_body = message.get_body(preferencelist=("html",)).get_content()
        self.assertEqual(plain_body.count("Individual Analyst"), 1)
        self.assertIn("Web Application Scanning (WAS)", plain_body)
        self.assertIn(
            "Cybersecurity and Infrastructure Security Agency (CISA)",
            plain_body,
        )
        self.assertIn("Email: reports@cyber.dhs.gov", plain_body)
        self.assertIn(
            "<strong>Individual Analyst</strong>",
            html_body,
        )

    def test_build_report_email_requires_recipient(self) -> None:
        """Reject messages without recipients."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
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
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
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
    @patch("was_mailer.email_reports.mark_report_run_email_failed_by_id")
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_send_report_run_email_downloads_s3_report_temporarily(
        self,
        mock_claim_report_run_email,
        mock_mark_failed,
        mock_mark_emailed,
    ) -> None:
        """Download an S3 report for SES and remove the temporary file."""
        mock_claim_report_run_email.return_value = ReportRunEmail(
            id=1,
            stakeholder_tag="TAG1",
            output_path="s3://reports/was_reports/2026-08-28/TAG1/1/TAG1_report_2026-08-28.pdf",
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
        mock_mark_failed.assert_not_called()
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
            output_path="s3://reports/was_reports/2026-08-28/TAG1/1/TAG1_report_2026-08-28.pdf",
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
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
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
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
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
            report_path = Path(directory) / "TAG1_report_2026-08-26.pdf"
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
            days_back=30,
        )

        self.assertEqual(sent_count, 2)
        self.assertEqual(mock_send_email.call_count, 2)
        mock_list_ready.assert_called_once_with(
            limit=2,
            include_previous_failures=False,
            stakeholder_tag=None,
            days_back=30,
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
                "--days-back",
                "30",
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
            days_back=30,
        )

    @patch("was_mailer.email_reports.recover_stale_report_operations_in_db")
    @patch("was_mailer.email_reports.send_ready_report_emails")
    def test_main_all_ready_accepts_unlimited_lookback(
        self,
        mock_send_ready,
        mock_recover_stale,
    ) -> None:
        """Translate an explicit all value into an unlimited delivery window."""
        exit_code = email_reports.main(
            [
                "--all-ready",
                "--source-email",
                "sender@example.gov",
                "--days-back",
                "all",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_recover_stale.assert_called_once_with()
        self.assertIsNone(mock_send_ready.call_args.kwargs["days_back"])

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
                "--batch-id",
                "batch-test",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_recover_stale.assert_called_once_with()
        mock_send_digests.assert_called_once_with(
            source_email="sender@example.gov",
            override_recipients="test@example.gov",
            dry_run=True,
            data_pull_date=None,
            limit=None,
            include_previous_failures=False,
            days_back=None,
            batch_id="batch-test",
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

    @patch("was_mailer.message.list_functional_test_recipient_emails_from_db")
    def test_analyst_policy_rejects_missing_and_unapproved_recipients(self, approved):
        """Never fall back to customer contacts for an analyst report."""
        approved.return_value = ["analyst@example.gov"]
        report = SimpleNamespace(delivery_purpose="analyst")
        for recipients in (None, "", "customer@example.gov", "not-an-email"):
            with self.subTest(recipients=recipients), self.assertRaises(ValueError):
                recipient_addresses(report, recipients)
        self.assertEqual(
            approved_analyst_recipients("ANALYST@example.gov;analyst@example.gov"),
            ["ANALYST@example.gov"],
        )

        with self.assertRaisesRegex(
            AnalystRecipientError,
            "not configured as an email-enabled WAS functional-test recipient",
        ):
            approved_analyst_recipients("inactive@example.gov")

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
        self.assertIn(b"could not be generated", message_bytes)
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

    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_template_replay_rejects_customer_purpose_before_claim(self, claim):
        """A template replay must never use the customer delivery policy."""
        with self.assertRaises(ValueError):
            email_reports.send_report_run_email(
                1, "sender@example.gov", preserve_customer_template=True
            )
        claim.assert_not_called()

    @patch("was_mailer.message.list_functional_test_recipient_emails_from_db",
           return_value=["analyst@example.gov"])
    @patch("was_mailer.email_reports.approved_analyst_recipients",
           return_value=["analyst@example.gov"])
    @patch("was_mailer.email_reports.mark_report_run_emailed_by_id")
    @patch("was_mailer.email_reports.touch_report_email_claim_by_id", return_value=True)
    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    def test_replay_preserves_template_without_customer_delivery(
        self, claim, touch, finish, validate, configured
    ):
        """Use the customer body but only approved analyst recipients."""
        claim.return_value = ReportRunEmail(
            id=2, stakeholder_tag="TAG1", output_path=None,
            report_password=None, distro_email="customer@example.gov",
            tech_poc_email=None, was_report_poc="Customer",
            template="All NWS", delivery_purpose="analyst", email_claim_token="token",
        )
        client = Mock()
        client.send_raw_email.return_value = {"MessageId": "message"}
        email_reports.send_report_run_email(
            2, "sender@example.gov", override_recipients="analyst@example.gov",
            delivery_purpose="analyst", preserve_customer_template=True,
            ses_client=client,
        )
        message_bytes = client.send_raw_email.call_args.kwargs["RawMessage"]["Data"]
        self.assertIn(b"To: analyst@example.gov", message_bytes)
        self.assertNotIn(b"To: customer@example.gov", message_bytes)
        self.assertIn(b"could not be generated", message_bytes)
        self.assertNotIn(b"Analyst Copy", message_bytes)
        finish.assert_called_once_with(2, "message", email_claim_token="token")

    @patch("was_mailer.email_reports.claim_report_run_email_by_id")
    @patch("was_mailer.email_reports.approved_analyst_recipients",
           side_effect=AnalystRecipientError("Recipient not enabled"))
    def test_replay_rejects_disabled_recipient_before_claim(self, validate, claim):
        """An unapproved recipient cannot cause a replay claim or send."""
        with self.assertRaises(AnalystRecipientError):
            email_reports.send_report_run_email(
                2, "sender@example.gov", override_recipients="disabled@example.gov",
                delivery_purpose="analyst", preserve_customer_template=True,
            )
        claim.assert_not_called()

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

    @patch("was_reports.reporting.analyst_summaries.send_batch_summary")
    @patch("was_mailer.email_reports.send_assignee_digest_email")
    def test_digest_batch_sends_one_shared_message(self, send, summary):
        """The compatibility entrypoint never fans out individual emails."""
        summary.return_value = "message"
        self.assertEqual(
            email_reports.send_ready_assignee_digests(
                "sender@example.gov", batch_id="batch-test"
            ),
            1,
        )
        summary.assert_called_once_with(
            "batch-test", "sender@example.gov", override_recipients=None, dry_run=False
        )
        send.assert_not_called()

    @patch.dict(os.environ, {"WAS_ANALYST_BATCH_ID": "batch-test"})
    @patch("was_reports.reporting.analyst_summaries.record_report_attempt")
    @patch("was_mailer.email_reports.list_report_runs_ready_for_email_from_db")
    @patch("was_mailer.email_reports.send_report_run_email")
    def test_delivery_retry_is_included_in_shared_batch(self, send, listing, record):
        """Include successful and failed delivery-only work without generation time."""
        listing.return_value = [
            SimpleNamespace(id=1, source_tracker_id=11),
            SimpleNamespace(id=2, source_tracker_id=12),
        ]
        send.side_effect = [RuntimeError("private message"), "message"]
        self.assertEqual(email_reports.send_ready_report_emails("sender@example.gov"), 1)
        self.assertEqual(record.call_count, 2)
        self.assertEqual(record.call_args_list[0].kwargs["error"], "RuntimeError")
        self.assertFalse(record.call_args_list[0].kwargs["sent"])
        self.assertTrue(record.call_args_list[1].kwargs["sent"])
        self.assertEqual(record.call_args_list[1].kwargs["duration_seconds"], 0.0)

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
