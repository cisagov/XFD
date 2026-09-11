"""Tests for stakeholder export storage in Amazon S3."""

# Standard Python Libraries
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

# First-Party Libraries
from was_reports.storage import stakeholder_exports


class StakeholderExportStorageTests(unittest.TestCase):
    """Validate stakeholder export S3 paths and upload security."""

    @patch("was_reports.storage.stakeholder_exports.uuid4", return_value="export-id")
    def test_stakeholder_export_object_key_is_unique(self, mock_uuid) -> None:
        """Place stakeholder exports below a dated dedicated prefix."""
        key = stakeholder_exports.stakeholder_export_object_key(
            filename="was-stakeholders.csv",
            exported_at=datetime(2026, 9, 11, tzinfo=timezone.utc),
            prefix="was_reports",
        )

        self.assertEqual(
            key,
            "was_reports/stakeholder_exports/2026-09-11/"
            "was-stakeholders-export-id.csv",
        )
        mock_uuid.assert_called_once_with()

    def test_upload_stakeholder_export_encrypts_csv(self) -> None:
        """Upload CSV exports with content metadata and encryption."""
        client = Mock()
        with tempfile.TemporaryDirectory() as directory:
            export_path = Path(directory) / "was-stakeholders.csv"
            export_path.write_text("tag\nTAG1\n", encoding="utf-8")
            with patch(
                "was_reports.storage.stakeholder_exports."
                "stakeholder_export_object_key",
                return_value="was_reports/stakeholder_exports/file.csv",
            ):
                export_uri = stakeholder_exports.upload_stakeholder_export(
                    export_path=export_path,
                    s3_client=client,
                    bucket="reports",
                )

        self.assertEqual(
            export_uri,
            "s3://reports/was_reports/stakeholder_exports/file.csv",
        )
        client.upload_file.assert_called_once_with(
            str(export_path),
            "reports",
            "was_reports/stakeholder_exports/file.csv",
            ExtraArgs={
                "ContentType": "text/csv",
                "ServerSideEncryption": "AES256",
            },
        )
