"""Output file helpers for WAS report generation."""

# Standard Python Libraries
from datetime import date
from pathlib import Path
from typing import Optional


def expected_pdf_output_path(
    stakeholder_tag: str,
    output_directory: str,
    report_date: Optional[date] = None,
) -> Path:
    """Return the expected legacy PDF output path for a stakeholder report."""
    resolved_report_date = report_date if report_date is not None else date.today()
    filename = "{}_report_{}.pdf".format(
        stakeholder_tag,
        resolved_report_date.isoformat(),
    )
    return Path(output_directory) / filename


def require_output_file(output_path: Path) -> Path:
    """Return an output file path after confirming it exists."""
    if not output_path.is_file():
        raise FileNotFoundError(
            "Expected WAS report output was not found at {}.".format(str(output_path))
        )

    return output_path
