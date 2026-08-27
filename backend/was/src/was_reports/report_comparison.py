"""Compare legacy and extracted WAS PDF report structure and content."""

# Standard Python Libraries
import argparse
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Third-Party Libraries
from pikepdf import Pdf
from pypdf import PdfReader

# First-Party Libraries
from was_reports.utils.env import getenv

PASSWORD_ENVIRONMENT_NAME = "WAS_REPORT_COMPARISON_PASSWORD"
COMPARABLE_METADATA_KEYS = ("/Title", "/Author", "/Subject", "/Keywords")


@dataclass(frozen=True)
class ReportInspection:
    """Comparable structural values extracted from one PDF report."""

    encrypted: bool
    page_count: int
    page_sizes: Tuple[Tuple[float, float], ...]
    page_text_hashes: Tuple[str, ...]
    attachments: Dict[str, str]
    metadata: Dict[str, str]


@dataclass(frozen=True)
class ComparisonResult:
    """Legacy and extracted PDF comparison outcome."""

    matches: bool
    differences: Tuple[str, ...]
    legacy: ReportInspection
    extracted: ReportInspection


def _normalized_text(value: str) -> str:
    """Normalize extracted page text without regular expressions."""
    return " ".join(value.split())


def _sha256(value: bytes) -> str:
    """Return a SHA-256 digest for comparable report content."""
    return hashlib.sha256(value).hexdigest()


def _page_size(page) -> Tuple[float, float]:
    """Return one page's MediaBox width and height."""
    media_box = page.MediaBox
    width = float(media_box[2]) - float(media_box[0])
    height = float(media_box[3]) - float(media_box[1])
    return round(width, 3), round(height, 3)


def attachment_hashes(pdf: Pdf) -> Dict[str, str]:
    """Return names-tree and page-annotation attachment content hashes."""
    attachments: Dict[str, str] = {}
    for attachment_name, file_specification in pdf.attachments.items():
        attachment_bytes = file_specification.get_file().read_bytes()
        attachments[str(attachment_name)] = _sha256(attachment_bytes)
    for page in pdf.pages:
        for annotation in page.obj.get("/Annots", []):
            if str(annotation.get("/Subtype", "")) != "/FileAttachment":
                continue
            if "/FS" not in annotation:
                continue
            file_specification = annotation["/FS"]
            embedded_files = file_specification.get("/EF", {})
            if "/F" not in embedded_files:
                continue
            attachment_name = str(
                file_specification.get(
                    "/UF",
                    file_specification.get("/F", "unnamed-attachment"),
                )
            )
            attachments[attachment_name] = _sha256(
                embedded_files["/F"].read_bytes()
            )
    return attachments


def _page_text_hashes(pdf: Pdf) -> Tuple[str, ...]:
    """Extract page text from an in-memory unencrypted PDF copy."""
    unencrypted_buffer = io.BytesIO()
    pdf.save(unencrypted_buffer)
    unencrypted_buffer.seek(0)
    reader = PdfReader(unencrypted_buffer)
    hashes = []
    for page in reader.pages:
        normalized_text = _normalized_text(page.extract_text() or "")
        hashes.append(_sha256(normalized_text.encode("utf-8")))
    return tuple(hashes)


def inspect_report(report_path: Path, password: str) -> ReportInspection:
    """Inspect one encrypted WAS report without writing decrypted content."""
    if not report_path.is_file():
        raise FileNotFoundError(
            "WAS comparison report not found at {}.".format(report_path)
        )
    with Pdf.open(report_path, password=password) as pdf:
        metadata = {
            key: str(pdf.docinfo[key])
            for key in COMPARABLE_METADATA_KEYS
            if key in pdf.docinfo
        }
        return ReportInspection(
            encrypted=pdf.is_encrypted,
            page_count=len(pdf.pages),
            page_sizes=tuple(_page_size(page) for page in pdf.pages),
            page_text_hashes=_page_text_hashes(pdf),
            attachments=attachment_hashes(pdf),
            metadata=metadata,
        )


def compare_reports(
    legacy_path: Path,
    extracted_path: Path,
    password: str,
) -> ComparisonResult:
    """Compare two reports and enumerate every structural difference."""
    legacy = inspect_report(legacy_path, password)
    extracted = inspect_report(extracted_path, password)
    differences: List[str] = []
    fields = (
        "encrypted",
        "page_count",
        "page_sizes",
        "page_text_hashes",
        "attachments",
        "metadata",
    )
    for field_name in fields:
        if getattr(legacy, field_name) != getattr(extracted, field_name):
            differences.append("{} differs".format(field_name))
    return ComparisonResult(
        matches=not differences,
        differences=tuple(differences),
        legacy=legacy,
        extracted=extracted,
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse legacy and extracted report paths."""
    parser = argparse.ArgumentParser(
        description="Compare legacy and extracted encrypted WAS PDF reports."
    )
    parser.add_argument("legacy_report", type=Path)
    parser.add_argument("extracted_report", type=Path)
    return parser.parse_args(argv)


def comparison_password() -> str:
    """Read the comparison password from environment or a hidden prompt."""
    password = getenv(PASSWORD_ENVIRONMENT_NAME)
    if password:
        return password
    return getpass("Report comparison password: ")


def main(argv: Optional[List[str]] = None) -> int:
    """Compare two WAS reports and print a machine-readable result."""
    arguments = parse_args(argv)
    result = compare_reports(
        legacy_path=arguments.legacy_report,
        extracted_path=arguments.extracted_report,
        password=comparison_password(),
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0 if result.matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
