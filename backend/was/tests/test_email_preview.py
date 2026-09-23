"""Check offline preview MIME attachments and delivery isolation."""

from email import policy
from datetime import date
from email.parser import BytesParser
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from was_reports.commands.email_preview import create_preview


class EmailPreviewTests(unittest.TestCase):
    """Validate the same MIME message used for customer delivery."""

    def test_pdf_is_attached_unchanged_and_html_logo_is_viewable(self) -> None:
        """Keep the supplied attachment intact and make the HTML self-contained."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            attachment = root / "OFFLINE_report_2026-09-23-unique-token.pdf"
            attachment.write_bytes(b"test attachment bytes")
            mime_path, html_path, text_path = create_preview(root, "Results", attachment)
            message = BytesParser(policy=policy.default).parsebytes(mime_path.read_bytes())
            self.assertEqual(message["To"], "preview@example.invalid")
            self.assertEqual(next(message.iter_attachments()).get_filename(),
                             "OFFLINE_WAS_report_2026-09-23.pdf")
            self.assertEqual(message["Subject"], "OFFLINE - WAS Results")
            self.assertEqual(
                list(message.iter_attachments())[0].get_payload(decode=True),
                attachment.read_bytes(),
            )
            self.assertIn("data:image/png;base64,", html_path.read_text())
            self.assertNotIn("cid:cisa-logo", html_path.read_text())
            self.assertIn("Sample POC,", text_path.read_text())

    def test_undated_preview_attachment_requires_explicit_date(self) -> None:
        """Use an explicit fixture date instead of silently guessing today's date."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            attachment = root / "fixture.pdf"
            attachment.write_bytes(b"test attachment bytes")
            with self.assertRaises(ValueError):
                create_preview(root, "Results", attachment)
            mime_path, _, _ = create_preview(
                root, "Results", attachment, report_date=date(2026, 9, 23)
            )
            message = BytesParser(policy=policy.default).parsebytes(mime_path.read_bytes())
            self.assertEqual(next(message.iter_attachments()).get_filename(),
                             "OFFLINE_WAS_report_2026-09-23.pdf")

    def test_all_nws_has_no_pdf_and_uses_no_report_subject(self) -> None:
        """Notification previews must never invent a report attachment."""
        with TemporaryDirectory() as directory:
            mime_path, _, _ = create_preview(Path(directory), "All NWS", None)
            message = BytesParser(policy=policy.default).parsebytes(mime_path.read_bytes())
            self.assertEqual(list(message.iter_attachments()), [])
            self.assertIn("Report Not Generated", message["Subject"])

    def test_report_preview_requires_existing_attachment(self) -> None:
        """Do not pretend a PDF-backed report was generated without a PDF."""
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                create_preview(Path(directory), "Results", None)
