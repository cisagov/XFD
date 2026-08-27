"""Tests for legacy and extracted WAS PDF comparison."""

# Standard Python Libraries
import tempfile
import unittest
from pathlib import Path

# Third-Party Libraries
from pikepdf import Array, Dictionary, Encryption, Name, Pdf, String

# First-Party Libraries
from was_reports.reporting import report_comparison

PASSWORD = "ComparisonPassword123!"


class ReportComparisonTests(unittest.TestCase):
    """Validate deterministic encrypted report comparison behavior."""

    def create_report(self, path: Path, page_width: int = 100) -> None:
        """Create one encrypted fixture PDF with a blank page."""
        with Pdf.new() as pdf:
            pdf.add_blank_page(page_size=(page_width, 100))
            pdf.docinfo["/Title"] = "WAS Report"
            pdf.save(
                path,
                encryption=Encryption(owner=PASSWORD, user=PASSWORD, R=4),
            )

    def create_report_with_annotation_attachment(self, path: Path) -> None:
        """Create an encrypted PDF containing a page-level file attachment."""
        with Pdf.new() as pdf:
            page = pdf.add_blank_page(page_size=(100, 100))
            embedded_file = pdf.make_stream(b"attachment-content")
            file_specification = Dictionary(
                Type=Name.Filespec,
                F=String("assets/report.csv"),
                UF=String("assets/report.csv"),
                EF=Dictionary(F=embedded_file),
            )
            annotation = Dictionary(
                Type=Name.Annot,
                Subtype=Name.FileAttachment,
                Rect=Array([0, 0, 10, 10]),
                FS=file_specification,
            )
            page.obj.Annots = Array([pdf.make_indirect(annotation)])
            pdf.save(
                path,
                encryption=Encryption(owner=PASSWORD, user=PASSWORD, R=4),
            )

    def test_matching_reports_have_no_differences(self) -> None:
        """Treat structurally equivalent encrypted PDFs as matching."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_path = root / "legacy.pdf"
            extracted_path = root / "extracted.pdf"
            self.create_report(legacy_path)
            self.create_report(extracted_path)

            result = report_comparison.compare_reports(
                legacy_path,
                extracted_path,
                PASSWORD,
            )

        self.assertTrue(result.matches)
        self.assertEqual(result.differences, ())
        self.assertTrue(result.legacy.encrypted)

    def test_page_size_difference_is_reported(self) -> None:
        """Identify a structural mismatch without exposing report content."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_path = root / "legacy.pdf"
            extracted_path = root / "extracted.pdf"
            self.create_report(legacy_path, page_width=100)
            self.create_report(extracted_path, page_width=200)

            result = report_comparison.compare_reports(
                legacy_path,
                extracted_path,
                PASSWORD,
            )

        self.assertFalse(result.matches)
        self.assertIn("page_sizes differs", result.differences)

    def test_inspection_finds_page_annotation_attachment(self) -> None:
        """Inventory attachments emitted by XeLaTeX attachfile2 annotations."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.pdf"
            self.create_report_with_annotation_attachment(report_path)

            inspection = report_comparison.inspect_report(
                report_path,
                PASSWORD,
            )

        self.assertEqual(
            set(inspection.attachments),
            {"assets/report.csv"},
        )


if __name__ == "__main__":
    unittest.main()
