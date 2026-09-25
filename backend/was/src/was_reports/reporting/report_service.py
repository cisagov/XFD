"""Orchestrate the production WAS report-generation pipeline."""

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

# Third-Party Libraries
# First-Party Libraries
from was_reports.qualys import finding_ages, report_data
from was_reports.qualys.qualys_client import QualysClient
from was_reports.reporting import (
    chart_renderer,
    latex_renderer,
    report_artifacts,
    report_metrics,
    report_retrieval,
    report_template_data,
    report_transformer,
    report_workspace,
    streaming_report,
)
from was_reports.reporting.pdf_security import (
    encrypt_pdf_in_place,
    publish_encrypted_pdf,
)
from was_reports.utils.qualys_config import QualysCredentials


@dataclass(frozen=True)
class ReportServicePaths:
    """Filesystem paths required by the production report pipeline."""

    resource_root: Path
    working_directory: Path
    asset_directory: Path
    output_directory: Path


def generate_unencrypted_report(
    client: QualysClient,
    credentials: QualysCredentials,
    stakeholder_tag: str,
    paths: ReportServicePaths,
    python_executable: str,
    current_time: datetime,
    report_request_key: str | None = None,
    existing_detail_report_id: str | None = None,
    existing_xml_report_id: str | None = None,
    report_id_recorder: Callable[[str, str], None] | None = None,
    report_id_clearer: Callable[[str, str], None] | None = None,
    report_status_recorder: Callable[[str, str], None] | None = None,
    report_creation_intent_claim: Callable[[str], bool] | None = None,
    tag_id: int | None = None,
    organization_name: str | None = None,
    allow_tag_lookup: bool = True,
) -> Path:
    """Generate one unencrypted PDF through the production WAS modules."""
    resolved_tag_id = tag_id
    resolved_organization_name = organization_name
    if resolved_tag_id is None:
        if not allow_tag_lookup:
            raise ValueError(
                "Automatic report generation requires a stored Qualys tag ID."
            )
        tag_details = report_data.get_tag_details(client, stakeholder_tag)
        resolved_tag_id = tag_details.tag_id
        if not resolved_organization_name:
            resolved_organization_name = tag_details.description
    if not resolved_organization_name:
        resolved_organization_name = stakeholder_tag
    with report_retrieval.managed_report_source_data(
        client=client,
        stakeholder_tag=stakeholder_tag,
        credentials=credentials,
        resource_root=paths.resource_root,
        output_directory=paths.output_directory,
        python_executable=python_executable,
        report_request_key=report_request_key,
        existing_detail_report_id=existing_detail_report_id,
        existing_xml_report_id=existing_xml_report_id,
        report_id_recorder=report_id_recorder,
        report_id_clearer=report_id_clearer,
        report_status_recorder=report_status_recorder,
        report_creation_intent_claim=report_creation_intent_claim,
        tag_id=resolved_tag_id,
    ) as source_data:
        parsed_report = None
        summary_metrics = None
        severity_totals = None
        if source_data.report_xml_path is not None:
            streamed = streaming_report.process_report_xml(
                xml_path=source_data.report_xml_path,
                stakeholder_tag=stakeholder_tag,
                asset_directory=paths.asset_directory,
                client=client,
                current_time=current_time,
            )
            transformation = streamed.transformation
            finding_metrics = streamed.finding_metrics
            summary_metrics = streamed.summary_metrics
            severity_totals = streamed.severity_totals
            generated_artifacts = streamed.artifacts
        else:
            parsed_report = report_transformer.parse_report(source_data.report_xml)
            transformation = report_transformer.transform_report_to_csv(
                report_xml=parsed_report,
                stakeholder_tag=stakeholder_tag,
                asset_directory=paths.asset_directory,
                current_time=current_time,
            )
            finding_metrics = report_metrics.calculate_finding_metrics(
                parsed_report,
                current_time,
            )
            generated_artifacts = report_artifacts.generate_report_artifacts(
                report_xml=parsed_report,
                stakeholder_tag=stakeholder_tag,
                asset_directory=paths.asset_directory,
                client=client,
            )
        chart_renderer.render_report_charts(
            finding_metrics=finding_metrics,
            ages=transformation.ages,
            severities=transformation.severities,
            asset_directory=paths.asset_directory,
        )
        maximum_ages = finding_ages.retrieve_finding_ages(
            client=client,
            stakeholder_tag=stakeholder_tag,
            current_time=current_time,
        )
        template_data = report_template_data.build_template_data(
            report_xml=parsed_report,
            stakeholder_tag=stakeholder_tag,
            organization_name=resolved_organization_name,
            artifacts=report_template_data.TemplateArtifactInputs(
                vulnerability_details=transformation.vulnerability_filename,
                information_details=transformation.information_filename,
                generated=generated_artifacts,
                detail_pdf=(
                    source_data.detail_pdf_path.name
                    if source_data.detail_pdf_path
                    else None
                ),
            ),
            finding_ages=report_template_data.FindingAgeInputs(
                critical_days=maximum_ages.critical_days,
                urgent_days=maximum_ages.urgent_days,
            ),
            web_application_count=source_data.web_application_count,
            current_time=current_time,
            finding_metrics=finding_metrics,
            summary_metrics=summary_metrics,
            severity_totals=severity_totals,
        )
        render_result = latex_renderer.render_report_pdf(
            template_path=paths.working_directory / "NEW_BIG.mustache",
            template_data=template_data,
            stakeholder_tag=stakeholder_tag,
            working_directory=paths.working_directory,
            output_directory=paths.output_directory,
            report_date=current_time.date(),
        )
        return render_result.pdf_path


