"""Email message helpers for WAS report delivery."""

# Standard Python Libraries
from email.message import EmailMessage
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Iterable, List
from zoneinfo import ZoneInfo

# Third-Party Libraries
# First-Party Libraries
from was_reports.tracker.tracker_csv import tracker_rows_to_csv_text

EASTERN_TIME = ZoneInfo("America/New_York")
ALL_NWS_TEMPLATES = frozenset({"All NWS", "FCEB All NWS"})
ACTION_REQUIRED_TEMPLATES = frozenset(
    {"Action Required", "FCEB Action Required", "Targets Removed"}
)
CYBER_HYGIENE_URL = "https://www.cisa.gov/cyber-hygiene-services"
WAS_ALLOWLIST_URL = "https://rules.vm.cyber.dhs.gov/was.txt"


def parse_email_addresses(raw_addresses: str | None) -> List[str]:
    """Parse semicolon or comma separated email addresses."""
    if not raw_addresses:
        return []

    addresses = []
    for semicolon_part in raw_addresses.split(";"):
        for comma_part in semicolon_part.split(","):
            address = comma_part.strip()
            if address:
                addresses.append(address)

    return addresses


def unique_addresses(addresses: Iterable[str]) -> List[str]:
    """Return unique email addresses while preserving order."""
    seen_addresses = set()
    unique = []
    for address in addresses:
        normalized_address = address.lower()
        if normalized_address in seen_addresses:
            continue
        seen_addresses.add(normalized_address)
        unique.append(address)
    return unique


def recipient_addresses(
    report_run_email,
    override_recipients: str | None = None,
) -> List[str]:
    """Return final recipients for a WAS report email."""
    if override_recipients:
        return unique_addresses(parse_email_addresses(override_recipients))

    addresses = []
    addresses.extend(parse_email_addresses(report_run_email.tech_poc_email))
    addresses.extend(parse_email_addresses(report_run_email.distro_email))
    return unique_addresses(addresses)


def build_report_email(
    source_email: str,
    recipients: List[str],
    stakeholder_tag: str,
    report_path: Path | None,
    template: str | None = None,
    assignee_name: str | None = None,
    recent_nws: str | None = None,
    remove_nws: str | None = None,
    qualys_error: str | None = None,
    last_scanned: int | None = None,
    next_scheduled: int | None = None,
    analyst_delivery: bool = False,
) -> EmailMessage:
    """Build a tracker-aware WAS customer email and optional PDF attachment."""
    if not recipients:
        raise ValueError("At least one report email recipient is required.")

    normalized_template = template or "Results"
    attachment_required = normalized_template not in ALL_NWS_TEMPLATES
    if attachment_required and (report_path is None or not report_path.is_file()):
        raise FileNotFoundError(
            "WAS report attachment was not found at {}.".format(
                str(report_path) if report_path else "<none>"
            )
        )

    message = EmailMessage()
    message["From"] = source_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = report_email_subject(
        stakeholder_tag=stakeholder_tag,
        template=normalized_template,
        analyst_delivery=analyst_delivery,
    )
    plain_body = report_email_body(
        stakeholder_tag=stakeholder_tag,
        template=normalized_template,
        assignee_name=assignee_name,
        recent_nws=recent_nws,
        remove_nws=remove_nws,
        qualys_error=qualys_error,
        last_scanned=last_scanned,
        next_scheduled=next_scheduled,
        analyst_delivery=analyst_delivery,
    )
    message.set_content(plain_body)
    message.add_alternative(
        report_email_html(
            plain_body=plain_body,
            stakeholder_tag=stakeholder_tag,
        ),
        subtype="html",
    )

    if attachment_required and report_path is not None:
        with report_path.open("rb") as report_file:
            report_bytes = report_file.read()

        message.add_attachment(
            report_bytes,
            maintype="application",
            subtype="pdf",
            filename=report_path.name,
        )
    return message


def report_email_subject(
    stakeholder_tag: str,
    template: str,
    analyst_delivery: bool = False,
) -> str:
    """Return the approved subject for a tracker-selected email template."""
    if analyst_delivery:
        return "{} WAS Results - Analyst Copy".format(stakeholder_tag)
    if template in ACTION_REQUIRED_TEMPLATES or template in ALL_NWS_TEMPLATES:
        return "{} WAS Results - Action Required".format(stakeholder_tag)
    return "{} WAS Results".format(stakeholder_tag)


def tracker_values(raw_value: str | None) -> list[str]:
    """Return tracker list values stored with legacy HTML separators."""
    if not raw_value:
        return []
    return [value.strip() for value in raw_value.split("<br>") if value.strip()]


def eastern_timestamp(epoch_value: int | None) -> str:
    """Format an epoch timestamp for customer display in Eastern Time."""
    if epoch_value is None:
        return "Not available"
    timestamp = datetime.fromtimestamp(epoch_value, tz=timezone.utc)
    return timestamp.astimezone(EASTERN_TIME).strftime(
        "%B %d, %Y at %I:%M %p Eastern Time"
    )


def append_value_list(lines: list[str], heading: str, values: list[str]) -> None:
    """Append a labeled customer-safe value list to an email body."""
    if not values:
        return
    lines.extend([heading, *["- {}".format(value) for value in values], ""])


