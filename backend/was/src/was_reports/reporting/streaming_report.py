"""Process large Qualys WAS report XML with bounded memory use."""

# Standard Python Libraries
import base64
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Dict, IO, Iterator, Tuple

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient
from was_reports.reporting.report_artifacts import (
    EMAILS_FOUND_QID,
    LINKS_CRAWLED_QID,
    REJECTED_LINKS_QID,
    ReportArtifactResult,
    write_sensitive_data_attachment,
)
from was_reports.reporting.report_metrics import (
    GROUP_LABELS,
    OWASP_LABELS,
    FindingMetrics,
    SummaryMetrics,
    increment_monthly_counts,
    initialize_monthly_counts,
    risk_color,
    status_color,
)
from was_reports.reporting.report_transformer import (
    INFORMATION_HEADER,
    VULNERABILITY_HEADER,
    InformationFinding,
    QidDefinition,
    TransformationResult,
    VulnerabilityFinding,
    clean_glossary_text,
    csv_row,
    finding_age_days,
    information_csv_row,
    parse_potential,
    vulnerability_csv_row,
)

SeverityTotals = Tuple[str, str, str, str, str]


@dataclass(frozen=True)
class StreamingReportResult:
    """All XML-derived values and artifacts required to render one report."""

    transformation: TransformationResult
    finding_metrics: FindingMetrics
    summary_metrics: SummaryMetrics
    severity_totals: SeverityTotals
    artifacts: ReportArtifactResult


class _LineWriter:
    """Write lines incrementally while optionally omitting the final newline."""

    def __init__(self, output_file: IO[str], trailing_newline: bool) -> None:
        """Store the output stream and requested legacy newline behavior."""
        self.output_file = output_file
        self.trailing_newline = trailing_newline
        self.has_lines = False

    def write(self, line: str) -> None:
        """Append one line without retaining previous report rows in memory."""
        if self.trailing_newline:
            self.output_file.write("{}\n".format(line))
        else:
            if self.has_lines:
                self.output_file.write("\n")
            self.output_file.write(line)
        self.has_lines = True


def _local_name(element) -> str:
    """Return an element's local tag name for namespaced or plain XML."""
    return etree.QName(element).localname


def _parent_name(element) -> str:
    """Return the local name of an element's parent when present."""
    parent = element.getparent()
    return _local_name(parent) if parent is not None else ""


def _child(element, name: str):
    """Return the first direct child with the requested local name."""
    for child in element:
        if isinstance(child.tag, str) and _local_name(child) == name:
            return child
    return None


def _text(element, name: str, default: str = "None") -> str:
    """Return direct child text using the legacy compatibility default."""
    child = _child(element, name)
    if child is None:
        return default
    return "".join(child.itertext())


def _required_text(element, name: str) -> str:
    """Return required direct child text or raise a clear parsing error."""
    child = _child(element, name)
    if child is None:
        raise AttributeError("Qualys report element is missing {}.".format(name))
    return "".join(child.itertext())


def _clear_element(element) -> None:
    """Release a processed subtree and preceding siblings from the parser."""
    element.clear()
    parent = element.getparent()
    if parent is not None:
        while element.getprevious() is not None:
            del parent[0]


def _iter_report(source: BinaryIO) -> Iterator[Tuple[str, object]]:
    """Yield secure streaming parse events for one report file."""
    parser = etree.iterparse(
        source,
        events=("start", "end"),
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        attribute_defaults=False,
        huge_tree=True,
    )
    root_checked = False
    for event, element in parser:
        if not root_checked and event == "start":
            root_checked = True
            if _local_name(element) != "WAS_WEBAPP_REPORT":
                raise ValueError(
                    "Qualys report XML has an unexpected root element."
                )
        yield event, element


def _qid_definition(element) -> Tuple[str, QidDefinition, str, str]:
    """Return glossary fields used by CSVs, charts, and classifications."""
    qid = _required_text(element, "QID")
    return (
        qid,
        QidDefinition(
            severity=_required_text(element, "SEVERITY"),
            title=_required_text(element, "TITLE"),
            group=_text(element, "GROUP", ""),
            description=clean_glossary_text(_required_text(element, "DESCRIPTION")),
            impact=clean_glossary_text(_required_text(element, "IMPACT")),
            solution=clean_glossary_text(_required_text(element, "SOLUTION")),
            cvss=_text(element, "CVSS_BASE"),
            cve=_text(element, "CVE"),
            cwe=_text(element, "CWE"),
        ),
        _text(element, "GROUP", ""),
        _text(element, "OWASP", "None"),
    )


