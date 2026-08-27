"""PDF helper functions for WAS report artifacts."""

# Standard Python Libraries
import subprocess
from pathlib import Path

# Third-Party Libraries
from PyPDF4 import PdfFileReader, PdfFileWriter
from pdfrw import PageMerge, PdfReader, PdfWriter


def redact_qualys_pdf(
    input_path: Path,
    output_path: Path,
    redactor_path: Path,
    python_executable: str,
) -> None:
    """Redact a Qualys PDF using the legacy redaction script."""
    with input_path.open("rb") as input_file:
        with output_path.open("wb") as output_file:
            subprocess.run(
                [python_executable, str(redactor_path)],
                stdin=input_file,
                stdout=output_file,
                check=True,
            )


def apply_watermark(input_path: Path, watermark_path: Path) -> None:
    """Apply a PDF watermark to every page in a file."""
    input_reader = PdfReader(str(input_path))
    output_writer = PdfWriter()
    watermark_reader = PdfReader(str(watermark_path))
    watermark = watermark_reader.pages[0]

    for current_page in range(len(input_reader.pages)):
        merger = PageMerge(input_reader.pages[current_page])
        merger.add(watermark).render()

    output_writer.write(str(input_path), input_reader)


def remove_first_page(input_path: Path, output_path: Path) -> None:
    """Write a copy of a PDF without the first page."""
    pdf_file = PdfFileReader(str(input_path))
    output_writer = PdfFileWriter()

    for page_index in range(1, pdf_file.getNumPages()):
        page = pdf_file.getPage(page_index)
        output_writer.addPage(page)

    with output_path.open("wb") as output_file:
        output_writer.write(output_file)


def post_process_detail_pdf(
    detail_path: Path,
    redacted_path: Path,
    watermark_path: Path,
    redactor_path: Path,
    python_executable: str,
) -> None:
    """Redact, watermark, and remove the first page from a detail PDF."""
    try:
        redact_qualys_pdf(
            input_path=detail_path,
            output_path=redacted_path,
            redactor_path=redactor_path,
            python_executable=python_executable,
        )
        apply_watermark(input_path=redacted_path, watermark_path=watermark_path)
        remove_first_page(input_path=redacted_path, output_path=detail_path)
    finally:
        if redacted_path.exists():
            redacted_path.unlink()
