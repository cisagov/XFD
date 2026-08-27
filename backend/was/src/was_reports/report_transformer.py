"""Transform Qualys WAS report XML into legacy-compatible CSV artifacts."""

# Standard Python Libraries
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Union

# Third-Party Libraries
from lxml import objectify

VULNERABILITY_HEADER = (
    "VULN_ID,NAME,QID,SEVERITY,BASE CVSS,CWE,CVE,FIRST DETECTION,"
    "LAST DETECTION,GROUP,WEB APPLICATION,URL,PAYLOAD REQUEST,"
    "PAYLOAD RESPONSE,DESCRIPTION,IMPACT,SOLUTION,VULN TYPE"
)
INFORMATION_HEADER = (
    "INFO_ID,NAME,QID,URL,LAST DETECTION,SEVERITY,DESCRIPTION,IMPACT,SOLUTION"
)
QUALYS_DATETIME_FORMAT = "%d %b %Y %I:%M%p %Z"


class _TextExtractor(HTMLParser):
    """Collect text content while ignoring HTML markup."""

    def __init__(self) -> None:
        """Initialize extracted text storage."""
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        """Collect text found between HTML tags."""
        self.parts.append(data)


@dataclass(frozen=True)
class QidDefinition:
    """Qualys glossary metadata for one QID."""

    severity: str
    title: str
    group: str
    description: str
    impact: str
    solution: str
    cvss: str
    cve: str
    cwe: str


@dataclass(frozen=True)
class VulnerabilityFinding:
    """Qualys vulnerability values used by the legacy CSV artifact."""

    finding_id: str
    qid: str
    url: str
    first_detected: str
    last_detected: str
    potential: bool
    status: str
    payload_request: str
    payload_response: str


@dataclass(frozen=True)
class InformationFinding:
    """Qualys information-gathered values used by the legacy CSV artifact."""

    finding_id: str
    qid: str
    last_detected: str


@dataclass(frozen=True)
class TransformationResult:
    """Generated CSV filenames and graph input values."""

    vulnerability_filename: str
    information_filename: str
    severities: List[str]
    ages: List[int]


def remove_html_tags(value: str) -> str:
    """Return text content with HTML markup removed."""
    extractor = _TextExtractor()
    extractor.feed(value)
    extractor.close()
    return "".join(extractor.parts)


def remove_commas(value: object) -> str:
    """Remove commas to preserve the legacy unquoted CSV field behavior."""
    return str(value).replace(",", "")


def quote_field(value: object) -> str:
    """Quote a field when it contains CSV delimiters or quote characters."""
    field = str(value)
    if "," in field or '"' in field:
        return '"{}"'.format(field.replace('"', '""'))
    return field


def optional_text(element, child_name: str, default: str = "None") -> str:
    """Return child text or a compatibility default when it is absent."""
    children = element.xpath("./{}".format(child_name))
    if not children:
        return default
    return str(children[0])


def format_payload_request(request) -> str:
    """Format a Qualys payload request as legacy multiline text."""
    method = optional_text(request, "METHOD", "")
    url = optional_text(request, "URL", "")
    header_lines = []
    for header in request.xpath("./HEADERS/HEADER"):
        header_lines.append(
            "{}: {}\n".format(
                optional_text(header, "key", ""),
                optional_text(header, "value", ""),
            )
        )
    body = optional_text(request, "BODY", "")
    return "{} {}\n{}\n{}".format(method, url, "".join(header_lines), body)


def parse_potential(value: str) -> bool:
    """Return whether Qualys marks a finding as potential."""
    return value.strip().lower() in ("1", "true", "yes")


def parse_vulnerability_finding(element) -> VulnerabilityFinding:
    """Parse one Qualys vulnerability element."""
    request_elements = element.xpath("./PAYLOADS/PAYLOAD/REQUEST")
    response_elements = element.xpath("./PAYLOADS/PAYLOAD/RESPONSE/CONTENTS")
    payload_request = (
        format_payload_request(request_elements[0]) if request_elements else "n/a"
    )
    payload_response = str(response_elements[0]) if response_elements else "Ti9B"
    return VulnerabilityFinding(
        finding_id=str(element.ID),
        qid=str(element.QID),
        url=str(element.URL),
        first_detected=str(element.FIRST_TIME_DETECTED),
        last_detected=str(element.LAST_TIME_DETECTED),
        potential=parse_potential(str(element.POTENTIAL)),
        status=str(element.STATUS),
        payload_request=payload_request,
        payload_response=payload_response,
    )


def parse_information_finding(element) -> InformationFinding:
    """Parse one Qualys information-gathered element."""
    return InformationFinding(
        finding_id=str(element.ID),
        qid=str(element.QID),
        last_detected=str(element.LAST_TIME_DETECTED),
    )


def clean_glossary_text(value: object) -> str:
    """Remove HTML and newline characters from glossary text."""
    return remove_html_tags(str(value)).replace("\n", "")


def parse_qid_definitions(report) -> Dict[str, QidDefinition]:
    """Return QID glossary definitions keyed by QID string."""
    qid_elements = report.xpath("./GLOSSARY/QID_LIST/QID")
    if not qid_elements:
        raise LookupError("Qualys report does not contain a QID glossary.")

    definitions: Dict[str, QidDefinition] = {}
    for entry in qid_elements:
        qid = str(entry.QID)
        definitions[qid] = QidDefinition(
            severity=str(entry.SEVERITY),
            title=str(entry.TITLE),
            group=optional_text(entry, "GROUP", ""),
            description=clean_glossary_text(entry.DESCRIPTION),
            impact=clean_glossary_text(entry.IMPACT),
            solution=clean_glossary_text(entry.SOLUTION),
            cvss=optional_text(entry, "CVSS_BASE"),
            cve=optional_text(entry, "CVE"),
            cwe=optional_text(entry, "CWE"),
        )
    return definitions


