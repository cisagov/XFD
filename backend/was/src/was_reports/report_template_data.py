"""Assemble the legacy Mustache data contract for a WAS report."""

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Mapping, Optional, Set, Union

# First-Party Libraries
from was_reports import latex_renderer, report_metrics
from was_reports.report_artifacts import ReportArtifactResult

REQUIRED_TEMPLATE_FIELDS: Set[str] = {
    "AppOverviewCSV",
    "AppOverviewCSVTex",
    "Bugcrowd",
    "Burp",
    "CrossSite",
    "CtlColor",
    "DetailsCSV",
    "DetailsCSVTex",
    "EmailsFound",
    "EmailsFoundTex",
    "InfoCSV",
    "InfoCSVTex",
    "InfoDisc",
    "LinksCrawled",
    "LinksCrawledTex",
    "LinksRejected",
    "LinksRejectedTex",
    "NameLen",
    "NewVulns",
    "NewVulnsColor",
    "NumApps",
    "OrgName",
    "PathDisc",
    "PdfFile",
    "Reopened",
    "ReopenedColor",
    "RiskColor",
    "SecurityRisk",
    "Sensitive",
    "SensitiveColor",
    "SqlInj",
    "StartDate",
    "TotInfo",
    "TotVulns",
    "TotVulnsColor",
    "UrgColor",
    "VulnCSV",
    "VulnCSVTex",
    "lev1",
    "lev2",
    "lev3",
    "lev4",
    "lev5",
    "maxctl",
    "maxurg",
}


@dataclass(frozen=True)
class TemplateArtifactInputs:
    """Artifact filenames consumed by the legacy report template."""

    vulnerability_details: str
    information_details: str
    generated: ReportArtifactResult
    detail_pdf: Optional[str] = None


@dataclass(frozen=True)
class FindingAgeInputs:
    """Maximum ages displayed on the legacy report card."""

    critical_days: Union[str, int]
    urgent_days: Union[str, int]


def _detail_pdf_block(
    detail_pdf_filename: Optional[str],
    web_application_count: int,
) -> str:
    """Return the preserved optional detail-PDF attachment block."""
    if web_application_count >= 35 or not detail_pdf_filename:
        return ""
    safe_filename = latex_renderer.validate_filename_component(
        Path(detail_pdf_filename).name
    )
    escaped_filename = latex_renderer.escape_latex(safe_filename)
    return """\\newline

\\textbf{{Attachment 9: Details PDF}}
\\newline
\\attachfile[appearance=false,mimetype=application/pdf,icon=Paperclip,ucfilespec=assets/{escaped}]{{assets/{filename}}}
{escaped}: Detailed PDF Report of all findings.
""".format(escaped=escaped_filename, filename=safe_filename)


def _artifact_fields(artifacts: TemplateArtifactInputs) -> Dict[str, str]:
    """Return raw and LaTeX-safe attachment filename fields."""
    filename_fields = {
        "DetailsCSV": artifacts.vulnerability_details,
        "InfoCSV": artifacts.information_details,
        "VulnCSV": artifacts.generated.vulnerabilities_by_webapp,
        "AppOverviewCSV": artifacts.generated.application_overview,
        "LinksCrawled": artifacts.generated.links_crawled,
        "LinksRejected": artifacts.generated.rejected_links,
        "EmailsFound": artifacts.generated.emails_found,
    }
    fields = dict(filename_fields)
    for field_name, filename in filename_fields.items():
        latex_field_name = "{}Tex".format(field_name)
        fields[latex_field_name] = latex_renderer.escape_latex(filename)
    return fields


def validate_template_data(template_data: Mapping[str, object]) -> None:
    """Raise when a field required by the preserved template is absent."""
    missing_fields = REQUIRED_TEMPLATE_FIELDS.difference(template_data)
    if missing_fields:
        raise ValueError(
            "Missing WAS template fields: {}.".format(
                ", ".join(sorted(missing_fields))
            )
        )


def find_template_fields(template_text: str) -> Set[str]:
    """Return Mustache field names without relying on regular expressions."""
    fields: Set[str] = set()
    search_position = 0
    while True:
        field_start = template_text.find("<<", search_position)
        if field_start < 0:
            return fields
        field_end = template_text.find(">>", field_start + 2)
        if field_end < 0:
            return fields
        field_name = template_text[field_start + 2:field_end].strip()
        if field_name:
            fields.add(field_name)
        search_position = field_end + 2


def build_template_data(
    report_xml,
    stakeholder_tag: str,
    organization_name: str,
    artifacts: TemplateArtifactInputs,
    finding_ages: FindingAgeInputs,
    web_application_count: int,
    current_time: datetime,
) -> Dict[str, str]:
    """Build every field required by the legacy NEW_BIG Mustache template."""
    summary = report_metrics.calculate_summary_metrics(report_xml)
    findings = report_metrics.calculate_finding_metrics(report_xml, current_time)
    severity_totals = report_metrics.calculate_severity_totals(report_xml)
    escaped_organization_name = latex_renderer.escape_latex(organization_name)
    critical_age = str(finding_ages.critical_days)
    urgent_age = str(finding_ages.urgent_days)

    template_data = {
        "StartDate": summary.start_date,
        "SecurityRisk": summary.security_risk,
        "TotInfo": summary.total_information_findings,
        "NumApps": summary.web_application_count,
        "RiskColor": summary.risk_color,
        "Sensitive": summary.sensitive_content_count,
        "SensitiveColor": summary.sensitive_color,
        "OrgName": escaped_organization_name,
        "NameLen": latex_renderer.organization_name_width(
            escaped_organization_name
        ),
        "OrgTag": latex_renderer.escape_latex(stakeholder_tag),
        "PathDisc": str(findings.group_counts["Path Disclosure"]),
        "InfoDisc": str(findings.group_counts["Information Disclosure"]),
        "CrossSite": str(findings.group_counts["Cross-Site Scripting"]),
        "Burp": str(findings.group_counts["Burp"]),
        "SqlInj": str(findings.group_counts["SQL Injection"]),
        "Bugcrowd": str(findings.group_counts["Bugcrowd"]),
        "Reopened": str(findings.reopened_count),
        "ReopenedColor": report_metrics.status_color(findings.reopened_count),
        "NewVulns": str(findings.new_count),
        "NewVulnsColor": report_metrics.status_color(findings.new_count),
        "TotVulns": str(findings.active_count),
        "TotVulnsColor": report_metrics.status_color(findings.active_count),
        "maxurg": critical_age,
        "UrgColor": report_metrics.status_color(critical_age),
        "maxctl": urgent_age,
        "CtlColor": report_metrics.status_color(urgent_age),
        "lev1": severity_totals[0],
        "lev2": severity_totals[1],
        "lev3": severity_totals[2],
        "lev4": severity_totals[3],
        "lev5": severity_totals[4],
        "PdfFile": _detail_pdf_block(
            artifacts.detail_pdf,
            web_application_count,
        ),
    }
    template_data.update(_artifact_fields(artifacts))
    validate_template_data(template_data)
    return template_data
