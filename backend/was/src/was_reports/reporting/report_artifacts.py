"""Create legacy-compatible WAS report attachment artifacts."""

# Standard Python Libraries
import base64
import csv
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import List, Sequence, Tuple, Union

# Third-Party Libraries
from lxml import etree, objectify
from lxml.builder import E

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, QualysRequest
from was_reports.reporting.report_transformer import parse_report

LINKS_CRAWLED_QID = "150009"
EMAILS_FOUND_QID = "150054"
REJECTED_LINKS_QID = "150041"
SSN_QIDS = ("150034", "150603")
CREDIT_CARD_QIDS = ("150033", "150080")
SENSITIVE_FINDING_ENDPOINT = "/search/was/finding"


@dataclass(frozen=True)
class ReportArtifactResult:
    """Filenames for report attachments produced from Qualys data."""

    vulnerabilities_by_webapp: str
    application_overview: str
    links_crawled: str
    emails_found: str
    rejected_links: str
    sensitive_data: str


def _write_lines(path: Path, lines: Sequence[str]) -> None:
    """Write text lines using the newline behavior of the legacy artifacts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_vulnerabilities_by_webapp(
    report_xml: Union[str, bytes, object],
    stakeholder_tag: str,
    asset_directory: Path,
) -> str:
    """Write vulnerability severity totals for every web application."""
    report = parse_report(report_xml)
    filename = "vulns-by-webapp-{}.csv".format(stakeholder_tag)
    lines = ["WEBAPP,LEVEL 1,LEVEL 2,LEVEL 3,LEVEL 4,LEVEL 5,TOTAL"]
    for summary in report.xpath("./SUMMARY/SUMMARY_STATS/SUMMARY_STAT"):
        severity_counts = [
            int(str(summary["LEVEL{}".format(level)]))
            for level in range(1, 6)
        ]
        lines.append(
            "{},{},{},{},{},{},{}".format(
                str(summary.WEB_APPLICATION),
                severity_counts[0],
                severity_counts[1],
                severity_counts[2],
                severity_counts[3],
                severity_counts[4],
                sum(severity_counts),
            )
        )
    _write_lines(asset_directory / filename, lines)
    return filename


def write_application_overview(
    report_xml: Union[str, bytes, object],
    stakeholder_tag: str,
    asset_directory: Path,
) -> str:
    """Write the legacy web application overview attachment."""
    report = parse_report(report_xml)
    filename = "webapp-overview-{}.csv".format(stakeholder_tag)
    lines = ["WEBAPP,URL,SCOPE,DETECTED OS"]
    for web_application in report.xpath("./APPENDIX/WEB_APPLICATION"):
        operating_systems = web_application.xpath("./OPERATING_SYSTEM")
        operating_system = (
            str(operating_systems[0]) if operating_systems else "N/A"
        )
        lines.append(
            "{},{},{},{}".format(
                str(web_application.NAME),
                str(web_application.URL),
                str(web_application.SCOPE),
                operating_system,
            )
        )
    _write_lines(asset_directory / filename, lines)
    return filename


def _decoded_information_values(web_application, qid: str) -> List[str]:
    """Return decoded data values for one information-gathered QID."""
    values: List[str] = []
    for information in web_application.xpath(
        "./INFORMATION_GATHERED_LIST/INFORMATION_GATHERED"
    ):
        if str(information.QID) != qid:
            continue
        encoded_values = information.xpath("./DATA")
        if not encoded_values:
            continue
        decoded_data = base64.b64decode(str(encoded_values[0]))
        values.extend(
            line.decode("utf-8") for line in decoded_data.splitlines()
        )
    return values


def write_information_attachment(
    report_xml: Union[str, bytes, object],
    stakeholder_tag: str,
    asset_directory: Path,
    filename_prefix: str,
    heading: str,
    qid: str,
) -> str:
    """Write one legacy information-gathered attachment."""
    report = parse_report(report_xml)
    filename = "{}-{}.csv".format(filename_prefix, stakeholder_tag)
    lines: List[str] = []
    for web_application in report.xpath("./RESULTS/WEB_APPLICATION"):
        lines.extend(
            [
                "",
                "{} {}:".format(heading, str(web_application.NAME)),
            ]
        )
        lines.extend(_decoded_information_values(web_application, qid))
    _write_lines(asset_directory / filename, lines)
    return filename


def build_sensitive_finding_payload(
    stakeholder_tag: str,
    qids: Sequence[str],
) -> str:
    """Build a Qualys request for active non-false-positive sensitive findings."""
    root = E.ServiceRequest(
        E.preferences(E.limitResults("1000"), E.verbose("true")),
        E.filters(
            E.Criteria(", ".join(qids), field="qid", operator="IN"),
            E.Criteria(
                stakeholder_tag,
                field="webApp.tags.name",
                operator="EQUALS",
            ),
            E.Criteria(
                "FALSE_POSITIVE",
                field="ignoredReason",
                operator="NOT EQUALS",
            ),
            E.Criteria("FIXED", field="status", operator="NOT EQUALS"),
        ),
    )
    objectify.deannotate(root, xsi_nil=True, pytype=True, xsi=True)
    return etree.tostring(root).decode()


def parse_sensitive_findings(response_xml: str) -> Tuple[List[str], List[str]]:
    """Return links and response payloads from a Qualys finding response."""
    root = objectify.fromstring(response_xml.encode())
    links: List[str] = []
    responses: List[str] = []
    for finding in root.xpath("./data/Finding"):
        payload_instances = finding.xpath(
            "./resultList/list/Result/payloads/list/PayloadInstance"
        )
        if not payload_instances:
            continue
        payload_instance = payload_instances[0]
        response_values = payload_instance.xpath("./response")
        link_values = payload_instance.xpath("./request/link")
        if response_values and link_values:
            links.append(str(link_values[0]))
            responses.append(str(response_values[0]))
    return links, responses


def retrieve_sensitive_findings(
    client: QualysClient,
    stakeholder_tag: str,
    qids: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """Retrieve sensitive findings for one stakeholder and QID collection."""
    response_xml = client.request(
        QualysRequest(
            endpoint=SENSITIVE_FINDING_ENDPOINT,
            payload=build_sensitive_finding_payload(stakeholder_tag, qids),
            http_method="POST",
        )
    )
    return parse_sensitive_findings(response_xml)


def write_sensitive_data_attachment(
    client: QualysClient,
    stakeholder_tag: str,
    asset_directory: Path,
) -> str:
    """Write the legacy SSN and credit-card findings attachment."""
    ssn_links, ssn_values = retrieve_sensitive_findings(
        client, stakeholder_tag, SSN_QIDS
    )
    card_links, card_values = retrieve_sensitive_findings(
        client, stakeholder_tag, CREDIT_CARD_QIDS
    )
    if not ssn_links:
        ssn_links.append("No SSN data found.")
    if not card_links:
        card_links.append("No Credit Card data found.")

    filename = "ssn-and-cc-found.csv"
    output_path = asset_directory / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file, lineterminator="\n")
        writer.writerow(
            ["SSN URL", "SSN FOUND", "", "CC URL", "CREDIT CARD FOUND"]
        )
        for ssn_link, ssn_value, card_link, card_value in zip_longest(
            ssn_links,
            ssn_values,
            card_links,
            card_values,
            fillvalue="",
        ):
            writer.writerow([ssn_link, ssn_value, "", card_link, card_value])
    return filename


def generate_report_artifacts(
    report_xml: Union[str, bytes, object],
    stakeholder_tag: str,
    asset_directory: Path,
    client: QualysClient,
) -> ReportArtifactResult:
    """Create the active report attachment artifacts used by the template."""
    return ReportArtifactResult(
        vulnerabilities_by_webapp=write_vulnerabilities_by_webapp(
            report_xml, stakeholder_tag, asset_directory
        ),
        application_overview=write_application_overview(
            report_xml, stakeholder_tag, asset_directory
        ),
        links_crawled=write_information_attachment(
            report_xml,
            stakeholder_tag,
            asset_directory,
            "links-crawled",
            "Links for web application",
            LINKS_CRAWLED_QID,
        ),
        emails_found=write_information_attachment(
            report_xml,
            stakeholder_tag,
            asset_directory,
            "emails-found",
            "Emails found for web application",
            EMAILS_FOUND_QID,
        ),
        rejected_links=write_information_attachment(
            report_xml,
            stakeholder_tag,
            asset_directory,
            "rejected-links",
            "Rejected Links found for web application",
            REJECTED_LINKS_QID,
        ),
        sensitive_data=write_sensitive_data_attachment(
            client, stakeholder_tag, asset_directory
        ),
    )
