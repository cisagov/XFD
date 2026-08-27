"""Calculate legacy WAS summary and chart metrics from Qualys report XML."""

# Standard Python Libraries
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Tuple, Union

# Third-Party Libraries
from dateutil.relativedelta import relativedelta

# First-Party Libraries
from was_reports.report_transformer import QUALYS_DATETIME_FORMAT, parse_report

GROUP_LABELS = {
    "PATH": "Path Disclosure",
    "INFO": "Information Disclosure",
    "XSS": "Cross-Site Scripting",
    "BURP": "Burp",
    "SQL": "SQL Injection",
    "BUGCROWD": "Bugcrowd",
}
OWASP_LABELS = {
    "A1": "Broken Access Control",
    "A2": "Cryptographic Failures",
    "A3": "Injection",
    "A4": "Insecure Design",
    "A5": "Security Misconfiguration",
    "A6": "Vulnerable and Outdated Components",
    "A7": "Identification and Authentication Failures",
    "A8": "Software and Data Integrity Failures",
    "A9": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery (SSRF)",
}


@dataclass(frozen=True)
class SummaryMetrics:
    """Qualys global summary values consumed by the report template."""

    start_date: str
    security_risk: str
    total_information_findings: str
    web_application_count: str
    sensitive_content_count: str
    risk_color: str
    sensitive_color: str


@dataclass(frozen=True)
class FindingMetrics:
    """Finding counts and trends consumed by WAS charts and template fields."""

    group_counts: Dict[str, int]
    owasp_counts: Dict[str, int]
    fixed_monthly: Dict[str, int]
    vulnerabilities_monthly: Dict[str, int]
    fixed_count: int
    total_count: int
    new_count: int
    reopened_count: int
    active_count: int


def risk_color(security_risk: str) -> str:
    """Return the legacy report color for a Qualys security-risk label."""
    colors = {
        "High": "CB0000",
        "Medium": "FFC702",
        "Low": "32CB00",
    }
    return colors.get(security_risk, "")


def status_color(value: Union[str, int]) -> str:
    """Return green for zero and red for a nonzero report value."""
    return "5e9732" if str(value) == "0" else "c41230"


def calculate_summary_metrics(report_xml) -> SummaryMetrics:
    """Return global summary values from a Qualys WAS report."""
    report = parse_report(report_xml)
    generation_datetime = str(report.HEADER.GENERATION_DATETIME)
    security_risk = str(report.SUMMARY.GLOBAL_SUMMARY.SECURITY_RISK)
    sensitive_content_count = str(
        report.SUMMARY.GLOBAL_SUMMARY.SENSITIVE_CONTENT
    )
    return SummaryMetrics(
        start_date=generation_datetime[:11],
        security_risk=security_risk,
        total_information_findings=str(
            report.SUMMARY.GLOBAL_SUMMARY.INFORMATION_GATHERED
        ),
        web_application_count=str(
            report.SUMMARY.GLOBAL_SUMMARY.WEB_APPLICATIONS
        ),
        sensitive_content_count=sensitive_content_count,
        risk_color=risk_color(security_risk),
        sensitive_color=status_color(sensitive_content_count),
    )


def calculate_severity_totals(report_xml) -> Tuple[str, str, str, str, str]:
    """Sum Qualys summary-stat levels using the legacy severity ordering."""
    report = parse_report(report_xml)
    totals = [0, 0, 0, 0, 0]
    for summary_stat in report.xpath("./SUMMARY/SUMMARY_STATS/SUMMARY_STAT"):
        for severity_index in range(5):
            level_name = "LEVEL{}".format(severity_index + 1)
            totals[severity_index] += int(
                summary_stat.xpath("./{}".format(level_name))[0]
            )
    return tuple(str(total) for total in totals)


def initialize_monthly_counts(current_time: datetime) -> Dict[str, int]:
    """Create the legacy 12-month dictionary from newest to oldest month."""
    monthly_counts: Dict[str, int] = {}
    for month_offset in range(12):
        key_date = current_time - relativedelta(months=month_offset)
        monthly_counts[key_date.strftime("%B %Y")] = 0
    return monthly_counts