def report_email_body(
    stakeholder_tag: str,
    template: str,
    assignee_name: str | None,
    recent_nws: str | None,
    remove_nws: str | None,
    qualys_error: str | None,
    last_scanned: int | None,
    next_scheduled: int | None,
    analyst_delivery: bool = False,
) -> str:
    """Return the approved plain-text body for a WAS tracker outcome."""
    lines = ["Hello,", ""]
    if analyst_delivery:
        lines.append(
            "The requested on-demand WAS report for {} is attached for "
            "analyst review. This message is not a customer delivery.".format(
                stakeholder_tag
            )
        )
    elif template in ALL_NWS_TEMPLATES:
        lines.append(
            "The latest WAS scan for {} found no accessible web services. "
            "No PDF report was generated for this scan.".format(stakeholder_tag)
        )
    else:
        lines.append(
            "The latest WAS report for {} is attached.".format(stakeholder_tag)
        )
    lines.extend(
        [
            "",
            "Last scan: {}".format(eastern_timestamp(last_scanned)),
            "Next scheduled scan: {}".format(
                eastern_timestamp(next_scheduled)
            ),
            "",
        ]
    )

    append_value_list(
        lines,
        "Web applications with no accessible web service:",
        tracker_values(recent_nws),
    )
    if template == "Targets Removed":
        append_value_list(
            lines,
            "Web applications removed from Qualys after two consecutive "
            "inaccessible scans:",
            tracker_values(remove_nws),
        )
    if template == "FCEB All NWS" or template == "FCEB Action Required":
        lines.extend(
            [
                "FCEB web applications remain enrolled during inaccessible "
                "scans and are removed only at the customer's request.",
                "",
            ]
        )
    append_value_list(
        lines,
        "The following web applications encountered Qualys errors and do not "
        "have updated results in this report:",
        tracker_values(qualys_error),
    )
    lines.extend(
        [
            "Qualys is currently unable to provide the sensitive-data "
            "attachment for Social Security number and credit-card findings. "
            "This temporary notice will be removed after Qualys restores the "
            "capability.",
            "",
            "CISA Cyber Hygiene Services: {}".format(CYBER_HYGIENE_URL),
            "WAS scanner IP allowlist: {}".format(WAS_ALLOWLIST_URL),
            "",
            "Thank you,",
            assignee_name or "CISA WAS Reporting Team",
        ]
    )
    return "\n".join(lines)


def report_email_html(plain_body: str, stakeholder_tag: str) -> str:
    """Return a simple accessible HTML alternative for a WAS customer email."""
    paragraphs = []
    for line in plain_body.splitlines():
        if not line:
            paragraphs.append("<br>")
        elif line.startswith("- "):
            paragraphs.append("<div>&bull; {}</div>".format(escape(line[2:])))
        else:
            paragraphs.append("<div>{}</div>".format(escape(line)))
    return (
        "<!doctype html><html><body>"
        "<h1 style=\"font-size:1.25rem\">WAS Results for {}</h1>{}"
        "</body></html>"
    ).format(escape(stakeholder_tag), "".join(paragraphs))


def build_assignee_digest_email(
    source_email: str,
    recipients: List[str],
    assignee_digest,
) -> EmailMessage:
    """Build a daily WAS tracker digest email for one assignee."""
    if not recipients:
        raise ValueError("At least one assignee digest recipient is required.")

    message = EmailMessage()
    message["From"] = source_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = "WAS Daily Tracker Assignments for {}".format(
        assignee_digest.assignee
    )
    message.set_content(assignee_digest_body(assignee_digest))
    message.add_attachment(
        tracker_rows_to_csv_text(assignee_digest.rows).encode("utf-8"),
        maintype="text",
        subtype="csv",
        filename=assignee_digest_csv_filename(assignee_digest.assignee),
    )
    return message


def assignee_digest_body(assignee_digest) -> str:
    """Return the plain text body for an assignee digest."""
    manual_rows = [
        tracker_row
        for tracker_row in assignee_digest.rows
        if tracker_row_is_manual(tracker_row)
    ]
    sent_rows = [
        tracker_row
        for tracker_row in assignee_digest.rows
        if tracker_row.report_sent_date is not None
    ]
    pending_rows = [
        tracker_row
        for tracker_row in assignee_digest.rows
        if tracker_row.report_sent_date is None
        and not tracker_row_is_manual(tracker_row)
    ]
    lines = [
        "WAS daily tracker assignments for {}".format(assignee_digest.assignee),
        "",
        "Total assigned rows: {}".format(len(assignee_digest.rows)),
        "Reports sent: {}".format(len(sent_rows)),
        "Manual reports: {}".format(len(manual_rows)),
        "Reports pending: {}".format(len(pending_rows)),
        "",
    ]
    for tracker_row in assignee_digest.rows:
        lines.append("Tag: {}".format(tracker_row.tag or ""))
        lines.append("Scan Name: {}".format(tracker_row.scan_name or ""))
        lines.append("Status: {}".format(tracker_row.status or ""))
        lines.append("Result: {}".format(tracker_row.result or ""))
        lines.append("Template: {}".format(tracker_row.template or ""))
        lines.append("Next Scan Date: {}".format(tracker_row.next_scan_date or ""))
        lines.append("Notes: {}".format(tracker_row.report_scan_notes or ""))
        lines.append("")
    lines.append("Do not reply with report passwords or scanner credentials.")
    return "\n".join(lines)


def tracker_row_is_manual(tracker_row) -> bool:
    """Return whether a tracker row requires manual analyst handling."""
    notes = (tracker_row.report_scan_notes or "").strip().upper()
    status = (tracker_row.status or "").strip().upper()
    return bool(notes) or status == "ERROR" or bool(tracker_row.qualys_error)


def assignee_digest_csv_filename(assignee_name: str) -> str:
    """Return a safe CSV filename for an assignee digest."""
    characters = []
    for character in assignee_name.strip().lower():
        if character.isalnum():
            characters.append(character)
        elif character in [" ", "-", "_"]:
            characters.append("-")
    safe_name = "".join(characters).strip("-")
    if not safe_name:
        safe_name = "assignee"
    return "was-daily-tracker-{}.csv".format(safe_name)
