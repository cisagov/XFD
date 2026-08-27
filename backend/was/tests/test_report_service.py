"""Tests for extracted WAS report pipeline orchestration."""

# Standard Python Libraries
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

# First-Party Libraries
from was_reports.qualys import finding_ages
from was_reports.reporting import (
    chart_renderer,
    latex_renderer,
    report_artifacts,
    report_retrieval,
    report_service,
    report_transformer,
)
from was_reports.utils.qualys_config import QualysCredentials

CURRENT_TIME = datetime(2026, 8, 27, 13, 0)


class ReportServiceTests(unittest.TestCase):
    """Validate extracted report pipeline sequencing and data flow."""

    def setUp(self) -> None:
        """Create representative service dependencies."""
        self.client = Mock()
        self.credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )
        self.paths = report_service.ReportServicePaths(
            legacy_root=Path("/legacy"),
            working_directory=Path("/work"),
            asset_directory=Path("/work/assets"),
            output_directory=Path("/output"),
        )

    @patch("was_reports.reporting.report_service.latex_renderer.render_report_pdf")
    @patch(
        "was_reports.reporting.report_service.report_template_data.build_template_data"
    )
    @patch("was_reports.reporting.report_service.finding_ages.retrieve_finding_ages")
    @patch(
        "was_reports.reporting.report_service.report_artifacts.generate_report_artifacts"
    )
    @patch("was_reports.reporting.report_service.chart_renderer.render_report_charts")
    @patch(
        "was_reports.reporting.report_service.report_metrics.calculate_finding_metrics"
    )
    @patch(
        "was_reports.reporting.report_service.report_transformer.transform_report_to_csv"
    )
    @patch(
        "was_reports.reporting.report_service.report_retrieval.managed_report_source_data"
    )
    @patch("was_reports.reporting.report_service.resolve_organization_name")
    def test_generate_unencrypted_report_connects_extracted_modules(
        self,
        mock_resolve_name,
        mock_managed_source_data,
        mock_transform,
        mock_metrics,
        mock_charts,
        mock_artifacts,
        mock_ages,
        mock_template_data,
        mock_render,
    ) -> None:
        """Pass retrieved values through every extracted report boundary."""
        source_data = report_retrieval.ReportSourceData(
            stakeholder_tag="CUSTOMER",
            tag_id="tag-1",
            web_application_count=12,
            xml_report_id="report-1",
            report_xml="<WAS_WEBAPP_REPORT />",
            detail_pdf_path=Path("/work/assets/CUSTOMERDetails.pdf"),
        )

        @contextmanager
        def source_context(*args, **kwargs):
            """Yield representative managed Qualys source data."""
            yield source_data

        mock_resolve_name.return_value = "Customer Organization"
        mock_managed_source_data.side_effect = source_context
        mock_transform.return_value = report_transformer.TransformationResult(
            vulnerability_filename="vulnerability-list-CUSTOMER.csv",
            information_filename="information-gathered-listCUSTOMER.csv",
            severities=["4"],
            ages=[10],
        )
        finding_metrics_result = Mock()
        mock_metrics.return_value = finding_metrics_result
        mock_charts.return_value = chart_renderer.ChartArtifacts(
            *(Path("/work/assets/chart.png") for unused_index in range(5))
        )
        mock_artifacts.return_value = report_artifacts.ReportArtifactResult(
            "vulns.csv",
            "overview.csv",
            "links.csv",
            "emails.csv",
            "rejects.csv",
            "sensitive.csv",
        )
        mock_ages.return_value = finding_ages.FindingAges(10, 20)
        mock_template_data.return_value = {"OrgName": "Customer Organization"}
        mock_render.return_value = latex_renderer.LatexRenderResult(
            tex_path=Path("/work/CUSTOMER_report_2026-08-27.tex"),
            pdf_path=Path("/output/CUSTOMER_report_2026-08-27.pdf"),
        )

        result = report_service.generate_unencrypted_report(
            client=self.client,
            credentials=self.credentials,
            stakeholder_tag="CUSTOMER",
            paths=self.paths,
            python_executable="python3",
            current_time=CURRENT_TIME,
        )

        self.assertEqual(result, Path("/output/CUSTOMER_report_2026-08-27.pdf"))
        mock_transform.assert_called_once()
        mock_charts.assert_called_once_with(
            finding_metrics=finding_metrics_result,
            ages=[10],
            severities=["4"],
            asset_directory=Path("/work/assets"),
        )
        template_arguments = mock_template_data.call_args.kwargs
        self.assertEqual(
            template_arguments["artifacts"].detail_pdf,
            "CUSTOMERDetails.pdf",
        )
        self.assertEqual(template_arguments["finding_ages"].critical_days, 10)
        mock_render.assert_called_once()

    @patch("was_reports.reporting.report_service.report_data.list_customer_tags")
    def test_resolve_organization_name_falls_back_to_tag(
        self,
        mock_list_customer_tags,
    ) -> None:
        """Use the stakeholder tag when Qualys has no child-tag description."""
        mock_list_customer_tags.return_value = {"OTHER": "Other Organization"}

        result = report_service.resolve_organization_name(
            self.client,
            "CUSTOMER",
        )

        self.assertEqual(result, "CUSTOMER")

    @patch("was_reports.reporting.report_service.publish_encrypted_pdf")
    @patch("was_reports.reporting.report_service.encrypt_pdf_in_place")
    @patch("was_reports.reporting.report_service.generate_unencrypted_report")
    @patch(
        "was_reports.reporting.report_service.report_workspace.isolated_report_workspace"
    )
    @patch(
        "was_reports.reporting.report_service.report_workspace.report_output_lock"
    )
    def test_generate_encrypted_report_uses_lock_and_private_workspace(
        self,
        mock_output_lock,
        mock_workspace,
        mock_generate_unencrypted,
        mock_encrypt,
        mock_publish,
    ) -> None:
        """Isolate temporary artifacts and encrypt before returning output."""
        mock_output_lock.return_value.__enter__.return_value = None
        mock_workspace.return_value.__enter__.return_value = Path("/private")
        unencrypted_path = Path("/private/docs/CUSTOMER_report_2026-08-27.pdf")
        final_path = Path("/output/CUSTOMER_report_2026-08-27.pdf")
        mock_generate_unencrypted.return_value = unencrypted_path
        mock_encrypt.return_value = unencrypted_path
        mock_publish.return_value = final_path

        result = report_service.generate_encrypted_report(
            client=self.client,
            credentials=self.credentials,
            stakeholder_tag="CUSTOMER",
            legacy_root=Path("/legacy"),
            workspace_root=Path("/workspaces"),
            output_directory=Path("/output"),
            python_executable="python3",
            current_time=CURRENT_TIME,
            report_password="SecurePassword123!",
        )

        self.assertEqual(result, final_path)
        service_paths = mock_generate_unencrypted.call_args.kwargs["paths"]
        self.assertEqual(service_paths.legacy_root, Path("/private"))
        self.assertEqual(service_paths.asset_directory, Path("/private/assets"))
        self.assertEqual(service_paths.output_directory, Path("/private/docs"))
        mock_encrypt.assert_called_once_with(
            unencrypted_path,
            "SecurePassword123!",
        )
        mock_publish.assert_called_once_with(
            unencrypted_path,
            Path("/output"),
        )


if __name__ == "__main__":
    unittest.main()