def increment_monthly_counts(
    monthly_counts: Dict[str, int],
    finding_datetime: str,
    current_time: datetime,
) -> None:
    """Apply the legacy cumulative month comparison to one finding date."""
    parsed_datetime = datetime.strptime(finding_datetime, QUALYS_DATETIME_FORMAT)
    parsed_datetime = parsed_datetime.replace(tzinfo=timezone.utc)
    resolved_current_time = current_time
    if resolved_current_time.tzinfo is None:
        resolved_current_time = resolved_current_time.replace(tzinfo=timezone.utc)
    for month_offset in range(12):
        key_date = resolved_current_time - relativedelta(months=month_offset)
        if parsed_datetime <= key_date:
            monthly_counts[key_date.strftime("%B %Y")] += 1


def qid_classifications(report) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return QID-to-group and QID-to-OWASP mappings."""
    groups: Dict[str, str] = {}
    owasp_categories: Dict[str, str] = {}
    for qid_element in report.xpath("./GLOSSARY/QID_LIST/QID"):
        qid = str(qid_element.QID)
        group_elements = qid_element.xpath("./GROUP")
        owasp_elements = qid_element.xpath("./OWASP")
        groups[qid] = str(group_elements[0]) if group_elements else ""
        owasp_categories[qid] = (
            str(owasp_elements[0]) if owasp_elements else "None"
        )
    return groups, owasp_categories


def calculate_finding_metrics(
    report_xml,
    current_time: datetime,
) -> FindingMetrics:
    """Calculate status, category, and monthly finding metrics."""
    report = parse_report(report_xml)
    fixed_monthly = initialize_monthly_counts(current_time)
    vulnerabilities_monthly = initialize_monthly_counts(current_time)
    qid_counts: Counter = Counter()
    fixed_count = 0
    new_count = 0
    reopened_count = 0
    active_count = 0
    nonfixed_count = 0

    for vulnerability in report.xpath(
        "./RESULTS/WEB_APPLICATION/VULNERABILITY_LIST/VULNERABILITY"
    ):
        status = str(vulnerability.STATUS)
        if status == "FIXED":
            fixed_count += 1
            increment_monthly_counts(
                fixed_monthly,
                str(vulnerability.LAST_TIME_DETECTED),
                current_time,
            )
            continue

        nonfixed_count += 1
        if status == "NEW":
            new_count += 1
        if status == "REOPENED":
            reopened_count += 1
        if status == "ACTIVE":
            active_count += 1
        increment_monthly_counts(
            vulnerabilities_monthly,
            str(vulnerability.FIRST_TIME_DETECTED),
            current_time,
        )
        qid_counts[str(vulnerability.QID)] += 1

    qid_groups, qid_owasp = qid_classifications(report)
    group_counts = {label: 0 for label in GROUP_LABELS.values()}
    owasp_counts = {label: 0 for label in OWASP_LABELS.values()}
    for qid, count in qid_counts.items():
        group_label = GROUP_LABELS.get(qid_groups.get(qid, ""))
        if group_label:
            group_counts[group_label] += count
        owasp_label = OWASP_LABELS.get(qid_owasp.get(qid, "None"))
        if owasp_label:
            owasp_counts[owasp_label] += count

    return FindingMetrics(
        group_counts=group_counts,
        owasp_counts=owasp_counts,
        fixed_monthly=fixed_monthly,
        vulnerabilities_monthly=vulnerabilities_monthly,
        fixed_count=fixed_count,
        total_count=nonfixed_count + fixed_count,
        new_count=new_count,
        reopened_count=reopened_count,
        active_count=active_count,
    )


def fixed_percentage(fixed_count: int, total_count: int) -> int:
    """Return the truncated fixed percentage used by the legacy donut chart."""
    if total_count == 0:
        return 0
    return int(fixed_count / total_count * 100)
