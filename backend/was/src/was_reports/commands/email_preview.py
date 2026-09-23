"""Build one customer-email preview from synthetic data without delivery."""

import argparse
import base64
from datetime import date, datetime, timezone
from email import policy
from importlib.resources import files
from pathlib import Path

from was_mailer.message import ALL_NWS_TEMPLATES, build_report_email

TEMPLATES = (
    "Results",
    "Action Required",
    "Targets Removed",
    "All NWS",
    "FCEB Action Required",
    "FCEB All NWS",
)


def create_preview(
    output_directory: Path,
    template: str,
    report_pdf: Path | None,
    qualys_error: bool = False,
    report_date: date | None = None,
) -> tuple[Path, Path, Path]:
    """Save the production MIME message plus browser and plain-text previews.

    The recipient, customer, targets, and analyst are synthetic. The provided
    PDF is attached unchanged. This function never calls SES or the database.
    """
    if template not in TEMPLATES:
        raise ValueError("Unknown customer-email template.")
    has_nws = template != "Results"
    has_removed = template == "Targets Removed"
    all_nws = template in ALL_NWS_TEMPLATES
    message = build_report_email(
        source_email="reports@cyber.dhs.gov",
        recipients=["preview@example.invalid"],
        stakeholder_tag="OFFLINE",
        report_path=None if all_nws else report_pdf,
        poc_name="Sample POC",
        template=template,
        assignee_name="Sample Analyst",
        recent_nws=("https://unavailable.example.invalid" if has_nws else None),
        nws_summary=("1, 1, 0" if all_nws else "3, 1, 1" if has_removed else "3, 1, 0"),
        remove_nws=("https://unavailable.example.invalid" if has_removed else None),
        qualys_error=("https://error.example.invalid" if qualys_error else None),
        last_scanned=int(datetime(2026, 8, 26, 13, tzinfo=timezone.utc).timestamp()),
        next_scheduled=int(datetime(2026, 9, 26, 13, tzinfo=timezone.utc).timestamp()),
        report_date=report_date,
    )
    output_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    name = template.lower().replace(" ", "-")
    if qualys_error:
        name += "-qualys-error"
    mime_path = output_directory / (name + ".eml")
    html_path = output_directory / (name + ".html")
    text_path = output_directory / (name + ".txt")
    logo = files("was_reports").joinpath("resources/assets/CISA_logo_email.png")
    logo_data = "data:image/png;base64," + base64.b64encode(logo.read_bytes()).decode("ascii")
    html_body = message.get_body(preferencelist=("html",)).get_content()
    plain_body = message.get_body(preferencelist=("plain",)).get_content()
    mime_path.write_bytes(message.as_bytes(policy=policy.SMTP))
    html_path.write_text(html_body.replace("cid:cisa-logo", logo_data), encoding="utf-8")
    text_path.write_text(plain_body, encoding="utf-8")
    for preview_path in (mime_path, html_path, text_path):
        preview_path.chmod(0o600)
    return mime_path, html_path, text_path


def main(argv: list[str] | None = None) -> int:
    """Generate a single selected template for review without sending it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", choices=TEMPLATES, default="Results")
    parser.add_argument("--report-pdf", type=Path)
    parser.add_argument(
        "--report-date", type=date.fromisoformat,
        help="Explicit generation date (YYYY-MM-DD) for PDFs without a dated filename.",
    )
    parser.add_argument("--qualys-error", action="store_true")
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.template not in ALL_NWS_TEMPLATES and args.report_pdf is None:
        parser.error("--report-pdf is required for templates that attach a report")
    paths = create_preview(
        args.output_directory, args.template, args.report_pdf, args.qualys_error,
        args.report_date,
    )
    print("Synthetic preview only. No database changes or email delivery.")
    for preview_path in paths:
        print(preview_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
