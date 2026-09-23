"""Check approved customer-visible PDF names without changing stored artifacts."""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from was_mailer.message import build_report_email, customer_report_attachment_filename


class CustomerAttachmentFilenameTests(unittest.TestCase):
    """Validate date preservation, safe tags, and MIME-only renaming."""

    def test_dated_legacy_and_unique_names_preserve_generation_date(self) -> None:
        """Strip unique run suffixes but retain the filename's generation date."""
        for name in (
            "CHILD_TAG_report_2026-09-23.pdf",
            "CHILD_TAG_report_2026-09-23-a1234567-abcd-1234-abcd-123456789abc.pdf",
            "CHILD_TAG_WAS_report_2026-09-23.pdf",
        ):
            self.assertEqual(customer_report_attachment_filename("CHILD_TAG", Path(name)),
                             "CHILD_TAG_WAS_report_2026-09-23.pdf")

    def test_invalid_dates_and_unsafe_tags_are_rejected(self) -> None:
        """Never invent dates or place path/control characters in attachment names."""
        for name in ("report.pdf", "TAG_report_2026-02-30.pdf",
                     "TAG_report_20260923.pdf", "TAG_report_2026-09-23junk.pdf"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                customer_report_attachment_filename("TAG", Path(name))
        for tag in ("../TAG", "TAG\\child", "TAG\r\nheader", ""):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                customer_report_attachment_filename(tag, Path("TAG_report_2026-09-23.pdf"))

    def test_explicit_generation_date_handles_arbitrary_fixture_names(self) -> None:
        """Allow a known supplied date for a PDF whose basename has no date."""
        self.assertEqual(
            customer_report_attachment_filename("TAG", Path("fixture.pdf"), date(2026, 9, 23)),
            "TAG_WAS_report_2026-09-23.pdf",
        )

    def test_customer_attachment_rename_preserves_file_and_payload(self) -> None:
        """Changing MIME metadata must not rename/delete/overwrite the PDF."""
        with TemporaryDirectory() as directory:
            report = Path(directory) / "TAG_report_2026-09-23-private-uuid.pdf"
            report.write_bytes(b"%PDF retained content")
            message = build_report_email("reports@example.gov", ["poc@example.gov"],
                                         "TAG", report)
            attachment = next(message.iter_attachments())
            self.assertEqual(attachment.get_filename(), "TAG_WAS_report_2026-09-23.pdf")
            self.assertEqual(attachment.get_payload(decode=True), report.read_bytes())
            self.assertEqual(list(Path(directory).iterdir()), [report])
            self.assertNotIn("private-uuid", message.as_string())

    def test_analyst_attachment_keeps_internal_name(self) -> None:
        """The customer naming request does not alter analyst-only delivery."""
        with TemporaryDirectory() as directory:
            report = Path(directory) / "internal-report.pdf"
            report.write_bytes(b"%PDF analyst artifact")
            message = build_report_email("reports@example.gov", ["analyst@example.gov"],
                                         "TAG", report, analyst_delivery=True)
            self.assertEqual(next(message.iter_attachments()).get_filename(), report.name)
