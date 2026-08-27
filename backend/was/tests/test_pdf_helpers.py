"""Tests for WAS PDF helper orchestration."""

# Standard Python Libraries
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# First-Party Libraries
from was_reports import pdf_helpers


class PdfHelperTests(unittest.TestCase):
    """Validate PDF helper orchestration behavior."""

    @patch("was_reports.pdf_helpers.remove_first_page")
    @patch("was_reports.pdf_helpers.apply_watermark")
    @patch("was_reports.pdf_helpers.redact_qualys_pdf")
    def test_post_process_detail_pdf_removes_redacted_file(
        self,
        mock_redact,
        mock_watermark,
        mock_remove_first_page,
    ) -> None:
        """Clean up the temporary redacted PDF after post-processing."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            detail_path = root / "detail.pdf"
            redacted_path = root / "detail.pdf_redacted.pdf"
            watermark_path = root / "watermark.pdf"
            redactor_path = root / "redact_qualys.py"
            redacted_path.write_bytes(b"redacted")

            pdf_helpers.post_process_detail_pdf(
                detail_path=detail_path,
                redacted_path=redacted_path,
                watermark_path=watermark_path,
                redactor_path=redactor_path,
                python_executable="python3",
            )

            self.assertFalse(redacted_path.exists())

        mock_redact.assert_called_once()
        mock_watermark.assert_called_once()
        mock_remove_first_page.assert_called_once()


if __name__ == "__main__":
    unittest.main()
