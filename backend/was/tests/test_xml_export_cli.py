"""Tests for the WAS XML export command."""

# Standard Python Libraries
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.commands import xml_export_cli

REPORT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<WAS_WEBAPP_REPORT>
  <HEADER>
    <COMPANY_INFO><NAME>Qualys Account</NAME></COMPANY_INFO>
    <USER_INFO><NAME>Operator</NAME></USER_INFO>
    <GENERATION_DATETIME>2026-08-26</GENERATION_DATETIME>
  </HEADER>
  <RESULTS />
</WAS_WEBAPP_REPORT>
"""


class XmlExportCliTests(unittest.TestCase):
    """Validate sanitized XML export behavior and CLI handling."""

    def setUp(self) -> None:
        """Isolate shared polling from external Qualys calls."""
        polling = patch(
            "was_reports.commands.xml_export_cli.wait_for_report_completion"
        )
        self.mock_poll = polling.start()
        self.addCleanup(polling.stop)

    def test_sanitize_report_xml_removes_account_metadata(self) -> None:
        """Remove company and user details while preserving report content."""
        sanitized_xml = xml_export_cli.sanitize_report_xml(REPORT_XML)
        root = etree.fromstring(sanitized_xml)

        self.assertIsNone(root.find("./HEADER/COMPANY_INFO"))
        self.assertIsNone(root.find("./HEADER/USER_INFO"))
        self.assertIsNotNone(root.find("./HEADER/GENERATION_DATETIME"))

    @patch("was_reports.commands.xml_export_cli.delete_report")
    @patch("was_reports.commands.xml_export_cli.get_report_xml")
    @patch(
        "was_reports.commands.xml_export_cli.create_webapp_xml_report",
        return_value="456",
    )
    @patch("was_reports.commands.xml_export_cli.get_tag_id", return_value="123")
    def test_poll_failure_prevents_download_and_preserves_primary_error(
        self,
        mock_tag,
        mock_create,
        mock_download,
        mock_delete,
    ) -> None:
        """Never download unfinished reports or mask polling errors with cleanup."""
        self.mock_poll.side_effect = TimeoutError("poll deadline")
        mock_delete.side_effect = RuntimeError("cleanup failed")
        with self.assertRaisesRegex(TimeoutError, "poll deadline"):
            xml_export_cli.export_xml_report(
                Mock(), "CUSTOMER", Path("template.xml"), Path("unused.xml")
            )
        mock_download.assert_not_called()
        mock_delete.assert_called_once()

    @patch("was_reports.commands.xml_export_cli.delete_report")
    @patch(
        "was_reports.commands.xml_export_cli.get_report_xml", return_value=REPORT_XML
    )
    @patch(
        "was_reports.commands.xml_export_cli.create_webapp_xml_report",
        return_value="456",
    )
    @patch("was_reports.commands.xml_export_cli.get_tag_id", return_value="123")
    def test_each_export_has_a_unique_name_and_waits_before_download(
        self,
        mock_tag,
        mock_create,
        mock_download,
        mock_delete,
    ) -> None:
        """Keep concurrent same-stakeholder requests distinct and ordered."""
        order = Mock()
        order.attach_mock(self.mock_poll, "poll")
        order.attach_mock(mock_download, "download")
        with tempfile.TemporaryDirectory() as directory:
            for unused_index in range(2):
                xml_export_cli.export_xml_report(
                    Mock(),
                    "CUSTOMER",
                    Path("template.xml"),
                    Path(directory) / "report.xml",
                )
        names = [call.kwargs["report_name"] for call in mock_create.call_args_list]
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(
            [call[0] for call in order.mock_calls],
            ["poll", "download", "poll", "download"],
        )

    def test_resolve_output_path_adds_xml_extension(self) -> None:
        """Add the XML extension when an operator omits it."""
        output_path = xml_export_cli.resolve_output_path(
            Path("/output"),
            "CUSTOMER_report",
        )

        self.assertEqual(output_path, Path("/output/CUSTOMER_report.xml"))

    def test_resolve_output_path_rejects_directory_components(self) -> None:
        """Prevent filenames from escaping the configured output directory."""
        with self.assertRaises(ValueError):
            xml_export_cli.resolve_output_path(Path("/output"), "../report.xml")

    @patch("was_reports.commands.xml_export_cli.delete_report")
    @patch("was_reports.commands.xml_export_cli.get_report_xml")
    @patch("was_reports.commands.xml_export_cli.create_webapp_xml_report")
    @patch("was_reports.commands.xml_export_cli.get_tag_id")
    def test_export_xml_report_writes_output_and_deletes_temporary_report(
        self,
        mock_get_tag_id,
        mock_create_report,
        mock_get_report,
        mock_delete_report,
    ) -> None:
        """Write sanitized XML and remove the temporary Qualys report."""
        mock_get_tag_id.return_value = "123"
        mock_create_report.return_value = "456"
        mock_get_report.return_value = REPORT_XML
        mock_delete_report.return_value = True

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "CUSTOMER_report.xml"
            result = xml_export_cli.export_xml_report(
                client=Mock(),
                stakeholder_tag="CUSTOMER",
                template_path=Path("/templates/was_report.xml"),
                output_path=output_path,
            )
            exported_xml = output_path.read_text(encoding="utf-8")

        self.assertEqual(result, output_path)
        self.assertNotIn("COMPANY_INFO", exported_xml)
        self.assertNotIn("USER_INFO", exported_xml)
        mock_delete_report.assert_called_once_with(unittest.mock.ANY, "456")
        self.mock_poll.assert_called_once_with(unittest.mock.ANY, "456")
        self.assertTrue(
            mock_create_report.call_args.kwargs["report_name"].startswith(
                "CUSTOMER_xml_"
            )
        )

    @patch("was_reports.commands.xml_export_cli.delete_report")
    @patch("was_reports.commands.xml_export_cli.get_report_xml")
    @patch("was_reports.commands.xml_export_cli.create_webapp_xml_report")
    @patch("was_reports.commands.xml_export_cli.get_tag_id")
    def test_export_xml_report_cleans_up_after_download_failure(
        self,
        mock_get_tag_id,
        mock_create_report,
        mock_get_report,
        mock_delete_report,
    ) -> None:
        """Delete the temporary Qualys report when its download fails."""
        mock_get_tag_id.return_value = "123"
        mock_create_report.return_value = "456"
        mock_get_report.side_effect = RuntimeError("download failed")

        with self.assertRaises(RuntimeError):
            xml_export_cli.export_xml_report(
                client=Mock(),
                stakeholder_tag="CUSTOMER",
                template_path=Path("/templates/was_report.xml"),
                output_path=Path("/output/CUSTOMER_report.xml"),
            )

        mock_delete_report.assert_called_once_with(unittest.mock.ANY, "456")


if __name__ == "__main__":
    unittest.main()
