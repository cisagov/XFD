"""Verify archived WAS attachments before a delivery retry."""

# Standard Python Libraries
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

# Third-Party Libraries
from pikepdf import Encryption, Pdf

# First-Party Libraries
from was_reports.storage.s3_reports import validate_archived_pdf
from was_reports.utils.passwords import generate_report_password


class ArchivedPdfValidationTests(TestCase):
    """Reject missing, corrupt, unencrypted, or inaccessible reports."""

    def test_encrypted_report_with_a_page_is_accepted(self) -> None:
        """Accept the PDF format and encryption produced by WAS reporting."""
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_password = generate_report_password()
            with Pdf.new() as report_document:
                report_document.add_blank_page(page_size=(612, 792))
                report_document.save(
                    report_path,
                    encryption=Encryption(
                        owner=report_password,
                        user=report_password,
                        R=4,
                    ),
                )

            original_digest = validate_archived_pdf(
                report_path, report_password, require_password_match=True
            )
            self.assertEqual(len(original_digest), 64)
            self.assertEqual(
                validate_archived_pdf(
                    report_path,
                    generate_report_password(),
                    expected_sha256=original_digest,
                ),
                original_digest,
            )
            with self.assertRaises(ValueError):
                validate_archived_pdf(
                    report_path,
                    generate_report_password(),
                    require_password_match=True,
                )
            with self.assertRaises(ValueError):
                validate_archived_pdf(
                    report_path, None, expected_sha256="0" * 64
                )

    def test_invalid_or_unencrypted_report_is_rejected(self) -> None:
        """Reject arbitrary bytes and an unprotected PDF before SES is called."""
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_password = generate_report_password()
            report_path.write_bytes(b"not a PDF")
            with self.assertRaises(ValueError) as invalid_document:
                validate_archived_pdf(report_path, report_password)
            self.assertIn("invalid or inaccessible", str(invalid_document.exception))

            with Pdf.new() as report_document:
                report_document.add_blank_page(page_size=(612, 792))
                report_document.save(report_path)
            with self.assertRaises(ValueError) as unencrypted_document:
                validate_archived_pdf(report_path, report_password)
            self.assertIn("invalid", str(unencrypted_document.exception))

    def test_valid_aes256_archive_does_not_require_optional_pypdf_crypto(self) -> None:
        """Recognize an archived encrypted PDF with the existing pikepdf dependency."""
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_password = generate_report_password()
            with Pdf.new() as report_document:
                report_document.add_blank_page(page_size=(612, 792))
                report_document.save(
                    report_path,
                    encryption=Encryption(
                        owner=report_password,
                        user=report_password,
                        R=6,
                    ),
                )

            original_digest = validate_archived_pdf(
                report_path, report_password, require_password_match=True
            )
            validate_archived_pdf(
                report_path, None, expected_sha256=original_digest
            )

    def test_zero_page_encrypted_report_is_rejected_before_initial_send(self) -> None:
        """Require a readable page before recording an initial archive digest."""
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_password = generate_report_password()
            with Pdf.new() as report_document:
                report_document.save(
                    report_path,
                    encryption=Encryption(
                        owner=report_password,
                        user=report_password,
                        R=4,
                    ),
                )
            with self.assertRaises(ValueError):
                validate_archived_pdf(
                    report_path, report_password, require_password_match=True
                )

    def test_missing_or_empty_report_is_rejected(self) -> None:
        """Fail without preparing an incomplete email attachment."""
        with TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            report_password = generate_report_password()
            with self.assertRaises(ValueError) as missing_document:
                validate_archived_pdf(report_path, report_password)
            self.assertIn("missing or empty", str(missing_document.exception))
            report_path.touch()
            with self.assertRaises(ValueError) as empty_document:
                validate_archived_pdf(report_path, report_password)
            self.assertIn("missing or empty", str(empty_document.exception))