def finding_age_days(first_detected: str, current_time: datetime) -> int:
    """Return whole UTC days since a Qualys finding was first detected."""
    detected_time = datetime.strptime(first_detected, QUALYS_DATETIME_FORMAT)
    detected_time = detected_time.replace(tzinfo=timezone.utc)
    resolved_current_time = current_time
    if resolved_current_time.tzinfo is None:
        resolved_current_time = resolved_current_time.replace(tzinfo=timezone.utc)
    return (resolved_current_time.astimezone(timezone.utc) - detected_time).days


def decode_payload_response(encoded_response: str) -> str:
    """Decode a Qualys payload response using legacy byte-string formatting."""
    return remove_commas(str(base64.b64decode(encoded_response)))


def information_csv_row(
    finding: InformationFinding,
    web_application_name: str,
    qid_definition: QidDefinition,
) -> str:
    """Return one legacy-compatible information-gathered CSV row."""
    return "{},{},{},{},{},{},{},{},{}".format(
        finding.finding_id,
        remove_commas(qid_definition.title),
        finding.qid,
        remove_commas(web_application_name),
        finding.last_detected,
        qid_definition.severity,
        remove_commas(qid_definition.description),
        remove_commas(qid_definition.impact),
        remove_commas(qid_definition.solution),
    )


def vulnerability_csv_row(
    finding: VulnerabilityFinding,
    web_application_name: str,
    qid_definition: QidDefinition,
) -> str:
    """Return one legacy-compatible vulnerability CSV row."""
    vulnerability_type = "Potential" if finding.potential else "Confirmed"
    return "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
        finding.finding_id,
        remove_commas(qid_definition.title),
        finding.qid,
        qid_definition.severity,
        qid_definition.cvss,
        remove_commas(qid_definition.cwe),
        remove_commas(qid_definition.cve),
        finding.first_detected,
        finding.last_detected,
        qid_definition.group,
        web_application_name,
        remove_commas(finding.url),
        quote_field(finding.payload_request),
        decode_payload_response(finding.payload_response),
        remove_commas(qid_definition.description),
        remove_commas(qid_definition.impact),
        remove_commas(qid_definition.solution),
        vulnerability_type,
    )


def parse_report(report_xml: Union[str, bytes, object]):
    """Return a Qualys report XML root from text, bytes, or an XML element."""
    if isinstance(report_xml, str):
        return objectify.fromstring(report_xml.encode("utf-8"))
    if isinstance(report_xml, bytes):
        return objectify.fromstring(report_xml)
    return report_xml


def transform_report_to_csv(
    report_xml: Union[str, bytes, object],
    stakeholder_tag: str,
    asset_directory: Path,
    current_time: Optional[datetime] = None,
) -> TransformationResult:
    """Create legacy WAS CSV artifacts and return chart input lists."""
    report = parse_report(report_xml)
    qid_definitions = parse_qid_definitions(report)
    resolved_current_time = current_time or datetime.now(timezone.utc)
    vulnerability_filename = "vulnerability-list-{}.csv".format(stakeholder_tag)
    information_filename = "information-gathered-list{}.csv".format(
        stakeholder_tag
    )
    vulnerability_lines = [VULNERABILITY_HEADER]
    information_lines = [INFORMATION_HEADER]
    severities: List[str] = []
    ages: List[int] = []

    for web_application in report.xpath("./RESULTS/WEB_APPLICATION"):
        web_application_name = str(web_application.NAME)
        for information_element in web_application.xpath(
            "./INFORMATION_GATHERED_LIST/*"
        ):
            information_finding = parse_information_finding(information_element)
            information_lines.append(
                information_csv_row(
                    finding=information_finding,
                    web_application_name=web_application_name,
                    qid_definition=qid_definitions[information_finding.qid],
                )
            )

        for vulnerability_element in web_application.xpath("./VULNERABILITY_LIST/*"):
            vulnerability_finding = parse_vulnerability_finding(
                vulnerability_element
            )
            if vulnerability_finding.status == "FIXED":
                continue
            qid_definition = qid_definitions[vulnerability_finding.qid]
            severities.append(qid_definition.severity)
            ages.append(
                finding_age_days(
                    vulnerability_finding.first_detected,
                    resolved_current_time,
                )
            )
            vulnerability_lines.append(
                vulnerability_csv_row(
                    finding=vulnerability_finding,
                    web_application_name=web_application_name,
                    qid_definition=qid_definition,
                )
            )

    asset_directory.mkdir(parents=True, exist_ok=True)
    (asset_directory / vulnerability_filename).write_text(
        "{}\n".format("\n".join(vulnerability_lines)),
        encoding="utf-8",
    )
    (asset_directory / information_filename).write_text(
        "{}\n".format("\n".join(information_lines)),
        encoding="utf-8",
    )
    return TransformationResult(
        vulnerability_filename=vulnerability_filename,
        information_filename=information_filename,
        severities=severities,
        ages=ages,
    )
