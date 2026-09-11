"""Tests for the WAS stakeholder administration CLI."""

# Standard Python Libraries
import csv
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.commands import stakeholders_cli


class StakeholdersCliTests(unittest.TestCase):
    """Validate stakeholder command safety and output behavior."""

    @patch(
        "was_reports.commands.stakeholders_cli."
        "update_stakeholder_contacts_for_tag"
    )
    def test_update_contacts_requires_confirmation(self, mock_update) -> None:
        """Reject stakeholder mutations without explicit confirmation."""
        exit_code = stakeholders_cli.main(
            [
                "update-contacts",
                "--tag",
                "TAG1",
                "--was-report-poc",
                "Analyst Name",
            ]
        )

        self.assertEqual(exit_code, 1)
        mock_update.assert_not_called()

    @patch(
        "was_reports.commands.stakeholders_cli."
        "update_stakeholder_contacts_for_tag"
    )
    def test_update_contacts_passes_only_supplied_fields(self, mock_update) -> None:
        """Pass validated updates to the stakeholder data service."""
        exit_code = stakeholders_cli.main(
            [
                "update-contacts",
                "--tag",
                "TAG1",
                "--tech-poc-email",
                "tech@example.gov; backup@example.gov",
                "--clear-distro-email",
                "--confirm",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_update.assert_called_once_with(
            tag="TAG1",
            updates={
                "tech_poc_email": "tech@example.gov; backup@example.gov",
                "distro_email": None,
            },
        )

    @patch("was_reports.commands.stakeholders_cli.display_stakeholder_record")
    @patch("was_reports.commands.stakeholders_cli.get_stakeholder_record_by_tag")
    def test_show_displays_exact_stakeholder_tag(
        self,
        mock_get_record,
        mock_display_record,
    ) -> None:
        """Retrieve and display the stakeholder matching the supplied tag."""
        mock_get_record.return_value = {"tag": "TAG1"}

        exit_code = stakeholders_cli.main(["show", "--tag", "TAG1"])

        self.assertEqual(exit_code, 0)
        mock_get_record.assert_called_once_with("TAG1")
        mock_display_record.assert_called_once_with({"tag": "TAG1"})

    @patch("was_reports.commands.stakeholders_cli.display_stakeholder_record")
    @patch("was_reports.commands.stakeholders_cli.get_stakeholder_record_by_tag")
    @patch(
        "was_reports.commands.stakeholders_cli.update_stakeholder_fields_for_tag"
    )
    def test_general_update_validates_and_updates_selected_fields(
        self,
        mock_update,
        mock_get_record,
        mock_display_record,
    ) -> None:
        """Update typed values and SQL NULL without touching other columns."""
        mock_get_record.return_value = {"tag": "TAG1", "retired": True}

        exit_code = stakeholders_cli.main(
            [
                "update",
                "--tag",
                "TAG1",
                "--set",
                "retired=true",
                "--set",
                "num_web_apps=3",
                "--clear",
                "comments",
                "--confirm",
            ]
        )

        self.assertEqual(exit_code, 0)
        mock_update.assert_called_once_with(
            tag="TAG1",
            updates={"retired": True, "num_web_apps": 3, "comments": None},
        )
        mock_display_record.assert_called_once_with(
            {"tag": "TAG1", "retired": True}
        )

    def test_sensitive_export_requires_separate_confirmation(self) -> None:
        """Reject password export without its explicit confirmation flag."""
        exit_code = stakeholders_cli.main(
            [
                "export-csv",
                "--output",
                "/tmp/stakeholders.csv",
                "--include-report-passwords",
            ]
        )

        self.assertEqual(exit_code, 1)

    @patch("was_reports.commands.stakeholders_cli.upload_stakeholder_export")
    @patch(
        "was_reports.commands.stakeholders_cli."
        "list_stakeholders_for_export_from_db"
    )
    def test_export_can_upload_directly_to_s3(
        self,
        mock_list_stakeholders,
        mock_upload,
    ) -> None:
        """Generate one temporary CSV and upload it to configured S3."""
        mock_list_stakeholders.return_value = (["tag"], [("TAG1",)])
        mock_upload.return_value = "s3://reports/was_reports/export.csv"

        exit_code = stakeholders_cli.main(["export-csv", "--s3"])

        self.assertEqual(exit_code, 0)
        uploaded_path = mock_upload.call_args.args[0]
        self.assertEqual(uploaded_path.name, "was-stakeholders.csv")

    @patch("was_reports.commands.stakeholders_cli.send_message")
    @patch("was_reports.commands.stakeholders_cli.create_ses_client")
    @patch("was_reports.commands.stakeholders_cli.build_stakeholder_export_email")
    @patch("was_reports.commands.stakeholders_cli.approved_analyst_recipients")
    @patch(
        "was_reports.commands.stakeholders_cli."
        "list_stakeholders_for_export_from_db"
    )
    def test_export_can_email_active_assignee(
        self,
        mock_list_stakeholders,
        mock_recipients,
        mock_build_message,
        mock_create_ses_client,
        mock_send_message,
    ) -> None:
        """Email the temporary export only after assignee validation."""
        mock_list_stakeholders.return_value = (["tag"], [("TAG1",)])
        mock_recipients.return_value = ["analyst@example.gov"]
        mock_send_message.return_value = "message-id"

        with patch.dict(
            "os.environ",
            {"WAS_EMAIL_SOURCE": "reports@example.gov"},
            clear=False,
        ):
            exit_code = stakeholders_cli.main(
                [
                    "export-csv",
                    "--email-assignee",
                    "analyst@example.gov",
                ]
            )

        self.assertEqual(exit_code, 0)
        mock_recipients.assert_called_once_with("analyst@example.gov")
        mock_build_message.assert_called_once()
        mock_send_message.assert_called_once_with(
            mock_create_ses_client.return_value,
            mock_build_message.return_value,
        )

    @patch(
        "was_reports.commands.stakeholders_cli."
        "list_stakeholders_for_export_from_db"
    )
    def test_password_export_cannot_be_emailed(
        self,
        mock_list_stakeholders,
    ) -> None:
        """Keep stakeholder report passwords out of email attachments."""
        exit_code = stakeholders_cli.main(
            [
                "export-csv",
                "--email-assignee",
                "analyst@example.gov",
                "--include-report-passwords",
                "--confirm-sensitive-export",
            ]
        )

        self.assertEqual(exit_code, 1)
        mock_list_stakeholders.assert_not_called()

    def test_write_stakeholder_csv_is_private_and_spreadsheet_safe(self) -> None:
        """Write owner-only CSV output and neutralize formula text."""
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "stakeholders.csv"
            stakeholders_cli.write_stakeholder_csv(
                columns=["tag", "comments", "report_password"],
                rows=[("TAG1", "=DANGEROUS()", "+ExactPassword")],
                output_path=output_path,
            )
            with output_path.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.reader(csv_file))
            permissions = os.stat(output_path).st_mode & 0o777

        self.assertEqual(rows[1][1], "'=DANGEROUS()")
        self.assertEqual(rows[1][2], "+ExactPassword")
        self.assertEqual(permissions, 0o600)

    def test_write_stakeholder_csv_formats_epoch_dates_as_utc(self) -> None:
        """Convert stakeholder epoch columns into readable UTC timestamps."""
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "stakeholders.csv"
            stakeholders_cli.write_stakeholder_csv(
                columns=[
                    "tag",
                    "last_scanned",
                    "next_scheduled",
                    "onboarding_date",
                    "web_apps_last_updated",
                ],
                rows=[
                    (
                        "TAG1",
                        0,
                        1789257600,
                        None,
                        1786620284,
                    )
                ],
                output_path=output_path,
            )
            with output_path.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(rows[1][1], "1970-01-01 00:00:00 UTC")
        self.assertEqual(rows[1][2], "2026-09-13 00:00:00 UTC")
        self.assertEqual(rows[1][3], "")
        self.assertEqual(rows[1][4], "2026-08-13 11:24:44 UTC")

    def test_stakeholder_export_rejects_invalid_epoch_dates(self) -> None:
        """Reject invalid stored epoch values instead of misreporting dates."""
        with self.assertRaisesRegex(ValueError, "invalid epoch"):
            stakeholders_cli.stakeholder_export_value(
                "last_scanned",
                "not-an-epoch",
            )


if __name__ == "__main__":
    unittest.main()
