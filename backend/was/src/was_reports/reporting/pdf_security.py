"""Apply password encryption to generated WAS PDF reports."""

# Standard Python Libraries
import os
import shutil
import tempfile
from pathlib import Path

# Third-Party Libraries
from pikepdf import Encryption, Pdf

# First-Party Libraries
from was_reports.utils.passwords import validate_report_password


def encrypt_pdf_in_place(pdf_path: Path, report_password: str) -> Path:
    """Atomically replace a PDF with its password-encrypted equivalent."""
    validate_report_password(report_password)
    if not pdf_path.is_file():
        raise FileNotFoundError(
            "WAS PDF report not found at {}.".format(pdf_path)
        )
    temporary_file = tempfile.NamedTemporaryFile(
        prefix=".{}-".format(pdf_path.stem),
        suffix=".pdf",
        dir=pdf_path.parent,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()
    try:
        with Pdf.open(pdf_path) as source_pdf:
            source_pdf.save(
                temporary_path,
                encryption=Encryption(
                    owner=report_password,
                    user=report_password,
                    R=4,
                ),
            )
        os.replace(temporary_path, pdf_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return pdf_path


def publish_encrypted_pdf(
    encrypted_pdf_path: Path,
    output_directory: Path,
) -> Path:
    """Atomically publish an already encrypted PDF to its final directory."""
    if not encrypted_pdf_path.is_file():
        raise FileNotFoundError(
            "Encrypted WAS PDF not found at {}.".format(encrypted_pdf_path)
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    final_path = output_directory / encrypted_pdf_path.name
    temporary_file = tempfile.NamedTemporaryFile(
        prefix=".{}-".format(encrypted_pdf_path.stem),
        suffix=".pdf",
        dir=output_directory,
        delete=False,
    )
    temporary_path = Path(temporary_file.name)
    temporary_file.close()
    try:
        shutil.copyfile(encrypted_pdf_path, temporary_path)
        os.replace(temporary_path, final_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return final_path
