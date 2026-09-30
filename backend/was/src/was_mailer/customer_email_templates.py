"""Compose the approved September 21 email components without rewriting them."""

from html import escape

from was_mailer.authoritative_email_sections import SECTIONS

ALL_NWS_TEMPLATES = frozenset({"All NWS", "FCEB All NWS"})
FCEB_TEMPLATES = frozenset({"FCEB Action Required", "FCEB All NWS"})

# Operator-approved September 30 sender-change notice, shared by every template.
SENDER_CHANGE_NOTICE = (
    "Notice: WAS reports now come from this email address: reports@cyber.dhs.gov. "
    'Please reference the email, "Cyber Hygiene (CyHy) WAS Report Email Address Change", '
    "sent from vulnerability@cisa.dhs.gov on 9/30/26. "
    "Inquiries should still be sent to vulnerability@cisa.dhs.gov."
)

# September 23 correction restores the source questions address verbatim.
# The signature address remains reports@cyber.dhs.gov in the source sections.


def section_names(
    template: str,
    has_nws: bool,
    has_removed: bool,
    has_errors: bool,
) -> list[str]:
    """Select sections in the order specified by the supplied flowchart."""
    if template in ALL_NWS_TEMPLATES:
        return ["report_not_generated", "results_part2"]
    names = ["results_part1"]
    if has_errors:
        names.append("qualys_scan_error")
    if has_nws:
        names.append("nws_notification")
        if template not in FCEB_TEMPLATES:
            names.append("nws_webapp_removal_warning")
            if has_removed:
                names.append("targets_removed")
    names.append("results_part2")
    return names


def substitute_values(source: str, values: dict[str, str], html: bool) -> str:
    """Substitute source placeholders once, escaping all supplied customer data."""
    opening = "&lt;" if html else "<"
    closing = "&gt;" if html else ">"
    rendered = []
    remaining = source
    while opening in remaining:
        prefix, _, candidate = remaining.partition(opening)
        name, separator, suffix = candidate.partition(closing)
        rendered.append(prefix)
        if not separator:
            rendered.append(opening + candidate)
            break
        if name not in values:
            rendered.append(opening + name + closing)
        elif html and name == "cisa_logo":
            rendered.append(
                '<img src="cid:cisa-logo" alt="CISA" '
                'style="max-width:240px;height:auto">'
            )
        else:
            value = values[name]
            rendered.append(escape(value).replace("\n", "<br>") if html else value)
        remaining = suffix
    else:
        rendered.append(remaining)
    return "".join(rendered)


def render_sections(
    template: str,
    values: dict[str, str],
    has_nws: bool,
    has_removed: bool,
    has_errors: bool,
    html: bool = False,
) -> str:
    """Render exact source sections, changing only documented placeholders."""
    names = section_names(template, has_nws, has_removed, has_errors)
    source = ("<br>\n" if html else "\n\n").join(
        SECTIONS[name]["html" if html else "text"] for name in names
    )
    body = substitute_values(source, values, html)
    if html:
        notice = escape(SENDER_CHANGE_NOTICE).replace(
            "vulnerability@cisa.dhs.gov",
            "<strong>vulnerability@cisa.dhs.gov</strong>",
        )
        body = "<div><em>{}</em></div><br>\n{}".format(notice, body)
    else:
        body = SENDER_CHANGE_NOTICE + "\n\n" + body
    if html:
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8"></head><body '
            'style="font-family:Aptos,Calibri,Arial,sans-serif;font-size:11pt">'
            + body
            + "</body></html>"
        )
    return body.rstrip()
