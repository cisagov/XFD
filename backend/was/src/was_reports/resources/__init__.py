"""Packaged templates and assets required to render WAS reports."""

# Standard Python Libraries
from pathlib import Path
from typing import Tuple

REQUIRED_RESOURCE_PATHS: Tuple[str, ...] = (
    "NEW_BIG.mustache",
    "cisa_marker_new.pdf",
    "pdf_redactor.py",
    "redact_qualys.py",
    "assets/CISA_Logo.png",
    "assets/CoverPage_Template.pdf",
    "assets/TLP_AMBER.png",
    "assets/TLP_DEFINITIONS.png",
    "assets/TOC.pdf",
    "assets/WAS_TITLE.png",
    "assets/WAS_TITLE_SMALLER.png",
    "assets/assessment-summary-title.pdf",
    "assets/cisa-logo.png",
    "assets/cisa_footer.png",
    "assets/figure1.png",
    "assets/figure3.png",
    "assets/fonts/Franklin Gothic Book Regular.ttf",
    "assets/fonts/Franklin Gothic Medium Italic.ttf",
    "assets/fonts/Franklin Gothic Medium Regular.ttf",
    "assets/fonts/Franklin Gothic-Bold.ttf",
    "assets/fonts/Franklin Gothic-BoldItalic.ttf",
    "assets/fonts/Franklin Gothic-Italic.ttf",
    "assets/fonts/Franklin Gothic.ttf",
    "assets/owasp_graph.png",
    "assets/regularpage.pdf",
    "assets/reportcard.pdf",
    "assets/table_content.jpeg",
    "assets/was_report.xml",
    "assets/was_report_details.xml",
)


def report_resource_root() -> Path:
    """Return the filesystem root containing packaged report resources."""
    return Path(__file__).resolve().parent


def missing_report_resources(resource_root: Path | None = None) -> Tuple[str, ...]:
    """Return required report resource paths that are not present."""
    resolved_root = resource_root or report_resource_root()
    return tuple(
        relative_path
        for relative_path in REQUIRED_RESOURCE_PATHS
        if not (resolved_root / relative_path).is_file()
    )


def require_report_resources(resource_root: Path | None = None) -> Path:
    """Return a complete report resource root or raise a clear error."""
    resolved_root = resource_root or report_resource_root()
    missing_paths = missing_report_resources(resolved_root)
    if missing_paths:
        raise FileNotFoundError(
            "Missing required WAS report resources: {}".format(
                ", ".join(missing_paths)
            )
        )
    return resolved_root
