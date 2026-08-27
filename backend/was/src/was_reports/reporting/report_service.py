"""Orchestrate the extracted unencrypted WAS report-generation pipeline."""

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
)
from was_reports.reporting.pdf_security import (
    encrypt_pdf_in_place,
    publish_encrypted_pdf,
)
from was_reports.utils.qualys_config import QualysCredentials


@dataclass(frozen=True)
class ReportServicePaths:
    """Filesystem paths required by the extracted report pipeline."""

    legacy_root: Path
    working_directory: Path
    asset_directory: Path
    output_directory: Path


def resolve_organization_name(
    client: QualysClient,
    stakeholder_tag: str,
) -> str:
    """Resolve a stakeholder description using the legacy tag hierarchy."""
    customer_tags = report_data.list_customer_tags(client)
    return customer_tags.get(stakeholder_tag, stakeholder_tag)


def generate_unencrypted_report(
    client: QualysClient,
    credentials: QualysCredentials,
    stakeholder_tag: str,
    paths: ReportServicePaths,
    python_executable: str,
    current_time: datetime,
) -> Path:
    """Generate one unencrypted PDF through the extracted WAS modules."""
    organization_name = resolve_organization_name(client, stakeholder_tag)
    with report_retrieval.managed_report_source_data(
        client=client,
        stakeholder_tag=stakeholder_tag,
        credentials=credentials,
        legacy_root=paths.legacy_root,
        output_directory=paths.output_directory,
        python_executable=python_executable,
    ) as source_data:
        transformation = report_transformer.transform_report_to_csv(
            report_xml=source_data.report_xml,
            stakeholder_tag=stakeholder_tag,
            asset_directory=paths.asset_directory,
            current_time=current_time,
        )
        finding_metrics = report_metrics.calculate_finding_metrics(
            source_data.report_xml,
            current_time,
        )
        chart_renderer.render_report_charts(
            finding_metrics=finding_metrics,
            ages=transformation.ages,
            severities=transformation.severities,
            asset_directory=paths.asset_directory,
        )
        generated_artifacts = report_artifacts.generate_report_artifacts(
            report_xml=source_data.report_xml,
            stakeholder_tag=stakeholder_tag,
            asset_directory=paths.asset_directory,
            client=client,
        )
        maximum_ages = finding_ages.retrieve_finding_ages(
            client=client,
            stakeholder_tag=stakeholder_tag,
            current_time=current_time,
        )
        template_data = report_template_data.build_template_data(
            report_xml=source_data.report_xml,
            stakeholder_tag=stakeholder_tag,
            organization_name=organization_name,
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
    legacy_root: Path,
    workspace_root: Path,
    output_directory: Path,
    python_executable: str,
    current_time: datetime,
    report_password: str,
) -> Path:
    """Generate an encrypted report in an isolated, concurrency-safe workspace."""
    with report_workspace.report_output_lock(
        output_directory,
        stakeholder_tag,
        current_time.date(),
    ):
        with report_workspace.isolated_report_workspace(
            legacy_root=legacy_root,
            workspace_root=workspace_root,
            stakeholder_tag=stakeholder_tag,
        ) as working_directory:
            private_output_directory = working_directory / "docs"
            pdf_path = generate_unencrypted_report(
                client=client,
                credentials=credentials,
                stakeholder_tag=stakeholder_tag,
                paths=ReportServicePaths(
                    legacy_root=working_directory,
                    working_directory=working_directory,
                    asset_directory=working_directory / "assets",
                    output_directory=private_output_directory,
                ),
                python_executable=python_executable,
                current_time=current_time,
            )
            encrypted_pdf_path = encrypt_pdf_in_place(pdf_path, report_password)
            return publish_encrypted_pdf(
                encrypted_pdf_path,
                output_directory,
            )
