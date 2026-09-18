"""Email message helpers for WAS report delivery."""

# Standard Python Libraries
from datetime import datetime, timezone
from email.headerregistry import Address
from email.message import EmailMessage
from html import escape
from importlib.resources import files
from pathlib import Path
from typing import Iterable, List
from zoneinfo import ZoneInfo

# Third-Party Libraries
from was_reports.data.assignees import (
    list_functional_test_recipient_emails_from_db,
)

# First-Party Libraries
from was_mailer import customer_email_templates
from was_reports.tracker.tracker_csv import tracker_rows_to_csv_text

EASTERN_TIME = ZoneInfo("America/New_York")
ALL_NWS_TEMPLATES = frozenset({"All NWS", "FCEB All NWS"})
ACTION_REQUIRED_TEMPLATES = frozenset(
    {"Action Required", "FCEB Action Required", "Targets Removed"}
)
CYBER_HYGIENE_URL = "https://www.cisa.gov/cyber-hygiene-services"
WAS_ALLOWLIST_URL = "https://rules.vm.cyber.dhs.gov/was.txt"
CISA_LOGO_RESOURCE = "resources/assets/CISA_logo_email.png"
CISA_LOGO_CONTENT_ID = "cisa-logo"


class AnalystRecipientError(ValueError):
    """Indicate that an analyst delivery address failed assignee validation."""


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
    if report_run_email.delivery_purpose not in {"customer", "analyst"}:
        raise ValueError("Unknown WAS report delivery purpose.")
    if report_run_email.delivery_purpose == "analyst":
        return approved_analyst_recipients(override_recipients)
    if override_recipients:
        return unique_addresses(parse_email_addresses(override_recipients))

    addresses = []
    addresses.extend(parse_email_addresses(report_run_email.tech_poc_email))
    addresses.extend(parse_email_addresses(report_run_email.distro_email))
    return unique_addresses(addresses)


def approved_analyst_recipients(raw_addresses: str | None) -> List[str]:
    """Require explicit, valid recipients that are currently active assignees."""
    recipients = unique_addresses(parse_email_addresses(raw_addresses))
    if not recipients:
        raise AnalystRecipientError(
            "At least one email-enabled WAS functional-test recipient is required."
        )
    for recipient in recipients:
        try:
            address = Address(addr_spec=recipient)
        except ValueError as error:
            raise AnalystRecipientError(
                "The submitted email address is invalid. Enter a complete "
                "address using the local@domain format."
            ) from error
        if not address.username or not address.domain:
            raise AnalystRecipientError(
                "The submitted email address is invalid. Enter a complete "
                "address using the local@domain format."
            )
    approved = {
        address.lower()
        for configured in list_functional_test_recipient_emails_from_db()
        for address in parse_email_addresses(configured)
    }
    rejected_recipients = [
        recipient for recipient in recipients if recipient.lower() not in approved
    ]
    if rejected_recipients:
        raise AnalystRecipientError(
            "The submitted email address is not configured as an email-enabled "
            "WAS functional-test recipient: {}.".format(
                ", ".join(rejected_recipients)
            )
        )
    return recipients


def build_stakeholder_export_email(
    source_email: str,
    recipients: List[str],
    export_path: Path,
    includes_passwords: bool = False,
) -> EmailMessage:
    """Build an analyst-only stakeholder database export email."""
    if not recipients:
        raise ValueError("At least one assignee recipient is required.")
    if not export_path.is_file() or export_path.suffix.lower() != ".csv":
        raise FileNotFoundError("The stakeholder CSV export was not found.")
    message = EmailMessage()
    message["From"] = source_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = "WAS Stakeholder Database Export - Analyst Copy"
    password_notice = (
        "This export contains stakeholder report passwords."
        if includes_passwords
        else "This export does not contain stakeholder report passwords."
    )
    message.set_content(
        "The requested WAS stakeholder database export is attached.\n\n"
        "{}\n\nDo not forward this attachment outside the approved WAS team.".format(
            password_notice
        )
    )
    message.add_attachment(
        export_path.read_bytes(),
        maintype="text",
        subtype="csv",
        filename=export_path.name,
    )
    return message


