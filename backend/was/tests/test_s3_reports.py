"""Tests for WAS report storage in Amazon S3."""

# Standard Python Libraries
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

# Third-Party Libraries
# First-Party Libraries
from was_reports.storage import s3_reports


class S3ReportStorageTests(unittest.TestCase):
    """Validate WAS report S3 keys, uploads, and temporary downloads."""

    def test_report_object_key_is_run_specific(self) -> None:
        """Separate repeated stakeholder reports by immutable report run id."""
        key = s3_reports.report_object_key(
            stakeholder_tag="TAG1",
            report_date=date(2026, 8, 28),
            report_run_id=42,
            filename="TAG1_report_2026-08-28.pdf",
            prefix="was_reports",
        )

        self.assertEqual(
            key,
            "was_reports/2026-08-28/TAG1/42/TAG1_report_2026-08-28.pdf",
        )

    def test_report_object_key_rejects_unsafe_tag(self) -> None:
        """Prevent stakeholder tags from changing the S3 key hierarchy."""
        with self.assertRaises(ValueError):
            s3_reports.report_object_key(
                stakeholder_tag="../TAG1",
                report_date=date(2026, 8, 28),
                report_run_id=42,
                filename="report.pdf",
                prefix="was_reports",
            )

    def test_upload_report_uses_server_side_encryption(self) -> None:
        """Upload PDFs with content metadata and S3-managed encryption."""
        client = Mock()
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "TAG1_report_2026-08-28.pdf"
            report_path.write_bytes(b"%PDF")

            report_uri = s3_reports.upload_report(
                report_path=report_path,
                stakeholder_tag="TAG1",
                report_date=date(2026, 8, 28),
                report_run_id=42,
                s3_client=client,
                bucket="reports-bucket",
                prefix="was_reports",
            )

        self.assertEqual(
            report_uri,
            "s3://reports-bucket/was_reports/2026-08-28/"
            "TAG1/42/TAG1_report_2026-08-28.pdf",
        )
        client.upload_file.assert_called_once_with(
            str(report_path),
            "reports-bucket",
            "was_reports/2026-08-28/TAG1/42/TAG1_report_2026-08-28.pdf",
            ExtraArgs={
                "ContentType": "application/pdf",
                "ServerSideEncryption": "AES256",
            },
        )

    def test_materialize_report_downloads_and_removes_temporary_file(self) -> None:
        """Download an S3 report privately and remove it after use."""
        client = Mock()
        downloaded_paths = []

        def download_file(bucket, key, destination):
            self.assertEqual(bucket, "reports-bucket")
            self.assertEqual(key, "was_reports/2026-08-28/TAG1/42/report.pdf")
            downloaded_path = Path(destination)
            downloaded_path.write_bytes(b"%PDF")
            downloaded_paths.append(downloaded_path)

        client.download_file.side_effect = download_file
        with s3_reports.materialize_report(
            "s3://reports-bucket/was_reports/2026-08-28/TAG1/42/report.pdf",
            s3_client=client,
            expected_bucket="reports-bucket",
            expected_prefix="was_reports",
        ) as report_path:
            self.assertTrue(report_path.is_file())
            self.assertEqual(report_path.stat().st_mode & 0o777, 0o600)

        self.assertFalse(downloaded_paths[0].exists())

    def test_materialize_report_rejects_unexpected_bucket(self) -> None:
        """Prevent database values from selecting another accessible bucket."""
        with self.assertRaises(ValueError):
            with s3_reports.materialize_report(
                "s3://other-bucket/was_reports/2026-08-28/TAG1/42/report.pdf",
                s3_client=Mock(),
                expected_bucket="reports-bucket",
                expected_prefix="was_reports",
            ):
                pass

    def test_materialize_report_rejects_non_pdf_object(self) -> None:
        """Do not attach an unexpected object type from a database reference."""
        with self.assertRaises(ValueError):
            with s3_reports.materialize_report(
                "s3://reports-bucket/was_reports/2026-08-28/TAG1/42/report.txt",
                s3_client=Mock(),
                expected_bucket="reports-bucket",
                expected_prefix="was_reports",
            ):
                pass

    def test_delete_report_uses_validated_s3_location(self) -> None:
        """Logically delete an orphan only from the configured storage prefix."""
        client = Mock()

        s3_reports.delete_report(
            "s3://reports-bucket/was_reports/2026-08-28/TAG1/42/report.pdf",
            s3_client=client,
            expected_bucket="reports-bucket",
            expected_prefix="was_reports",
        )

        client.delete_object.assert_called_once_with(
            Bucket="reports-bucket",
            Key="was_reports/2026-08-28/TAG1/42/report.pdf",
        )

    def test_materialize_report_preserves_local_compatibility(self) -> None:
        """Yield existing local reports without invoking S3."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")

            with s3_reports.materialize_report(
                str(report_path),
                storage_mode="local",
                expected_local_root=Path(directory),
            ) as materialized:
                self.assertEqual(materialized, report_path.resolve())

    def test_materialize_report_rejects_local_path_in_s3_mode(self) -> None:
        """Prevent database local paths from bypassing production S3 storage."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_path.write_bytes(b"%PDF")

            with self.assertRaises(ValueError):
                with s3_reports.materialize_report(
                    str(report_path),
                    storage_mode="s3",
                ):
                    pass

    def test_materialize_report_rejects_path_outside_local_root(self) -> None:
        """Prevent a database path from attaching another readable file."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_directory = root / "reports"
            output_directory.mkdir()
            outside_report = root / "outside.pdf"
            outside_report.write_bytes(b"%PDF")

            with self.assertRaises(ValueError):
                with s3_reports.materialize_report(
                    str(outside_report),
                    storage_mode="local",
                    expected_local_root=output_directory,
                ):
                    pass


if __name__ == "__main__":
    unittest.main()
