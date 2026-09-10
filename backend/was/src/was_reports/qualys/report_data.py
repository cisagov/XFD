"""Qualys report data functions for WAS reporting."""

# Standard Python Libraries
from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import Callable, Dict, Optional

# Third-Party Libraries
from lxml import etree, objectify
from lxml.builder import E
import requests

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, QualysRequest
from was_reports.utils.env import getenv

WEBAPP_REPORT_TEMPLATE_ID = "1994875"
DETAIL_REPORT_TEMPLATE_ID = "2201149"
CUSTOMER_PARENT_TAG = "WAS_CUSTOMERS"
DEFAULT_CREATE_RECONCILE_TIMEOUT_SECONDS = 300.0
DEFAULT_CREATE_RECONCILE_POLL_SECONDS = 10.0
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class QualysReportReference:
    """Identifying fields returned by the Qualys report search API."""

    report_id: str
    name: str
    report_format: str
    status: str | None


class QualysReportCreationUncertainError(RuntimeError):
    """Indicate that Qualys may have created a report that was not found."""


def _positive_float_setting(name: str, default: float) -> float:
    """Return a positive floating-point environment setting."""
    raw_value = getenv(name, str(default))
    try:
        value = float(raw_value) if raw_value is not None else default
    except ValueError as error:
        raise ValueError("{} must be numeric.".format(name)) from error
    if value <= 0:
        raise ValueError("{} must be greater than zero.".format(name))
    return value


def xml_to_string(root) -> str:
    """Serialize an XML object for submission to Qualys."""
    objectify.deannotate(root, xsi_nil=True, pytype=True, xsi=True)
    etree.cleanup_namespaces(root)
    payload = etree.tostring(root).decode()
    payload = payload.replace("&lt;", "<")
    return payload.replace("&gt;", ">")


def build_tag_lookup_payload(tag_name: str) -> str:
    """Build the Qualys tag lookup request payload."""
    root = E.ServiceRequest(
        E.filters(
            E.Criteria(str(tag_name), field="name", operator="EQUALS"),
        )
    )
    return xml_to_string(root)


def parse_tag_id(response_xml: str) -> str:
    """Parse a Qualys tag ID from a tag lookup response."""
    root = objectify.fromstring(response_xml.encode())
    if int(root.count) == 0:
        raise LookupError("No Qualys tag found with the supplied name.")
    return str(root.data.Tag.id)


def get_tag_id(client: QualysClient, tag_name: str) -> str:
    """Return the Qualys tag ID for a stakeholder tag name."""
    response_xml = client.request(
        QualysRequest(
            endpoint="search/am/tag",
            payload=build_tag_lookup_payload(tag_name),
        )
    )
    return parse_tag_id(response_xml)


def build_webapp_count_payload(tag_name: str) -> str:
    """Build the Qualys web application count payload."""
    root = E.ServiceRequest(
        E.filters(
            E.Criteria(str(tag_name), field="tags.name", operator="EQUALS"),
        )
    )
    return xml_to_string(root)


def parse_count(response_xml: str) -> int:
    """Parse a Qualys count response."""
    root = objectify.fromstring(response_xml.encode())
    return int(root.count)


def count_webapps(client: QualysClient, tag_name: str) -> int:
    """Return the number of web applications associated with a tag."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/count/was/webapp",
            payload=build_webapp_count_payload(tag_name),
            http_method="POST",
        )
    )
    return parse_count(response_xml)


def build_customer_tags_payload(
    parent_tag_name: str = CUSTOMER_PARENT_TAG,
) -> str:
    """Build the Qualys request for child stakeholder tags."""
    root = E.ServiceRequest(
        E.preferences(E.limitResults("1000")),
        E.filters(
            E.Criteria(
                str(parent_tag_name),
                field="name",
                operator="EQUALS",
            ),
        ),
    )
    return xml_to_string(root)


def parse_customer_tags(response_xml: str) -> Dict[str, str]:
    """Return stakeholder tag names mapped to their descriptions."""
    root = objectify.fromstring(response_xml.encode())
    parent_tags = root.xpath("./data/Tag")
    if not parent_tags:
        raise LookupError("Qualys did not return the WAS customer parent tag.")

    customer_tags: Dict[str, str] = {}
    for tag in parent_tags[0].xpath("./children/list/Tag"):
        tag_name = str(tag.name)
        description_elements = tag.xpath("./description")
        description = (
            str(description_elements[0]) if description_elements else tag_name
        )
        customer_tags[tag_name] = description
    return customer_tags


def list_customer_tags(
    client: QualysClient,
    parent_tag_name: str = CUSTOMER_PARENT_TAG,
) -> Dict[str, str]:
    """Return Qualys child tags under the WAS customer parent tag."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/search/am/tag",
            payload=build_customer_tags_payload(parent_tag_name),
            http_method="POST",
        )
    )
    return parse_customer_tags(response_xml)