def _summary_metrics(element) -> SummaryMetrics:
    """Return global report summary values with legacy colors."""
    security_risk = _required_text(element, "SECURITY_RISK")
    sensitive_count = _required_text(element, "SENSITIVE_CONTENT")
    return SummaryMetrics(
        start_date="",
        security_risk=security_risk,
        total_information_findings=_required_text(element, "INFORMATION_GATHERED"),
        web_application_count=_required_text(element, "WEB_APPLICATIONS"),
        sensitive_content_count=sensitive_count,
        risk_color=risk_color(security_risk),
        sensitive_color=status_color(sensitive_count),
    )


def _severity_row(element) -> Tuple[str, list[int]]:
    """Return one application name and its five summary severity counts."""
    counts = [int(_required_text(element, "LEVEL{}".format(level))) for level in range(1, 6)]
    return _required_text(element, "WEB_APPLICATION"), counts


def _write_overview_row(element, writer: _LineWriter) -> None:
    """Write one appendix application without retaining the appendix tree."""
    writer.write(
        csv_row(
            [
                _required_text(element, "NAME"),
                _required_text(element, "URL"),
                _required_text(element, "SCOPE"),
                _text(element, "OPERATING_SYSTEM", "N/A"),
            ]
        )
    )


def _parse_vulnerability(element) -> VulnerabilityFinding:
    """Parse one streamed vulnerability using legacy field semantics."""
    payloads = _child(element, "PAYLOADS")
    request = None
    response_contents = None
    if payloads is not None:
        payload = _child(payloads, "PAYLOAD")
        if payload is not None:
            request = _child(payload, "REQUEST")
            response = _child(payload, "RESPONSE")
            if response is not None:
                response_contents = _child(response, "CONTENTS")

    request_text = "n/a"
    if request is not None:
        header_lines = []
        headers = _child(request, "HEADERS")
        if headers is not None:
            for header in headers:
                if isinstance(header.tag, str) and _local_name(header) == "HEADER":
                    header_lines.append(
                        "{}: {}\n".format(
                            _text(header, "key", ""),
                            _text(header, "value", ""),
                        )
                    )
        request_text = "{} {}\n{}\n{}".format(
            _text(request, "METHOD", ""),
            _text(request, "URL", ""),
            "".join(header_lines),
            _text(request, "BODY", ""),
        )

    return VulnerabilityFinding(
        finding_id=_required_text(element, "ID"),
        qid=_required_text(element, "QID"),
        url=_required_text(element, "URL"),
        first_detected=_required_text(element, "FIRST_TIME_DETECTED"),
        last_detected=_required_text(element, "LAST_TIME_DETECTED"),
        potential=parse_potential(_required_text(element, "POTENTIAL")),
        status=_required_text(element, "STATUS"),
        payload_request=request_text,
        payload_response=(
            "".join(response_contents.itertext())
            if response_contents is not None
            else "Ti9B"
        ),
    )


def _parse_information(element) -> InformationFinding:
    """Parse one streamed information-gathered record."""
    return InformationFinding(
        finding_id=_required_text(element, "ID"),
        qid=_required_text(element, "QID"),
        last_detected=_required_text(element, "LAST_TIME_DETECTED"),
    )


def _web_application_name(element) -> str:
    """Return the containing result web application's name."""
    parent = element.getparent()
    while parent is not None and _local_name(parent) != "WEB_APPLICATION":
        parent = parent.getparent()
    if parent is None:
        raise LookupError("Qualys finding is not within a web application.")
    return _required_text(parent, "NAME")


def _decoded_data_values(element) -> list[str]:
    """Decode all lines from an information-gathered DATA value."""
    data = _child(element, "DATA")
    if data is None:
        return []
    decoded = base64.b64decode("".join(data.itertext()))
    return [line.decode("utf-8") for line in decoded.splitlines()]


def _open_writer(
    stack: ExitStack,
    path: Path,
    trailing_newline: bool,
) -> _LineWriter:
    """Open one UTF-8 artifact and register it for deterministic closure."""
    output_file = stack.enter_context(path.open("w", encoding="utf-8", newline=""))
    return _LineWriter(output_file, trailing_newline)


