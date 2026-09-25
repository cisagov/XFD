"""Tests for bounded-memory Qualys report XML processing."""

# Standard Python Libraries
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.reporting import (
    report_artifacts,
    report_metrics,
    report_transformer,
    streaming_report,
)

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures"
CURRENT_TIME = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)


def _append_child_xml(parent, xml_text: str) -> None:
    """Append one test-only XML fragment to an element."""
    parent.append(etree.fromstring(xml_text.encode("utf-8")))


def _write_complete_report(path: Path) -> None:
    """Build one fixture containing every report section used in production."""
    root = etree.fromstring(
        (FIXTURE_DIRECTORY / "was_report_sample.xml").read_bytes()
    )
    metrics_root = etree.fromstring(
        (FIXTURE_DIRECTORY / "was_report_metrics.xml").read_bytes()
    )
    artifacts_root = etree.fromstring(
        (FIXTURE_DIRECTORY / "was_report_artifacts.xml").read_bytes()
    )
    root.insert(0, metrics_root.find("HEADER"))
    root.insert(1, metrics_root.find("SUMMARY"))
    root.append(artifacts_root.find("APPENDIX"))

    first_definition = root.find("./GLOSSARY/QID_LIST/QID")
    _append_child_xml(first_definition, "<OWASP>A3</OWASP>")
    information_list = root.find(
        "./RESULTS/WEB_APPLICATION/INFORMATION_GATHERED_LIST"
    )
    information_values = (
        ("150009", "links", "aHR0cHM6Ly9leGFtcGxlLmdvdi9vbmU="),
        ("150054", "emails", "dXNlckBleGFtcGxlLmdvdg=="),
        ("150041", "rejected", "aHR0cHM6Ly9leGFtcGxlLmdvdi9yZWplY3RlZA=="),
    )
    glossary = root.find("./GLOSSARY/QID_LIST")
    for qid, suffix, encoded_data in information_values:
        _append_child_xml(
            information_list,
            "<INFORMATION_GATHERED>"
            "<ID>info-{}</ID><QID>{}</QID>"
            "<LAST_TIME_DETECTED>26 Aug 2026 01:00PM UTC</LAST_TIME_DETECTED>"
            "<DATA>{}</DATA></INFORMATION_GATHERED>".format(
                suffix, qid, encoded_data
            ),
        )
        _append_child_xml(
            glossary,
            "<QID><QID>{}</QID><SEVERITY>1</SEVERITY>"
            "<TITLE>{}</TITLE><DESCRIPTION>description</DESCRIPTION>"
            "<IMPACT>impact</IMPACT><SOLUTION>solution</SOLUTION></QID>".format(
                qid, suffix
            ),
        )
    path.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8"))


class StreamingReportTests(unittest.TestCase):
    """Validate streaming results against the established in-memory pipeline."""

    def test_process_report_matches_existing_outputs_and_metrics(self) -> None:
        """Preserve all legacy outputs while parsing the source only twice."""
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "report.xml"
            expected_directory = base_directory / "expected"
            actual_directory = base_directory / "actual"
            expected_directory.mkdir()
            _write_complete_report(xml_path)
            report_bytes = xml_path.read_bytes()
            client = Mock()

            expected_transformation = report_transformer.transform_report_to_csv(
                report_bytes,
                "CUSTOMER",
                expected_directory,
                CURRENT_TIME,
            )
            expected_findings = report_metrics.calculate_finding_metrics(
                report_bytes, CURRENT_TIME
            )
            expected_summary = report_metrics.calculate_summary_metrics(report_bytes)
            expected_totals = report_metrics.calculate_severity_totals(report_bytes)
            expected_artifacts = report_artifacts.generate_report_artifacts(
                report_bytes,
                "CUSTOMER",
                expected_directory,
                client,
            )

            with patch.object(
                streaming_report,
                "_iter_report",
                wraps=streaming_report._iter_report,
            ) as iter_report:
                actual = streaming_report.process_report_xml(
                    xml_path,
                    "CUSTOMER",
                    actual_directory,
                    client,
                    CURRENT_TIME,
                )

            self.assertEqual(iter_report.call_count, 2)
            self.assertEqual(actual.transformation, expected_transformation)
            self.assertEqual(actual.finding_metrics, expected_findings)
            self.assertEqual(actual.summary_metrics, expected_summary)
            self.assertEqual(actual.severity_totals, expected_totals)
            self.assertEqual(actual.artifacts, expected_artifacts)
            expected_files = sorted(path.name for path in expected_directory.iterdir())
            self.assertEqual(
                sorted(path.name for path in actual_directory.iterdir()),
                expected_files,
            )
            for filename in expected_files:
                self.assertEqual(
                    (actual_directory / filename).read_bytes(),
                    (expected_directory / filename).read_bytes(),
                    filename,
                )

    def test_process_report_uses_secure_iterparse_without_reading_whole_file(
        self,
    ) -> None:
        """Disable entity expansion and avoid Path whole-file read helpers."""
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "report.xml"
            _write_complete_report(xml_path)
            real_iterparse = etree.iterparse
            calls = []

            def recording_iterparse(*args, **kwargs):
                calls.append(kwargs)
                return real_iterparse(*args, **kwargs)

            with patch.object(etree, "iterparse", side_effect=recording_iterparse), patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("whole-file read is not allowed"),
            ):
                streaming_report.process_report_xml(
                    xml_path,
                    "CUSTOMER",
                    base_directory / "assets",
                    Mock(),
                    CURRENT_TIME,
                )

        self.assertEqual(len(calls), 2)
        for arguments in calls:
            self.assertFalse(arguments["resolve_entities"])
            self.assertTrue(arguments["no_network"])
            self.assertFalse(arguments["load_dtd"])
            self.assertFalse(arguments["dtd_validation"])
            self.assertFalse(arguments["attribute_defaults"])
            self.assertTrue(arguments["huge_tree"])

    def test_process_report_rejects_unexpected_root(self) -> None:
        """Reject a valid XML document that is not a Qualys WAS report."""
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "report.xml"
            xml_path.write_text("<UNEXPECTED />", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unexpected root"):
                streaming_report.process_report_xml(
                    xml_path,
                    "CUSTOMER",
                    base_directory / "assets",
                    Mock(),
                    CURRENT_TIME,
                )


if __name__ == "__main__":
    unittest.main()
