"""Tests for WAS mailer message and SES delivery helpers."""

# Standard Python Libraries
from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_mailer import email_reports
from was_mailer.message import (
    build_assignee_digest_email,
    build_report_email,
    parse_email_addresses,
    recipient_addresses,
)
from was_reports.data.daily_report_tracker import AssigneeDigest, DailyReportTrackerRow
from was_reports.data.report_runs import ReportRunEmail


class WasMailerTests(unittest.TestCase):
    """Validate WAS mailer behavior."""

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
        self.assertEqual(message["Subject"], "WAS Report for TAG1")
        self.assertNotIn("password123", message.as_string())
        self.assertIn("TAG1_report_2026-08-26.pdf", message.as_string())

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
        mock_mark_emailed.assert_called_once_with(1, "message-id")

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
        mock_mark_emailed.assert_called_once_with(1, "message-id")

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
    @patch("was_mailer.email_reports.LOGGER.exception")
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
            hold_for_manual_retry=False,
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

        mock_mark_failed.assert_not_called()

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

    @patch("was_mailer.email_reports.send_ready_report_emails")
    def test_main_all_ready_uses_batch_mode(self, mock_send_ready) -> None:
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
        mock_send_ready.assert_called_once_with(
            source_email="sender@example.gov",
            override_recipients="test@example.gov",
            dry_run=True,
            limit=1,
            include_previous_failures=False,
        )

    @patch("was_mailer.email_reports.send_ready_assignee_digests")
    def test_main_assignee_digests_routes_to_digest_mode(
        self,
        mock_send_digests,
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
        mock_send_digests.assert_called_once_with(
            source_email="sender@example.gov",
            override_recipients="test@example.gov",
            dry_run=True,
            data_pull_date=date(2026, 8, 26),
            limit=5,
        )

    @patch("was_mailer.email_reports.mark_assignee_digest_success_for_dates")
    def test_send_assignee_digest_email_sends_with_ses(
        self,
        mock_mark_success,
    ) -> None:
        """Send an assignee digest through SES."""
        digest = AssigneeDigest(
            assignee_id=3,
            assignee="Analyst",
            email="analyst@example.gov",
            rows=[DailyReportTrackerRow(data_pull_date=date(2026, 8, 26))],
        )
        ses_client = Mock()
        ses_client.send_raw_email.return_value = {"MessageId": "message-id"}

        message_id = email_reports.send_assignee_digest_email(
            assignee_digest=digest,
            source_email="sender@example.gov",
            ses_client=ses_client,
        )

        self.assertEqual(message_id, "message-id")
        self.assertEqual(ses_client.send_raw_email.call_count, 1)
        mock_mark_success.assert_called_once_with(digest, "message-id")


if __name__ == "__main__":
    unittest.main()