def load_report_template(template_path: Path):
    """Load a Qualys report request XML template."""
    if not template_path.is_file():
        raise FileNotFoundError(
            "Qualys report template not found at {}.".format(str(template_path))
        )
    return objectify.fromstring(template_path.read_bytes())


def build_webapp_report_payload(
    report_name: str,
    tag_id: str,
    template_path: Path,
    template_id: str = WEBAPP_REPORT_TEMPLATE_ID,
) -> str:
    """Build a Qualys XML web application report request payload."""
    root = load_report_template(template_path)
    root.data.Report.template.id = template_id
    root.data.Report.config.webAppReport.target.tags.included.tagList.Tag.id = tag_id
    root.data.Report.name = "<![CDATA[{}]]>".format(report_name)
    root.data.Report.format = "XML"
    return xml_to_string(root)


def build_detail_report_payload(
    report_name: str,
    target_id: str,
    template_path: Path,
    from_webapp_id: bool = False,
    template_id: str = DETAIL_REPORT_TEMPLATE_ID,
) -> str:
    """Build a Qualys PDF detail report request payload."""
    root = load_report_template(template_path)
    root.data.Report.template.id = template_id
    if from_webapp_id:
        root.data.Report.config.webAppReport.target.webapps.WebApp.id = target_id
    else:
        root.data.Report.config.webAppReport.target.tags.included.tagList.Tag.id = (
            target_id
        )
    root.data.Report.name = "<![CDATA[{}]]>".format(report_name)
    root.data.Report.format = "PDF"
    return xml_to_string(root)


def parse_created_report_id(response_xml: str) -> str:
    """Parse a created Qualys report ID from a create-report response."""
    root = objectify.fromstring(response_xml.encode())
    if str(root.responseCode) != "SUCCESS":
        raise RuntimeError(
            "Qualys report creation failed with response code {}.".format(
                str(root.responseCode)
            )
        )
    return str(root.data.Report.id)


def build_report_search_payload(report_name: str, report_format: str) -> str:
    """Build an exact Qualys report search for timeout reconciliation."""
    root = E.ServiceRequest(
        E.preferences(
            E.limitResults("100"),
            E.startFromOffset("1"),
            E.verbose("true"),
        ),
        E.filters(
            E.Criteria(report_name, field="name", operator="EQUALS"),
            E.Criteria(report_format, field="format", operator="EQUALS"),
        ),
    )
    return xml_to_string(root)


def parse_report_search(response_xml: str) -> list[QualysReportReference]:
    """Parse report references returned by the Qualys report search API."""
    root = objectify.fromstring(response_xml.encode())
    references: list[QualysReportReference] = []
    reports = root.xpath("./data/Report | ./data/list/Report")
    for report in reports:
        report_ids = report.xpath("./id")
        names = report.xpath("./name")
        formats = report.xpath("./format")
        statuses = report.xpath("./status")
        if not report_ids or not names or not formats:
            continue
        references.append(
            QualysReportReference(
                report_id=str(report_ids[0]),
                name=str(names[0]),
                report_format=str(formats[0]),
                status=str(statuses[0]) if statuses else None,
            )
        )
    return references


