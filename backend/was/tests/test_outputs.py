"""Tests for WAS report output helpers."""

# Standard Python Libraries
import tempfile
import unittest
from datetime import date
from pathlib import Path

# First-Party Libraries
from was_reports.utils.outputs import expected_pdf_output_path, require_output_file


class OutputTests(unittest.TestCase):
    """Validate WAS output file helpers."""

    def test_expected_pdf_output_path_matches_legacy_name(self) -> None:
        """Build the expected legacy PDF output path."""
        output_path = expected_pdf_output_path(
            stakeholder_tag="TAG1",
            output_directory="/WAS_REPORT_GENERATION/docs",
            report_date=date(2026, 8, 25),
        )

        self.assertEqual(
            str(output_path),
            "/WAS_REPORT_GENERATION/docs/TAG1_report_2026-08-25.pdf",
        )

    def test_require_output_file_returns_existing_file(self) -> None:
        """Return an existing report output path."""
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.pdf"
            output_path.write_text("pdf", encoding="utf-8")

            self.assertEqual(require_output_file(output_path), output_path)

    def test_require_output_file_rejects_missing_file(self) -> None:
        """Reject a missing report output path."""
        with self.assertRaises(FileNotFoundError):
            require_output_file(Path("/tmp/missing-was-report.pdf"))


if __name__ == "__main__":
    unittest.main()