def process_report_xml(
    xml_path: Path,
    stakeholder_tag: str,
    asset_directory: Path,
    client: QualysClient,
    current_time: datetime,
) -> StreamingReportResult:
    """Process one Qualys report in two bounded-memory streaming passes."""
    asset_directory.mkdir(parents=True, exist_ok=True)
    filenames = {
        "vulnerability": "vulnerability-list-{}.csv".format(stakeholder_tag),
        "information": "information-gathered-list{}.csv".format(stakeholder_tag),
        "severity": "vulns-by-webapp-{}.csv".format(stakeholder_tag),
        "overview": "webapp-overview-{}.csv".format(stakeholder_tag),
        "links": "links-crawled-{}.csv".format(stakeholder_tag),
        "emails": "emails-found-{}.csv".format(stakeholder_tag),
        "rejected": "rejected-links-{}.csv".format(stakeholder_tag),
    }
    qid_definitions: Dict[str, QidDefinition] = {}
    qid_groups: Dict[str, str] = {}
    qid_owasp: Dict[str, str] = {}
    summary = None
    generation_datetime = None
    severity_totals = [0, 0, 0, 0, 0]

    with ExitStack() as stack:
        severity_writer = _open_writer(
            stack, asset_directory / filenames["severity"], False
        )
        severity_writer.write("WEBAPP,LEVEL 1,LEVEL 2,LEVEL 3,LEVEL 4,LEVEL 5,TOTAL")
        overview_writer = _open_writer(
            stack, asset_directory / filenames["overview"], False
        )
        overview_writer.write("WEBAPP,URL,SCOPE,DETECTED OS")

        with xml_path.open("rb") as xml_file:
            for event, element in _iter_report(xml_file):
                if event != "end" or not isinstance(element.tag, str):
                    continue
                name = _local_name(element)
                parent_name = _parent_name(element)
                if name == "GENERATION_DATETIME" and parent_name == "HEADER":
                    generation_datetime = "".join(element.itertext())
                elif name == "GLOBAL_SUMMARY":
                    summary = _summary_metrics(element)
                    _clear_element(element)
                elif name == "SUMMARY_STAT":
                    web_application, counts = _severity_row(element)
                    for index, count in enumerate(counts):
                        severity_totals[index] += count
                    severity_writer.write(
                        csv_row([web_application] + counts + [sum(counts)])
                    )
                    _clear_element(element)
                elif name == "QID" and parent_name == "QID_LIST":
                    qid, definition, group, owasp = _qid_definition(element)
                    qid_definitions[qid] = definition
                    qid_groups[qid] = group
                    qid_owasp[qid] = owasp
                    _clear_element(element)
                elif name == "WEB_APPLICATION" and parent_name == "APPENDIX":
                    _write_overview_row(element, overview_writer)
                    _clear_element(element)
                elif name == "VULNERABILITY" and parent_name == "VULNERABILITY_LIST":
                    _clear_element(element)
                elif (
                    name == "INFORMATION_GATHERED"
                    and parent_name == "INFORMATION_GATHERED_LIST"
                ):
                    _clear_element(element)
                elif name == "WEB_APPLICATION" and parent_name == "RESULTS":
                    _clear_element(element)

    if not qid_definitions:
        raise LookupError("Qualys report does not contain a QID glossary.")
    if summary is None or generation_datetime is None:
        raise LookupError("Qualys report does not contain the required summary.")
    summary = SummaryMetrics(
        start_date=generation_datetime[:11],
        security_risk=summary.security_risk,
        total_information_findings=summary.total_information_findings,
        web_application_count=summary.web_application_count,
        sensitive_content_count=summary.sensitive_content_count,
        risk_color=summary.risk_color,
        sensitive_color=summary.sensitive_color,
    )

    severities = []
    ages = []
    fixed_monthly = initialize_monthly_counts(current_time)
    vulnerabilities_monthly = initialize_monthly_counts(current_time)
    qid_counts: Counter = Counter()
    fixed_count = 0
    new_count = 0
    reopened_count = 0
    active_count = 0
    nonfixed_count = 0

    with ExitStack() as stack:
        vulnerability_writer = _open_writer(
            stack, asset_directory / filenames["vulnerability"], True
        )
        vulnerability_writer.write(VULNERABILITY_HEADER)
        information_writer = _open_writer(
            stack, asset_directory / filenames["information"], True
        )
        information_writer.write(INFORMATION_HEADER)
        links_writer = _open_writer(
            stack, asset_directory / filenames["links"], False
        )
        emails_writer = _open_writer(
            stack, asset_directory / filenames["emails"], False
        )
        rejected_writer = _open_writer(
            stack, asset_directory / filenames["rejected"], False
        )
        attachment_writers = {
            LINKS_CRAWLED_QID: (links_writer, "Links for web application"),
            EMAILS_FOUND_QID: (emails_writer, "Emails found for web application"),
            REJECTED_LINKS_QID: (
                rejected_writer,
                "Rejected Links found for web application",
            ),
        }

        with xml_path.open("rb") as xml_file:
            for event, element in _iter_report(xml_file):
                if event != "end" or not isinstance(element.tag, str):
                    continue
                name = _local_name(element)
                parent_name = _parent_name(element)
                if name == "NAME" and parent_name == "WEB_APPLICATION":
                    web_application_element = element.getparent()
                    container = web_application_element.getparent()
                    if container is not None and _local_name(container) == "RESULTS":
                        web_application = "".join(element.itertext())
                        for attachment_writer, heading in attachment_writers.values():
                            attachment_writer.write("")
                            attachment_writer.write(
                                csv_row(
                                    ["{} {}:".format(heading, web_application)]
                                )
                            )
                elif name == "VULNERABILITY" and parent_name == "VULNERABILITY_LIST":
                    finding = _parse_vulnerability(element)
                    if finding.status == "FIXED":
                        fixed_count += 1
                        increment_monthly_counts(
                            fixed_monthly, finding.last_detected, current_time
                        )
                    else:
                        definition = qid_definitions[finding.qid]
                        web_application = _web_application_name(element)
                        nonfixed_count += 1
                        if finding.status == "NEW":
                            new_count += 1
                        if finding.status == "REOPENED":
                            reopened_count += 1
                        if finding.status == "ACTIVE":
                            active_count += 1
                        increment_monthly_counts(
                            vulnerabilities_monthly,
                            finding.first_detected,
                            current_time,
                        )
                        qid_counts[finding.qid] += 1
                        severities.append(definition.severity)
                        ages.append(
                            finding_age_days(finding.first_detected, current_time)
                        )
                        vulnerability_writer.write(
                            vulnerability_csv_row(
                                finding, web_application, definition
                            )
                        )
                    _clear_element(element)
                elif (
                    name == "INFORMATION_GATHERED"
                    and parent_name == "INFORMATION_GATHERED_LIST"
                ):
                    qid = _required_text(element, "QID")
                    web_application = _web_application_name(element)
                    information = _parse_information(element)
                    information_writer.write(
                        information_csv_row(
                            information,
                            web_application,
                            qid_definitions[information.qid],
                        )
                    )
                    attachment = attachment_writers.get(qid)
                    if attachment is not None:
                        attachment_writer, unused_heading = attachment
                        for value in _decoded_data_values(element):
                            attachment_writer.write(csv_row([value]))
                    _clear_element(element)
                elif name == "WEB_APPLICATION" and parent_name == "RESULTS":
                    _clear_element(element)
                elif name == "SUMMARY_STAT":
                    _clear_element(element)
                elif name == "GLOBAL_SUMMARY":
                    _clear_element(element)
                elif name == "QID" and parent_name == "QID_LIST":
                    _clear_element(element)
                elif name == "WEB_APPLICATION" and parent_name == "APPENDIX":
                    _clear_element(element)

    group_counts = {label: 0 for label in GROUP_LABELS.values()}
    owasp_counts = {label: 0 for label in OWASP_LABELS.values()}
    for qid, count in qid_counts.items():
        group_label = GROUP_LABELS.get(qid_groups.get(qid, ""))
        if group_label:
            group_counts[group_label] += count
        owasp_label = OWASP_LABELS.get(qid_owasp.get(qid, "None"))
        if owasp_label:
            owasp_counts[owasp_label] += count

    sensitive_filename = write_sensitive_data_attachment(
        client, stakeholder_tag, asset_directory
    )
    return StreamingReportResult(
        transformation=TransformationResult(
            vulnerability_filename=filenames["vulnerability"],
            information_filename=filenames["information"],
            severities=severities,
            ages=ages,
        ),
        finding_metrics=FindingMetrics(
            group_counts=group_counts,
            owasp_counts=owasp_counts,
            fixed_monthly=fixed_monthly,
            vulnerabilities_monthly=vulnerabilities_monthly,
            fixed_count=fixed_count,
            total_count=nonfixed_count + fixed_count,
            new_count=new_count,
            reopened_count=reopened_count,
            active_count=active_count,
        ),
        summary_metrics=summary,
        severity_totals=tuple(str(total) for total in severity_totals),
        artifacts=ReportArtifactResult(
            vulnerabilities_by_webapp=filenames["severity"],
            application_overview=filenames["overview"],
            links_crawled=filenames["links"],
            emails_found=filenames["emails"],
            rejected_links=filenames["rejected"],
            sensitive_data=sensitive_filename,
        ),
    )