def build_report_email(
    source_email: str,
    recipients: List[str],
    stakeholder_tag: str,
    report_path: Path | None,
    poc_name: str | None = None,
    template: str | None = None,
    assignee_name: str | None = None,
    recent_nws: str | None = None,
    nws_summary: str | None = None,
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
        poc_name=poc_name,
        template=normalized_template,
        assignee_name=assignee_name,
        recent_nws=recent_nws,
        nws_summary=nws_summary,
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
    html_part = message.get_payload()[-1]
    html_part.add_related(
        files("was_reports").joinpath(CISA_LOGO_RESOURCE).read_bytes(),
        maintype="image",
        subtype="png",
        cid="<{}>".format(CISA_LOGO_CONTENT_ID),
        filename="CISA_logo_email.png",
        disposition="inline",
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


def eastern_date(epoch_value: int | None) -> str | None:
    """Format an epoch timestamp as the customer-facing Eastern calendar date."""
    if epoch_value is None:
        return None
    timestamp = datetime.fromtimestamp(epoch_value, tz=timezone.utc)
    return timestamp.astimezone(EASTERN_TIME).strftime("%B %d, %Y")


def nws_counts(raw_summary: str | None) -> tuple[int, int] | None:
    """Return total and inaccessible counts from the tracker NWS summary."""
    if not raw_summary:
        return None
    parts = [part.strip() for part in raw_summary.split(",")]
    if len(parts) < 2:
        return None
    try:
        total_count = int(parts[0])
        inaccessible_count = int(parts[1])
    except ValueError:
        return None
    if total_count < 0 or inaccessible_count < 0:
        return None
    return total_count, inaccessible_count


def append_value_list(lines: list[str], heading: str, values: list[str]) -> None:
    """Append a labeled customer-safe value list to an email body."""
    if not values:
        return
    lines.extend([heading, *["- {}".format(value) for value in values], ""])


def report_email_body(
    stakeholder_tag: str,
    poc_name: str | None,
    template: str,
    assignee_name: str | None,
    recent_nws: str | None,
    nws_summary: str | None,
    remove_nws: str | None,
    qualys_error: str | None,
    last_scanned: int | None,
    next_scheduled: int | None,
    analyst_delivery: bool = False,
) -> str:
    """Return the approved plain-text body for a WAS tracker outcome."""
    greeting_name = (poc_name or "").strip()
    greeting = (
        "Hello {},".format(greeting_name)
        if greeting_name and not analyst_delivery
        else "Hello,"
    )
    lines = [greeting, ""]
    if analyst_delivery:
        lines.extend(
            [
                "The requested on-demand WAS report for {} is attached for "
                "analyst review. This message is not a customer delivery.".format(
                    stakeholder_tag
                ),
                "",
                "Regards,",
                assignee_name or "CISA WAS Reporting Team",
            ]
        )
        return "\n".join(lines)

    if template not in ALL_NWS_TEMPLATES:
        lines.extend(
            [
                customer_email_templates.ALLOWLIST_NOTICE.format(
                    allowlist_url=WAS_ALLOWLIST_URL
                ),
                "",
                customer_email_templates.REPORT_ATTACHMENT_NOTICE,
                "",
                customer_email_templates.SENSITIVE_DATA_NOTICE,
                "",
            ]
        )
    else:
        lines.extend([customer_email_templates.NO_REPORT_NOTICE, ""])

    inaccessible_targets = tracker_values(recent_nws)
    if inaccessible_targets:
        counts = nws_counts(nws_summary)
        if counts is None:
            lines.append(customer_email_templates.INACCESSIBLE_TARGETS)
        else:
            total_count, inaccessible_count = counts
            lines.append(
                customer_email_templates.INACCESSIBLE_TARGETS_WITH_COUNTS.format(
                    inaccessible_count=inaccessible_count,
                    total_count=total_count,
                )
            )
        lines.extend([*["- {}".format(value) for value in inaccessible_targets], ""])
        lines.append(customer_email_templates.INACCESSIBLE_REASONS_HEADING)
        lines.extend(
            [
                *[
                    "- {}".format(reason)
                    for reason in customer_email_templates.INACCESSIBLE_REASONS
                ],
                "",
            ]
        )

        if template in {"FCEB All NWS", "FCEB Action Required"}:
            lines.extend([customer_email_templates.FCEB_RETENTION_NOTICE, ""])
        elif template == "All NWS":
            lines.extend([customer_email_templates.TWO_SCAN_REMOVAL_NOTICE, ""])

    if template == "Targets Removed":
        removed_targets = tracker_values(remove_nws)
        append_value_list(
            lines,
            customer_email_templates.REMOVED_TARGETS_HEADING,
            removed_targets,
        )
        if removed_targets:
            lines.extend(
                [customer_email_templates.TARGETS_REMOVED_REQUEST_NOTICE, ""]
            )
    qualys_error_targets = tracker_values(qualys_error)
    append_value_list(
        lines,
        customer_email_templates.QUALYS_ERROR_HEADING,
        qualys_error_targets,
    )
    if qualys_error_targets:
        lines.extend([customer_email_templates.QUALYS_ERROR_RESCAN_NOTICE, ""])

    if template not in ALL_NWS_TEMPLATES:
        lines.extend(
            [
                customer_email_templates.APPENDIX_NOTICE.format(
                    faq_url=CYBER_HYGIENE_URL
                ),
                "",
                customer_email_templates.PASSWORD_SUPPORT_NOTICE,
                "",
            ]
        )

    lines.extend([customer_email_templates.QUESTIONS_NOTICE, ""])
    next_scan_date = eastern_date(next_scheduled)
    if next_scan_date is not None:
        lines.extend(
            [
                customer_email_templates.NEXT_SCAN_NOTICE.format(
                    next_scan_date=next_scan_date
                ),
                "",
            ]
        )
    lines.extend(
        [
            "Regards,",
            assignee_name or "CISA WAS Reporting Team",
            *customer_email_templates.CUSTOMER_SIGNATURE,
        ]
    )
    return "\n".join(lines)


def customer_email_html_line(line: str) -> str:
    """Return approved HTML formatting for one customer-email text line."""
    escaped_line = escape(line)
    if line == customer_email_templates.SENSITIVE_DATA_NOTICE:
        note_label = escape("Important Note:")
        notice_text = escape(line.removeprefix("Important Note: "))
        notice_text = notice_text.replace(
            "will not",
            "<u>will not</u>",
            1,
        )
        return (
            '<span style="background-color:#f8e71c">'
            "<strong>{}</strong> <em>{}</em></span>"
        ).format(note_label, notice_text)
    if line == customer_email_templates.APPENDIX_NOTICE.format(
        faq_url=CYBER_HYGIENE_URL
    ):
        appendix_heading = (
            "Additional details regarding findings, links crawled, "
            "vulnerabilities by webapp and severity, sensitive data found, "
            "etc., can be found under Appendix C: Attachments."
        )
        escaped_line = escaped_line.replace(
            escape(appendix_heading),
            "<strong>{}</strong>".format(escape(appendix_heading)),
            1,
        )
        paperclip_instruction = "double-click on the paper clip icon"
        escaped_line = escaped_line.replace(
            escape(paperclip_instruction),
            "<u>{}</u>".format(escape(paperclip_instruction)),
            1,
        )
        return customer_email_html_links(escaped_line)
    if line.startswith("Results indicate that "):
        prefix = "Results indicate that "
        inaccessible_count, separator, remainder = line.removeprefix(prefix).partition(
            " out of "
        )
        total_count, count_separator, suffix = remainder.partition(
            " web applications"
        )
        if separator and count_separator:
            return (
                "{}<strong>{}</strong> out of <strong>{}</strong> "
                "web applications{}"
            ).format(
                escape(prefix),
                escape(inaccessible_count),
                escape(total_count),
                escape(suffix),
            )
    if line.startswith("Your next scan is scheduled for "):
        prefix = "Your next scan is scheduled for "
        return "{}<strong>{}</strong>".format(
            escape(prefix),
            escape(line.removeprefix(prefix)),
        )
    if line in {
        customer_email_templates.QUALYS_ERROR_HEADING,
        customer_email_templates.REMOVED_TARGETS_HEADING,
    }:
        return "<strong>{}</strong>".format(escaped_line)
    if line in customer_email_templates.CUSTOMER_SIGNATURE:
        return '<span style="color:#552479">{}</span>'.format(escaped_line)
    return customer_email_html_links(escaped_line)


def customer_email_html_links(escaped_line: str) -> str:
    """Render approved customer-email URLs as underlined links."""
    rendered_line = escaped_line
    for url in (WAS_ALLOWLIST_URL, CYBER_HYGIENE_URL):
        escaped_url = escape(url)
        rendered_line = rendered_line.replace(
            escaped_url,
            '<a href="{}"><u>{}</u></a>'.format(escaped_url, escaped_url),
        )
    return rendered_line


def report_email_html(plain_body: str, stakeholder_tag: str) -> str:
    """Return an accessible, template-formatted HTML customer email."""
    body_parts = []
    list_items = []
    signature_name_pending = False

    def append_list() -> None:
        """Append any pending list items to the HTML body."""
        if not list_items:
            return
        body_parts.append("<ul>{}</ul>".format("".join(list_items)))
        list_items.clear()

    for line in plain_body.splitlines():
        if line.startswith("- "):
            list_items.append(
                "<li>{}</li>".format(customer_email_html_line(line[2:]))
            )
            continue
        append_list()
        if not line:
            body_parts.append("<br>")
            continue
        rendered_line = customer_email_html_line(line)
        if signature_name_pending:
            rendered_line = (
                '<strong><span style="color:#552479">{}</span></strong>'
            ).format(escape(line))
            signature_name_pending = False
        body_parts.append("<div>{}</div>".format(rendered_line))
        if line == "Regards,":
            signature_name_pending = True
    append_list()
    return (
        "<!doctype html><html><body>"
        '<h1 style="font-size:1.25rem">WAS Results for {}</h1>{}'
        '<div style="margin-top:1.5rem">'
        '<img src="cid:{}" alt="CISA" style="max-width:240px;height:auto">'
        "</div>"
        "</body></html>"
    ).format(
        escape(stakeholder_tag),
        "".join(body_parts),
        CISA_LOGO_CONTENT_ID,
    )


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
