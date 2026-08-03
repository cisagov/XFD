"""Shared PDF password-encryption used by the report-encryption helpers.

Identical across all three original scripts (download_encrypt_reports.py,
encrypt_accessor.py, download_encrypt_excel.py); factored out here so a
future fix to the encryption method only needs to happen in one place.
"""

# Third-Party Libraries
import fitz

_PERMISSIONS = int(
    fitz.PDF_PERM_ACCESSIBILITY
    | fitz.PDF_PERM_PRINT  # permit printing
    | fitz.PDF_PERM_COPY  # permit copying
    | fitz.PDF_PERM_ANNOTATE  # permit annotations
)


def encrypt(file_path, password, encrypted_file_path):
    """AES-256 password-protect file_path, writing the result to encrypted_file_path."""
    doc = fitz.open(file_path)
    doc.save(
        encrypted_file_path,
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw=password,
        permissions=_PERMISSIONS,
        garbage=4,
        deflate=True,
    )