def generate_encrypted_report(
    client: QualysClient,
    credentials: QualysCredentials,
    stakeholder_tag: str,
    resource_root: Path,
    workspace_root: Path,
    output_directory: Path,
    python_executable: str,
    current_time: datetime,
    report_password: str,
    report_request_key: str | None = None,
    existing_detail_report_id: str | None = None,
    existing_xml_report_id: str | None = None,
    report_id_recorder: Callable[[str, str], None] | None = None,
    report_id_clearer: Callable[[str, str], None] | None = None,
    report_status_recorder: Callable[[str, str], None] | None = None,
    report_creation_intent_claim: Callable[[str], bool] | None = None,
    tag_id: int | None = None,
    organization_name: str | None = None,
    allow_tag_lookup: bool = True,
) -> Path:
    """Generate an encrypted report in an isolated, concurrency-safe workspace."""
    with report_workspace.report_output_lock(
        output_directory,
        stakeholder_tag,
        current_time.date(),
    ):
        with report_workspace.isolated_report_workspace(
            resource_root=resource_root,
            workspace_root=workspace_root,
            stakeholder_tag=stakeholder_tag,
        ) as working_directory:
            private_output_directory = working_directory / "docs"
            pdf_path = generate_unencrypted_report(
                client=client,
                credentials=credentials,
                stakeholder_tag=stakeholder_tag,
                paths=ReportServicePaths(
                    resource_root=working_directory,
                    working_directory=working_directory,
                    asset_directory=working_directory / "assets",
                    output_directory=private_output_directory,
                ),
                python_executable=python_executable,
                current_time=current_time,
                report_request_key=report_request_key,
                existing_detail_report_id=existing_detail_report_id,
                existing_xml_report_id=existing_xml_report_id,
                report_id_recorder=report_id_recorder,
                report_id_clearer=report_id_clearer,
                report_status_recorder=report_status_recorder,
                report_creation_intent_claim=report_creation_intent_claim,
                tag_id=tag_id,
                organization_name=organization_name,
                allow_tag_lookup=allow_tag_lookup,
            )
            encrypted_pdf_path = encrypt_pdf_in_place(pdf_path, report_password)
            return publish_encrypted_pdf(
                encrypted_pdf_path,
                output_directory,
            )
