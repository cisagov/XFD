"""Tests for atomic WAS PDF password encryption."""

# Standard Python Libraries
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Third-Party Libraries
from pikepdf import PasswordError, Pdf

# First-Party Libraries
from was_reports.reporting import pdf_security


class PdfSecurityTests(unittest.TestCase):
    """Validate password encryption and failure-safe replacement."""

    def create_pdf(self, path: Path) -> None:
        """Create a minimal valid PDF for encryption tests."""
        with Pdf.new() as pdf:
            pdf.add_blank_page(page_size=(100, 100))
            pdf.save(path)

    def test_encrypt_pdf_in_place_requires_password(self) -> None:
        """Encrypt with the stakeholder password and replace the source file."""
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "report.pdf"
            self.create_pdf(pdf_path)

            result = pdf_security.encrypt_pdf_in_place(
                pdf_path,
                "SecurePassword123!",
            )

            self.assertEqual(result, pdf_path)
            with self.assertRaises(PasswordError):
                Pdf.open(pdf_path)
            with Pdf.open(pdf_path, password="SecurePassword123!") as pdf:
                self.assertEqual(len(pdf.pages), 1)

    def test_encryption_failure_preserves_original_pdf(self) -> None:
        """Leave the unencrypted source intact when encrypted save fails."""
        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "report.pdf"
            self.create_pdf(pdf_path)
            original_content = pdf_path.read_bytes()

            with patch("was_reports.reporting.pdf_security.Pdf.open") as mock_open:
                mock_open.side_effect = RuntimeError("encryption failed")
                with self.assertRaises(RuntimeError):
                    pdf_security.encrypt_pdf_in_place(
                        pdf_path,
                        "SecurePassword123!",
                    )

            self.assertEqual(pdf_path.read_bytes(), original_content)
            temporary_files = list(Path(directory).glob(".report-*.pdf"))
            self.assertEqual(temporary_files, [])

    def test_publish_encrypted_pdf_uses_final_filename(self) -> None:
        """Publish encrypted bytes without exposing an intermediate filename."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private_path = root / "private" / "report.pdf"
            private_path.parent.mkdir()
            private_path.write_bytes(b"encrypted-pdf")

            final_path = pdf_security.publish_encrypted_pdf(
                private_path,
                root / "output",
            )

            self.assertEqual(final_path, root / "output" / "report.pdf")
            self.assertEqual(final_path.read_bytes(), b"encrypted-pdf")
            self.assertEqual(
                list((root / "output").glob(".report-*.pdf")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