def search_reports(
    client: QualysClient,
    report_name: str,
    report_format: str,
) -> list[QualysReportReference]:
    """Search for an exact report name and format in the caller's scope."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/search/was/report",
            payload=build_report_search_payload(report_name, report_format),
            http_method="POST",
        )
    )
    return [
        report
        for report in parse_report_search(response_xml)
        if report.name == report_name and report.report_format == report_format
    ]


def reconcile_created_report(
    client: QualysClient,
    report_name: str,
    report_format: str,
    operation_label: str,
    timeout_seconds: float | None = None,
    poll_seconds: float | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
    monotonic_function: Callable[[], float] = time.monotonic,
) -> str:
    """Find one report created despite an uncertain create response."""
    resolved_timeout = timeout_seconds or _positive_float_setting(
        "WAS_QUALYS_CREATE_RECONCILE_TIMEOUT_SECONDS",
        DEFAULT_CREATE_RECONCILE_TIMEOUT_SECONDS,
    )
    resolved_poll = poll_seconds or _positive_float_setting(
        "WAS_QUALYS_CREATE_RECONCILE_POLL_SECONDS",
        DEFAULT_CREATE_RECONCILE_POLL_SECONDS,
    )
    deadline = monotonic_function() + resolved_timeout
    while True:
        matching_reports = search_reports(client, report_name, report_format)
        if len(matching_reports) == 1:
            report_id = matching_reports[0].report_id
            LOGGER.info(
                "Recovered Qualys %s ID %s after an uncertain create response.",
                operation_label,
                report_id,
            )
            return report_id
        if len(matching_reports) > 1:
            raise QualysReportCreationUncertainError(
                "Multiple Qualys {} records matched unique report name {}; "
                "manual reconciliation is required.".format(
                    operation_label,
                    report_name,
                )
            )
        if monotonic_function() >= deadline:
            raise QualysReportCreationUncertainError(
                "Qualys {} creation timed out and no matching report appeared "
                "within {} seconds.".format(
                    operation_label,
                    int(resolved_timeout),
                )
            )
        LOGGER.info(
            "Waiting for Qualys %s %s to become searchable after a create timeout.",
            operation_label,
            report_name,
        )
        sleep_function(resolved_poll)


def create_report_with_recovery(
    client: QualysClient,
    payload: str,
    report_name: str,
    report_format: str,
    operation_label: str,
) -> str:
    """Create one report and recover its ID after an uncertain network failure."""
    try:
        response_xml = client.request(
            QualysRequest(
                endpoint="/create/was/report",
                payload=payload,
                http_method="post",
            )
        )
    except (requests.ConnectionError, requests.Timeout) as error:
        LOGGER.warning(
            "Qualys %s creation response was uncertain (%s); searching for "
            "the unique report name before any replacement is attempted.",
            operation_label,
            type(error).__name__,
        )
        try:
            return reconcile_created_report(
                client=client,
                report_name=report_name,
                report_format=report_format,
                operation_label=operation_label,
            )
        except QualysReportCreationUncertainError as reconciliation_error:
            raise reconciliation_error from error
    return parse_created_report_id(response_xml)


def create_webapp_xml_report(
    client: QualysClient,
    report_name: str,
    tag_id: str,
    template_path: Path,
    template_id: str = WEBAPP_REPORT_TEMPLATE_ID,
) -> str:
    """Create a Qualys XML web application report and return its report ID."""
    return create_report_with_recovery(
        client=client,
        payload=build_webapp_report_payload(
            report_name=report_name,
            tag_id=tag_id,
            template_path=template_path,
            template_id=template_id,
        ),
        report_name=report_name,
        report_format="XML",
        operation_label="XML report",
    )


def create_detail_pdf_report(
    client: QualysClient,
    report_name: str,
    target_id: str,
    template_path: Path,
    from_webapp_id: bool = False,
    template_id: str = DETAIL_REPORT_TEMPLATE_ID,
) -> str:
    """Create a Qualys PDF detail report and return its report ID."""
    return create_report_with_recovery(
        client=client,
        payload=build_detail_report_payload(
            report_name=report_name,
            target_id=target_id,
            template_path=template_path,
            from_webapp_id=from_webapp_id,
            template_id=template_id,
        ),
        report_name=report_name,
        report_format="PDF",
        operation_label="detail PDF report",
    )


def get_report_xml(client: QualysClient, report_id: str) -> str:
    """Download a generated Qualys WAS report as XML."""
    return client.request(
        QualysRequest(
            endpoint="/download/was/report/{}".format(report_id),
            http_method="get",
        )
    )


def parse_report_status(response_xml: str) -> Optional[str]:
    """Parse a Qualys report status response."""
    root = etree.fromstring(response_xml.encode())
    status = root.find("./data/Report/status")
    if status is None:
        return None
    return status.text


def get_report_status(client: QualysClient, report_id: str) -> Optional[str]:
    """Return the status for a generated Qualys report."""
    response_xml = client.request(
        QualysRequest(
            endpoint="/status/was/report/{}".format(report_id),
            http_method="get",
        )
    )
    return parse_report_status(response_xml)


def delete_report(client: QualysClient, report_id: str) -> bool:
    """Delete a temporary Qualys report and return whether it succeeded."""
    response_xml = client.request(
        QualysRequest(endpoint="/delete/was/report/{}".format(report_id))
    )
    root = objectify.fromstring(response_xml.encode())
    return str(root.responseCode) == "SUCCESS"
