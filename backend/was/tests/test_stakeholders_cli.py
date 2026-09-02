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


if __name__ == "__main__":
    unittest.main()
