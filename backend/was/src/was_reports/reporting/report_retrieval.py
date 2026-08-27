"""Orchestrate Qualys source-data retrieval for one WAS report."""

# Standard Python Libraries
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional

# First-Party Libraries
from was_reports.qualys import report_data
from was_reports.qualys.qualys_client import QualysClient
from was_reports.reporting import detail_reports
from was_reports.utils.qualys_config import QualysCredentials

DETAIL_REPORT_WEBAPP_LIMIT = 35


@dataclass(frozen=True)
class ReportSourceData:
    """Qualys source artifacts required by the WAS transformation layer."""

    stakeholder_tag: str
    tag_id: str
    web_application_count: int
    xml_report_id: str
    report_xml: str
    detail_pdf_path: Optional[Path]


def retrieve_report_source_data(
    client: QualysClient,
    stakeholder_tag: str,
    credentials: QualysCredentials,
    legacy_root: Path,
    output_directory: Path,
    python_executable: str,
    detail_downloader: Callable = detail_reports.download_and_process_detail_report,
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
    if web_application_count < DETAIL_REPORT_WEBAPP_LIMIT:
        detail_report_id = report_data.create_detail_pdf_report(
            client=client,
            report_name=stakeholder_tag,
            target_id=tag_id,
            template_path=legacy_root / "assets" / "was_report.xml",
        )
        detail_pdf_path = detail_downloader(
            client=client,
            report_id=detail_report_id,
            filename=stakeholder_tag,
            credentials=credentials,
            output_directory=output_directory,
            legacy_root=legacy_root,
            from_webapp=False,
            python_executable=python_executable,
        )

    xml_report_id = report_data.create_webapp_xml_report(
        client=client,
        report_name=stakeholder_tag,
        tag_id=tag_id,
        template_path=legacy_root / "assets" / "was_report.xml",
    )
    try:
        report_xml = report_data.get_report_xml(client, xml_report_id)
    except Exception:
        report_data.delete_report(client, xml_report_id)
        raise

    return ReportSourceData(
        stakeholder_tag=stakeholder_tag,
        tag_id=tag_id,
        web_application_count=web_application_count,
        xml_report_id=xml_report_id,
        report_xml=report_xml,
        detail_pdf_path=detail_pdf_path,
    )


@contextmanager
def managed_report_source_data(
    client: QualysClient,
    stakeholder_tag: str,
    credentials: QualysCredentials,
    legacy_root: Path,
    output_directory: Path,
    python_executable: str,
    detail_downloader: Callable = detail_reports.download_and_process_detail_report,
) -> Iterator[ReportSourceData]:
    """Yield report source data and delete its temporary Qualys XML report."""
    source_data = retrieve_report_source_data(
        client=client,
        stakeholder_tag=stakeholder_tag,
        credentials=credentials,
        legacy_root=legacy_root,
        output_directory=output_directory,
        python_executable=python_executable,
        detail_downloader=detail_downloader,
    )
    try:
        yield source_data
    finally:
        report_data.delete_report(client, source_data.xml_report_id)
