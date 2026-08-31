"""Tests for WAS Qualys source-data retrieval orchestration."""

# Standard Python Libraries
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.reporting import report_retrieval
from was_reports.utils.qualys_config import QualysCredentials


class ReportRetrievalTests(unittest.TestCase):
    """Validate the active WAS report retrieval sequence."""

    def setUp(self) -> None:
        """Create shared report retrieval test values."""
        self.client = Mock()
        self.credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )
        self.resource_root = Path("/resources")
        self.output_directory = Path("/output")

    @patch("was_reports.reporting.report_retrieval.report_data.get_report_xml")
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_webapp_xml_report"
    )
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_detail_pdf_report"
    )
    @patch("was_reports.reporting.report_retrieval.report_data.get_tag_id")
    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_includes_detail_pdf_below_limit(
        self,
        mock_count_webapps,
        mock_get_tag_id,
        mock_create_detail_report,
        mock_create_xml_report,
        mock_get_report_xml,
    ) -> None:
        """Preserve the legacy detail attachment threshold behavior."""
        mock_count_webapps.return_value = 34
        mock_get_tag_id.return_value = "tag-123"
        mock_create_detail_report.return_value = "detail-456"
        mock_create_xml_report.return_value = "xml-789"
        mock_get_report_xml.return_value = "<WAS_WEBAPP_REPORT />"
        detail_downloader = Mock(return_value=Path("/legacy/assets/TAGDetails.pdf"))

        source_data = report_retrieval.retrieve_report_source_data(
            client=self.client,
            stakeholder_tag="TAG",
            credentials=self.credentials,
            resource_root=self.resource_root,
            output_directory=self.output_directory,
            python_executable="python3",
            detail_downloader=detail_downloader,
        )

        self.assertEqual(source_data.web_application_count, 34)
        self.assertEqual(source_data.tag_id, "tag-123")
        self.assertEqual(source_data.xml_report_id, "xml-789")
        self.assertEqual(source_data.report_xml, "<WAS_WEBAPP_REPORT />")
        self.assertEqual(
            source_data.detail_pdf_path,
            Path("/legacy/assets/TAGDetails.pdf"),
        )
        detail_downloader.assert_called_once()

    @patch("was_reports.reporting.report_retrieval.report_data.get_report_xml")
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_webapp_xml_report"
    )
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_detail_pdf_report"
    )
    @patch("was_reports.reporting.report_retrieval.report_data.get_tag_id")
    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_skips_detail_pdf_at_limit(
        self,
        mock_count_webapps,
        mock_get_tag_id,
        mock_create_detail_report,
        mock_create_xml_report,
        mock_get_report_xml,
    ) -> None:
        """Skip the detail attachment when the web application count is 35."""
        mock_count_webapps.return_value = 35
        mock_get_tag_id.return_value = "tag-123"
        mock_create_xml_report.return_value = "xml-789"
        mock_get_report_xml.return_value = "<WAS_WEBAPP_REPORT />"
        detail_downloader = Mock()

        source_data = report_retrieval.retrieve_report_source_data(
            client=self.client,
            stakeholder_tag="TAG",
            credentials=self.credentials,
            resource_root=self.resource_root,
            output_directory=self.output_directory,
            python_executable="python3",
            detail_downloader=detail_downloader,
        )

        self.assertIsNone(source_data.detail_pdf_path)
        mock_create_detail_report.assert_not_called()
        detail_downloader.assert_not_called()

    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_rejects_empty_tag(
        self,
        mock_count_webapps,
    ) -> None:
        """Stop before report creation when the tag has no web applications."""
        mock_count_webapps.return_value = 0

        with self.assertRaises(LookupError):
            report_retrieval.retrieve_report_source_data(
                client=self.client,
                stakeholder_tag="TAG",
                credentials=self.credentials,
                resource_root=self.resource_root,
                output_directory=self.output_directory,
                python_executable="python3",
            )

    @patch("was_reports.reporting.report_retrieval.report_data.delete_report")
    @patch("was_reports.reporting.report_retrieval.report_data.get_report_xml")
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_webapp_xml_report"
    )
    @patch("was_reports.reporting.report_retrieval.report_data.get_tag_id")
    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_cleans_up_failed_xml_download(
        self,
        mock_count_webapps,
        mock_get_tag_id,
        mock_create_xml_report,
        mock_get_report_xml,
        mock_delete_report,
    ) -> None:
        """Delete the temporary Qualys report when XML download fails."""
        mock_count_webapps.return_value = 35
        mock_get_tag_id.return_value = "tag-123"
        mock_create_xml_report.return_value = "xml-789"
        mock_get_report_xml.side_effect = RuntimeError("download failed")

        with self.assertRaises(RuntimeError):
            report_retrieval.retrieve_report_source_data(
                client=self.client,
                stakeholder_tag="TAG",
                credentials=self.credentials,
                resource_root=self.resource_root,
                output_directory=self.output_directory,
                python_executable="python3",
            )

        mock_delete_report.assert_called_once_with(self.client, "xml-789")

    @patch("was_reports.reporting.report_retrieval.report_data.delete_report")
    @patch("was_reports.reporting.report_retrieval.retrieve_report_source_data")
    def test_managed_source_data_cleans_up_after_processing_error(
        self,
        mock_retrieve_source_data,
        mock_delete_report,
    ) -> None:
        """Delete the temporary XML report after downstream processing fails."""
        source_data = report_retrieval.ReportSourceData(
            stakeholder_tag="TAG",
            tag_id="tag-123",
            web_application_count=35,
            xml_report_id="xml-789",
            report_xml="<WAS_WEBAPP_REPORT />",
            detail_pdf_path=None,
        )
        mock_retrieve_source_data.return_value = source_data

        with self.assertRaises(RuntimeError):
            with report_retrieval.managed_report_source_data(
                client=self.client,
                stakeholder_tag="TAG",
                credentials=self.credentials,
                resource_root=self.resource_root,
                output_directory=self.output_directory,
                python_executable="python3",
            ):
                raise RuntimeError("transformation failed")

        mock_delete_report.assert_called_once_with(self.client, "xml-789")


if __name__ == "__main__":
    unittest.main()
