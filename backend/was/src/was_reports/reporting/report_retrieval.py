"""Orchestrate Qualys source-data retrieval for one WAS report."""

# Standard Python Libraries
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
import logging
from pathlib import Path
from typing import Callable, Iterator, Optional
from uuid import uuid4

# Third-Party Libraries
from was_reports.data.report_runs import ActiveReportOperationError

# First-Party Libraries
from was_reports.qualys import report_data
from was_reports.qualys.qualys_client import QualysClient
from was_reports.reporting import detail_reports
from was_reports.utils.logging_config import exception_details
from was_reports.utils.operation_lease import (
    OperationLeaseLostError,
    check_operation_ownership,
)
from was_reports.utils.qualys_config import QualysCredentials

DETAIL_REPORT_WEBAPP_LIMIT = 35
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportSourceData:
    """Qualys source artifacts required by the WAS transformation layer."""

    stakeholder_tag: str
    tag_id: str
    web_application_count: int
    xml_report_id: str
    report_xml: str
    detail_pdf_path: Optional[Path]
    detail_report_id: str | None = None


def report_request_name(
    stakeholder_tag: str,
    report_request_key: str | None,
    artifact_label: str,
) -> str:
    """Return a unique, searchable Qualys report name for one WAS run."""
    report_request_key = report_request_key or "REQUEST-{}".format(uuid4())
    return "WAS-{}-{}-{}".format(
        stakeholder_tag,
        report_request_key,
        artifact_label,
    )


def retrieve_report_source_data(
    client: QualysClient,
    stakeholder_tag: str,
    credentials: QualysCredentials,
    resource_root: Path,
    output_directory: Path,
    python_executable: str,
    report_request_key: str | None = None,
    existing_detail_report_id: str | None = None,
    existing_xml_report_id: str | None = None,
    report_id_recorder: Callable[[str, str], None] | None = None,
    report_id_clearer: Callable[[str, str], None] | None = None,
    report_status_recorder: Callable[[str, str], None] | None = None,
    report_creation_intent_claim: Callable[[str], bool] | None = None,
    detail_downloader: Callable = detail_reports.download_and_process_detail_report,
    report_waiter: Callable = detail_reports.wait_for_report_completion,
) -> ReportSourceData:
    """Retrieve the Qualys XML report and optional detail PDF artifact."""
    web_application_count = report_data.count_webapps(client, stakeholder_tag)
    if web_application_count < 1:
        raise LookupError(
            "No Qualys web applications found for stakeholder tag {}.".format(
                stakeholder_tag
            )
        )

    tag_id = report_data.get_tag_id(client, stakeholder_tag)
    detail_pdf_path = None
    detail_report_id = existing_detail_report_id
    if web_application_count < DETAIL_REPORT_WEBAPP_LIMIT:
        if detail_report_id is None:
            check_operation_ownership()
            detail_report_id = report_data.create_detail_pdf_report(
                client=client,
                report_name=report_request_name(
                    stakeholder_tag,
                    report_request_key,
                    "DETAIL",
                ),
                target_id=tag_id,
                template_path=resource_root / "assets" / "was_report.xml",
                report_request_key=report_request_key,
                creation_intent_claim=(
                    partial(report_creation_intent_claim, "detail")
                    if report_creation_intent_claim is not None
                    else None
                ),
            )
            if report_id_recorder is not None:
                report_id_recorder("detail", detail_report_id)
        else:
            LOGGER.info("Resuming Qualys detail report %s.", detail_report_id)
        detail_arguments = {
            "client": client,
            "report_id": detail_report_id,
            "filename": stakeholder_tag,
            "credentials": credentials,
            "output_directory": output_directory,
            "resource_root": resource_root,
            "from_webapp": False,
            "python_executable": python_executable,
        }
        if report_status_recorder is not None:
            detail_arguments["status_callback"] = partial(
                report_status_recorder,
                "detail",
            )
        check_operation_ownership()
        detail_pdf_path = detail_downloader(**detail_arguments)

    xml_report_id = existing_xml_report_id
    if xml_report_id is None:
        check_operation_ownership()
        xml_report_id = report_data.create_webapp_xml_report(
            client=client,
            report_name=report_request_name(
                stakeholder_tag,
                report_request_key,
                "XML",
            ),
            tag_id=tag_id,
            template_path=resource_root / "assets" / "was_report.xml",
            report_request_key=report_request_key,
            creation_intent_claim=(
                partial(report_creation_intent_claim, "xml")
                if report_creation_intent_claim is not None
                else None
            ),
        )
        if report_id_recorder is not None:
            report_id_recorder("xml", xml_report_id)
    else:
        LOGGER.info("Resuming Qualys XML report %s.", xml_report_id)
    waiter_arguments = {"client": client, "report_id": xml_report_id}
    if report_status_recorder is not None:
        waiter_arguments["status_callback"] = partial(
            report_status_recorder,
            "xml",
        )
    report_waiter(**waiter_arguments)
    report_xml = report_data.get_report_xml(client, xml_report_id)

    return ReportSourceData(
        stakeholder_tag=stakeholder_tag,
        tag_id=tag_id,
        web_application_count=web_application_count,
        xml_report_id=xml_report_id,
        report_xml=report_xml,
        detail_pdf_path=detail_pdf_path,
        detail_report_id=detail_report_id,
    )


@contextmanager
def managed_report_source_data(
    client: QualysClient,
    stakeholder_tag: str,
    credentials: QualysCredentials,
    resource_root: Path,
    output_directory: Path,
    python_executable: str,
    report_request_key: str | None = None,
    existing_detail_report_id: str | None = None,
    existing_xml_report_id: str | None = None,
    report_id_recorder: Callable[[str, str], None] | None = None,
    report_id_clearer: Callable[[str, str], None] | None = None,
    report_status_recorder: Callable[[str, str], None] | None = None,
    report_creation_intent_claim: Callable[[str], bool] | None = None,
    detail_downloader: Callable = detail_reports.download_and_process_detail_report,
    report_waiter: Callable = detail_reports.wait_for_report_completion,
) -> Iterator[ReportSourceData]:
    """Retain retry references on failure; clean up only after successful use."""
    source_data = retrieve_report_source_data(
        client=client,
        stakeholder_tag=stakeholder_tag,
        credentials=credentials,
        resource_root=resource_root,
        output_directory=output_directory,
        python_executable=python_executable,
        report_request_key=report_request_key,
        existing_detail_report_id=existing_detail_report_id,
        existing_xml_report_id=existing_xml_report_id,
        report_id_recorder=report_id_recorder,
        report_id_clearer=report_id_clearer,
        report_status_recorder=report_status_recorder,
        report_creation_intent_claim=report_creation_intent_claim,
        detail_downloader=detail_downloader,
        report_waiter=report_waiter,
    )
    yield source_data
    for label, report_id in (
        ("xml", source_data.xml_report_id),
        ("detail", source_data.detail_report_id),
    ):
        if report_id is None:
            continue
        check_operation_ownership()
        try:
            if report_data.delete_report(client, report_id) is True:
                if report_id_clearer is not None:
                    report_id_clearer(label, report_id)
            else:
                LOGGER.warning(
                    "Qualys %s deletion was not confirmed; retaining its reference.",
                    label,
                )
        except (ActiveReportOperationError, OperationLeaseLostError):
            raise
        except Exception as error:
            LOGGER.warning(
                "Qualys %s cleanup was not confirmed; retaining its reference: %s",
                label,
                exception_details(error),
            )
