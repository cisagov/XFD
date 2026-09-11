"""Tests for WAS Qualys source-data retrieval orchestration."""

# Standard Python Libraries
from contextlib import ExitStack
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.reporting import report_retrieval
from was_reports.utils.operation_lease import (
    OperationLeaseLostError,
    operation_heartbeat,
)
from was_reports.utils.qualys_config import QualysCredentials


class ReportRetrievalTests(unittest.TestCase):
    """Validate the active WAS report retrieval sequence."""

    def test_standalone_names_are_unique_without_persistent_request_keys(
        self,
    ) -> None:
        """Do not reuse a stakeholder-only name for independent local requests."""
        first = report_retrieval.report_request_name("TAG", None, "XML")
        second = report_retrieval.report_request_name("TAG", None, "XML")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("WAS-TAG-REQUEST-"))

    def test_polling_uncertainty_preserves_reference_for_retry(self) -> None:
        """Retry with the same ID after timeout or status-persistence failure."""
        for error in (
            TimeoutError("poll timeout"),
            OSError("commit uncertain"),
        ):
            with self.subTest(error=type(error).__name__), ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        report_retrieval.report_data,
                        "count_webapps",
                        return_value=35,
                    )
                )
                stack.enter_context(
                    patch.object(
                        report_retrieval.report_data,
                        "get_tag_id",
                        return_value="tag-1",
                    )
                )
                stack.enter_context(
                    patch.object(
                        report_retrieval.report_data,
                        "get_report_xml",
                        return_value="<report />",
                    )
                )
                create = stack.enter_context(
                    patch.object(
                        report_retrieval.report_data,
                        "create_webapp_xml_report",
                    )
                )
                delete = stack.enter_context(
                    patch.object(report_retrieval.report_data, "delete_report")
                )
                clear = Mock()
                waiter = Mock(side_effect=[error, None])
                arguments = dict(
                    client=self.client,
                    stakeholder_tag="TAG",
                    credentials=self.credentials,
                    resource_root=self.resource_root,
                    output_directory=self.output_directory,
                    python_executable="python3",
                    existing_xml_report_id="xml-saved",
                    report_id_clearer=clear,
                    report_waiter=waiter,
                )
                with self.assertRaises(type(error)):
                    report_retrieval.retrieve_report_source_data(**arguments)
                source = report_retrieval.retrieve_report_source_data(**arguments)
                self.assertEqual(source.xml_report_id, "xml-saved")
                self.assertEqual(waiter.call_count, 2)
                create.assert_not_called()
                delete.assert_not_called()
                clear.assert_not_called()

    def test_cleanup_clears_only_confirmed_deletion(self) -> None:
        """Retain saved IDs after rejected, missing, or uncertain delete responses."""
        source = report_retrieval.ReportSourceData(
            stakeholder_tag="TAG",
            tag_id="tag-1",
            web_application_count=35,
            xml_report_id="xml-saved",
            report_xml="<report />",
            detail_pdf_path=None,
        )
        for outcome in (True, False, None, TimeoutError("delete uncertain")):
            with self.subTest(outcome=type(outcome).__name__), ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        report_retrieval,
                        "retrieve_report_source_data",
                        return_value=source,
                    )
                )
                delete = stack.enter_context(
                    patch.object(report_retrieval.report_data, "delete_report")
                )
                clear = Mock()
                if isinstance(outcome, Exception):
                    delete.side_effect = outcome
                else:
                    delete.return_value = outcome
                try:
                    with report_retrieval.managed_report_source_data(
                        client=self.client,
                        stakeholder_tag="TAG",
                        credentials=self.credentials,
                        resource_root=self.resource_root,
                        output_directory=self.output_directory,
                        python_executable="python3",
                        report_id_clearer=clear,
                    ):
                        pass
                finally:
                    if outcome is True:
                        clear.assert_called_once_with("xml", "xml-saved")
                    else:
                        clear.assert_not_called()
                delete.assert_called_once_with(self.client, "xml-saved")

    def test_cleanup_handles_both_reports_and_retains_uncertain_reference(self) -> None:
        """Clean detail reports after success even if XML deletion is uncertain."""
        source = report_retrieval.ReportSourceData(
            stakeholder_tag="TAG",
            tag_id="tag",
            web_application_count=1,
            xml_report_id="xml-id",
            report_xml="<report />",
            detail_pdf_path=Path("/detail.pdf"),
            detail_report_id="detail-id",
        )
        for xml_result in (True, TimeoutError("private-payload")):
            with self.subTest(
                xml_result=type(xml_result).__name__
            ), ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        report_retrieval,
                        "retrieve_report_source_data",
                        return_value=source,
                    )
                )
                delete = stack.enter_context(
                    patch.object(
                        report_retrieval.report_data,
                        "delete_report",
                        side_effect=[xml_result, True],
                    )
                )
                clear = Mock()
                if isinstance(xml_result, Exception):
                    captured = stack.enter_context(
                        self.assertLogs(report_retrieval.LOGGER, level="WARNING")
                    )
                with report_retrieval.managed_report_source_data(
                    client=self.client,
                    stakeholder_tag="TAG",
                    credentials=self.credentials,
                    resource_root=self.resource_root,
                    output_directory=self.output_directory,
                    python_executable="python3",
                    report_id_clearer=clear,
                ):
                    delete.assert_not_called()
                self.assertEqual(delete.call_count, 2)
                clear.assert_any_call("detail", "detail-id")
                if xml_result is True:
                    clear.assert_any_call("xml", "xml-id")
                else:
                    clear.assert_called_once_with("detail", "detail-id")
                    self.assertNotIn("private-payload", " ".join(captured.output))

    def test_cleanup_database_error_does_not_fail_rendered_report(self) -> None:
        """Keep successful rendering when confirmed deletion cannot be recorded."""
        source = report_retrieval.ReportSourceData(
            "TAG", "tag", 35, "xml-id", "<report />", None
        )
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    report_retrieval, "retrieve_report_source_data", return_value=source
                )
            )
            stack.enter_context(
                patch.object(
                    report_retrieval.report_data, "delete_report", return_value=True
                )
            )
            clear = Mock(side_effect=OSError("private-sql-payload"))
            captured = stack.enter_context(
                self.assertLogs(report_retrieval.LOGGER, level="WARNING")
            )
            with report_retrieval.managed_report_source_data(
                client=self.client,
                stakeholder_tag="TAG",
                credentials=self.credentials,
                resource_root=self.resource_root,
                output_directory=self.output_directory,
                python_executable="python3",
                report_id_clearer=clear,
            ):
                pass
            self.assertNotIn("private-sql-payload", " ".join(captured.output))

    def test_lost_ownership_retains_xml_during_cleanup(self) -> None:
        """Never delete a Qualys artifact after another worker owns the run."""
        source = report_retrieval.ReportSourceData(
            stakeholder_tag="TAG",
            tag_id="tag-1",
            web_application_count=35,
            xml_report_id="xml-1",
            report_xml="<report />",
            detail_pdf_path=None,
        )
        heartbeat = Mock(side_effect=[True, False])
        with patch.object(
            report_retrieval,
            "retrieve_report_source_data",
            return_value=source,
        ):
            with patch.object(report_retrieval.report_data, "delete_report") as delete:
                with self.assertRaises(OperationLeaseLostError):
                    with operation_heartbeat(heartbeat, "test"):
                        with report_retrieval.managed_report_source_data(
                            client=self.client,
                            stakeholder_tag="TAG",
                            credentials=self.credentials,
                            resource_root=self.resource_root,
                            output_directory=self.output_directory,
                            python_executable="python3",
                        ):
                            pass
                delete.assert_not_called()

    def test_lost_ownership_prevents_report_creation(self) -> None:
        """Recheck ownership immediately before Qualys report creation."""
        with patch.object(
            report_retrieval.report_data, "count_webapps", return_value=35
        ):
            with patch.object(
                report_retrieval.report_data,
                "get_tag_id",
                return_value="tag-1",
            ):
                with patch.object(
                    report_retrieval.report_data, "create_webapp_xml_report"
                ) as create:
                    with self.assertRaises(OperationLeaseLostError):
                        with operation_heartbeat(
                            Mock(side_effect=[True, False]), "test"
                        ):
                            report_retrieval.retrieve_report_source_data(
                                client=self.client,
                                stakeholder_tag="TAG",
                                credentials=self.credentials,
                                resource_root=self.resource_root,
                                output_directory=self.output_directory,
                                python_executable="python3",
                            )
                    create.assert_not_called()

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
        report_waiter = Mock()

        claim = Mock(return_value=True)
        source_data = report_retrieval.retrieve_report_source_data(
            client=self.client,
            stakeholder_tag="TAG",
            credentials=self.credentials,
            resource_root=self.resource_root,
            output_directory=self.output_directory,
            python_executable="python3",
            report_request_key="RUN-17",
            report_creation_intent_claim=claim,
            detail_downloader=detail_downloader,
            report_waiter=report_waiter,
        )

        self.assertEqual(source_data.web_application_count, 34)
        self.assertEqual(source_data.detail_report_id, "detail-456")
        for creation, label in (
            (mock_create_detail_report, "detail"),
            (mock_create_xml_report, "xml"),
        ):
            self.assertEqual(creation.call_args.kwargs["report_request_key"], "RUN-17")
            self.assertIs(creation.call_args.kwargs["creation_intent_claim"](), True)
            claim.assert_called_with(label)
        self.assertEqual(source_data.tag_id, "tag-123")
        self.assertEqual(source_data.xml_report_id, "xml-789")
        self.assertEqual(source_data.report_xml, "<WAS_WEBAPP_REPORT />")
        self.assertEqual(
            source_data.detail_pdf_path,
            Path("/legacy/assets/TAGDetails.pdf"),
        )
        detail_downloader.assert_called_once()
        self.assertEqual(
            mock_create_detail_report.call_args.kwargs["report_name"],
            "WAS-TAG-RUN-17-DETAIL",
        )
        self.assertEqual(
            mock_create_xml_report.call_args.kwargs["report_name"],
            "WAS-TAG-RUN-17-XML",
        )
        report_waiter.assert_called_once_with(
            client=self.client,
            report_id="xml-789",
        )

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
        report_waiter = Mock()

        source_data = report_retrieval.retrieve_report_source_data(
            client=self.client,
            stakeholder_tag="TAG",
            credentials=self.credentials,
            resource_root=self.resource_root,
            output_directory=self.output_directory,
            python_executable="python3",
            detail_downloader=detail_downloader,
            report_waiter=report_waiter,
        )

        self.assertIsNone(source_data.detail_pdf_path)
        self.assertIsNone(source_data.detail_report_id)
        mock_create_detail_report.assert_not_called()
        detail_downloader.assert_not_called()
        report_waiter.assert_called_once_with(
            client=self.client,
            report_id="xml-789",
        )

    @patch("was_reports.reporting.report_retrieval.report_data.get_report_xml")
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_webapp_xml_report"
    )
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_detail_pdf_report"
    )
    @patch("was_reports.reporting.report_retrieval.report_data.get_tag_id")
    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_resumes_persisted_reports(
        self,
        mock_count_webapps,
        mock_get_tag_id,
        mock_create_detail_report,
        mock_create_xml_report,
        mock_get_report_xml,
    ) -> None:
        """Reuse persisted report IDs instead of submitting duplicate reports."""
        mock_count_webapps.return_value = 34
        mock_get_tag_id.return_value = "tag-123"
        mock_get_report_xml.return_value = "<WAS_WEBAPP_REPORT />"
        detail_downloader = Mock(return_value=Path("/output/TAGDetails.pdf"))
        report_waiter = Mock()
        status_recorder = Mock()

        source_data = report_retrieval.retrieve_report_source_data(
            client=self.client,
            stakeholder_tag="TAG",
            credentials=self.credentials,
            resource_root=self.resource_root,
            output_directory=self.output_directory,
            python_executable="python3",
            existing_detail_report_id="detail-existing",
            existing_xml_report_id="xml-existing",
            report_status_recorder=status_recorder,
            detail_downloader=detail_downloader,
            report_waiter=report_waiter,
        )

        self.assertEqual(source_data.xml_report_id, "xml-existing")
        mock_create_detail_report.assert_not_called()
        mock_create_xml_report.assert_not_called()
        self.assertEqual(
            detail_downloader.call_args.kwargs["report_id"],
            "detail-existing",
        )
        detail_downloader.call_args.kwargs["status_callback"]("RUNNING")
        status_recorder.assert_called_with("detail", "RUNNING")
        self.assertEqual(
            report_waiter.call_args.kwargs["report_id"],
            "xml-existing",
        )

    @patch("was_reports.reporting.report_retrieval.report_data.get_report_xml")
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_webapp_xml_report"
    )
    @patch("was_reports.reporting.report_retrieval.report_data.get_tag_id")
    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_records_new_xml_report_id(
        self,
        mock_count_webapps,
        mock_get_tag_id,
        mock_create_xml_report,
        mock_get_report_xml,
    ) -> None:
        """Persist a new Qualys report ID before polling starts."""
        mock_count_webapps.return_value = 35
        mock_get_tag_id.return_value = "tag-123"
        mock_create_xml_report.return_value = "xml-new"
        mock_get_report_xml.return_value = "<WAS_WEBAPP_REPORT />"
        report_id_recorder = Mock()

        report_retrieval.retrieve_report_source_data(
            client=self.client,
            stakeholder_tag="TAG",
            credentials=self.credentials,
            resource_root=self.resource_root,
            output_directory=self.output_directory,
            python_executable="python3",
            report_id_recorder=report_id_recorder,
            report_waiter=Mock(),
        )

        report_id_recorder.assert_called_once_with("xml", "xml-new")

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
                report_waiter=Mock(),
            )

    @patch("was_reports.reporting.report_retrieval.report_data.delete_report")
    @patch("was_reports.reporting.report_retrieval.report_data.get_report_xml")
    @patch(
        "was_reports.reporting.report_retrieval.report_data.create_webapp_xml_report"
    )
    @patch("was_reports.reporting.report_retrieval.report_data.get_tag_id")
    @patch("was_reports.reporting.report_retrieval.report_data.count_webapps")
    def test_retrieve_source_data_retains_failed_xml_download(
        self,
        mock_count_webapps,
        mock_get_tag_id,
        mock_create_xml_report,
        mock_get_report_xml,
        mock_delete_report,
    ) -> None:
        """Retain the Qualys report and saved reference when download fails."""
        mock_count_webapps.return_value = 35
        mock_get_tag_id.return_value = "tag-123"
        mock_create_xml_report.return_value = "xml-789"
        mock_get_report_xml.side_effect = RuntimeError("download failed")
        report_waiter = Mock()
        report_id_clearer = Mock()

        with self.assertRaises(RuntimeError):
            report_retrieval.retrieve_report_source_data(
                client=self.client,
                stakeholder_tag="TAG",
                credentials=self.credentials,
                resource_root=self.resource_root,
                output_directory=self.output_directory,
                python_executable="python3",
                report_id_clearer=report_id_clearer,
                report_waiter=report_waiter,
            )

        mock_delete_report.assert_not_called()
        report_id_clearer.assert_not_called()
        report_waiter.assert_called_once_with(
            client=self.client,
            report_id="xml-789",
        )

    @patch("was_reports.reporting.report_retrieval.report_data.delete_report")
    @patch("was_reports.reporting.report_retrieval.retrieve_report_source_data")
    def test_managed_source_data_retains_reference_after_processing_error(
        self,
        mock_retrieve_source_data,
        mock_delete_report,
    ) -> None:
        """Keep a reusable XML reference when downstream processing fails."""
        source_data = report_retrieval.ReportSourceData(
            stakeholder_tag="TAG",
            tag_id="tag-123",
            web_application_count=35,
            xml_report_id="xml-789",
            report_xml="<WAS_WEBAPP_REPORT />",
            detail_pdf_path=None,
        )
        mock_retrieve_source_data.return_value = source_data
        report_id_clearer = Mock()

        with self.assertRaises(RuntimeError):
            with report_retrieval.managed_report_source_data(
                client=self.client,
                stakeholder_tag="TAG",
                credentials=self.credentials,
                resource_root=self.resource_root,
                output_directory=self.output_directory,
                python_executable="python3",
                report_id_clearer=report_id_clearer,
            ):
                raise RuntimeError("transformation failed")

        mock_delete_report.assert_not_called()
        report_id_clearer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
