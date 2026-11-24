"""Tests for bounded-memory Qualys report XML processing."""

# Standard Python Libraries
import csv
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
from was_reports.reporting.exceptions import ReportXmlUnsafeContentError

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures"
CURRENT_TIME = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)


def _append_child_xml(parent, xml_text: str) -> None:
    """Append one test-only XML fragment to an element."""
    parent.append(etree.fromstring(xml_text.encode("utf-8")))


def _write_complete_report(path: Path) -> None:
    """Build one fixture containing every report section used in production."""
    root = etree.fromstring((FIXTURE_DIRECTORY / "was_report_sample.xml").read_bytes())
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
    information_list = root.find("./RESULTS/WEB_APPLICATION/INFORMATION_GATHERED_LIST")
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
            "<DATA>{}</DATA></INFORMATION_GATHERED>".format(suffix, qid, encoded_data),
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


def _write_flat_report(path: Path) -> None:
    """Write findings under RESULTS with two applications in the appendix."""
    _write_complete_report(path)
    root = etree.fromstring(path.read_bytes())
    results = root.find("RESULTS")
    application = results.find("WEB_APPLICATION")
    vulnerabilities = application.find("VULNERABILITY_LIST")
    information = application.find("INFORMATION_GATHERED_LIST")
    vulnerabilities[0].find("STATUS").text = "New"
    vulnerabilities[1].find("STATUS").text = "Fixed"
    active = etree.fromstring(etree.tostring(vulnerabilities[0]))
    active.find("STATUS").text = "Active"
    vulnerabilities.append(active)
    second_link = etree.fromstring(etree.tostring(information[1]))
    information.append(second_link)
    results.extend([vulnerabilities, information])
    results.remove(application)
    for number, finding in enumerate([*vulnerabilities, *information], start=1):
        finding.find("ID").text = str(number)
    path.write_bytes(etree.tostring(root))


def _flat_finding_response(
    *, omit_last: bool = False, wrong_qid: bool = False, outside_report: bool = False
) -> str:
    """Return findings with ownership supplied by the Qualys search endpoint."""
    first_application = ("Example Application", "https://example.gov")
    second_application = ("No OS Application", "https://no-os.example.gov")
    if outside_report:
        second_application = (second_application[0], "https://unrelated.example.gov")
    applications = [
        first_application,
        first_application,
        second_application,
        second_application,
        first_application,
        first_application,
        first_application,
        second_application,
    ]
    qids = ["9999" if wrong_qid else "1001", "1001", "1001", "1002"]
    qids.extend(["150009", "150054", "150041", "150009"])
    response = etree.Element("ServiceResponse")
    etree.SubElement(response, "responseCode").text = "SUCCESS"
    etree.SubElement(response, "hasMoreRecords").text = "false"
    data = etree.SubElement(response, "data")
    for number, (qid, (name, url)) in enumerate(zip(qids, applications), start=1):
        if omit_last and number == len(qids):
            break
        finding = etree.SubElement(data, "Finding")
        etree.SubElement(finding, "id").text = str(number)
        etree.SubElement(finding, "qid").text = qid
        etree.SubElement(finding, "type").text = (
            "VULNERABILITY" if number <= 3 else "INFORMATION_GATHERED"
        )
        web_app = etree.SubElement(finding, "webApp")
        etree.SubElement(web_app, "name").text = name
        etree.SubElement(web_app, "url").text = url
    return etree.tostring(response, encoding="unicode")


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

            with patch.object(
                etree, "iterparse", side_effect=recording_iterparse
            ), patch.object(
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

    @patch.object(streaming_report, "write_sensitive_data_attachment")
    def test_flat_report_uses_verified_owners_and_normalizes_statuses(
        self, unused_sensitive_writer
    ) -> None:
        """Place flat findings and links under their verified applications."""
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "flat.xml"
            assets = base_directory / "assets"
            _write_flat_report(xml_path)
            client = Mock()
            client.request.return_value = _flat_finding_response()
            result = streaming_report.process_report_xml(
                xml_path, "CUSTOMER", assets, client, CURRENT_TIME
            )
            client.request.assert_called_once()
            request = client.request.call_args.args[0]
            self.assertEqual(request.endpoint, "/search/was/finding")
            filters = etree.fromstring(request.payload.encode()).find("filters")
            self.assertEqual(
                filters.findtext("Criteria[@field='webApp.tags.name']"), "CUSTOMER"
            )
            self.assertEqual(
                filters.findtext("Criteria[@field='id']"), "1, 2, 3, 4, 5, 6, 7, 8"
            )
            self.assertEqual(result.finding_metrics.new_count, 1)
            self.assertEqual(result.finding_metrics.fixed_count, 1)
            self.assertEqual(result.finding_metrics.active_count, 1)
            with (assets / result.transformation.vulnerability_filename).open() as file:
                vulnerability_rows = list(csv.reader(file))[1:]
            self.assertEqual(
                [(row[0], row[10]) for row in vulnerability_rows],
                [("1", "Example Application"), ("3", "No OS Application")],
            )
            with (assets / result.transformation.information_filename).open() as file:
                information_rows = list(csv.reader(file))[1:]
            self.assertEqual(
                [row[3] for row in information_rows],
                [
                    "No OS Application",
                    *(["Example Application"] * 3),
                    "No OS Application",
                ],
            )
            self.assertEqual(
                (assets / result.artifacts.links_crawled).read_text().splitlines(),
                [
                    "",
                    "Links for web application Example Application:",
                    "https://example.gov/one",
                    "",
                    "Links for web application No OS Application:",
                    "https://example.gov/one",
                ],
            )

    def test_flat_report_rejects_unverified_attribution(self) -> None:
        """Fail on missing IDs, mismatched identities, or out-of-report owners."""
        responses = (
            (_flat_finding_response(omit_last=True), "every flat report finding"),
            (_flat_finding_response(wrong_qid=True), "conflicting finding ownership"),
            (
                _flat_finding_response(outside_report=True),
                "does not match the appendix",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "flat.xml"
            _write_flat_report(xml_path)
            for response, error_message in responses:
                with self.subTest(error_message=error_message):
                    client = Mock()
                    client.request.return_value = response
                    with self.assertRaisesRegex(LookupError, error_message):
                        streaming_report.process_report_xml(
                            xml_path,
                            "CUSTOMER",
                            base_directory / "assets",
                            client,
                            CURRENT_TIME,
                        )

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

    def test_process_report_rejects_actual_document_doctype(self) -> None:
        """Reject a real document DTD before processing report content."""
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "report.xml"
            _write_complete_report(xml_path)
            root = etree.fromstring(xml_path.read_bytes())
            root.insert(0, etree.Entity("probe"))
            xml_path.write_bytes(
                etree.tostring(
                    root,
                    xml_declaration=True,
                    encoding="UTF-8",
                    doctype=(
                        "<!DOCTYPE WAS_WEBAPP_REPORT "
                        '[<!ENTITY probe "EXPANSION_SENTINEL">]>'
                    ),
                )
            )

            with self.assertRaisesRegex(
                ReportXmlUnsafeContentError,
                "prohibited DTD declaration",
            ):
                streaming_report.process_report_xml(
                    xml_path,
                    "CUSTOMER",
                    base_directory / "assets",
                    Mock(),
                    CURRENT_TIME,
                )

    def test_process_report_accepts_literal_declarations_in_cdata_and_comment(
        self,
    ) -> None:
        """Treat declaration-like CDATA and comments as inert literal text."""
        with tempfile.TemporaryDirectory() as directory:
            base_directory = Path(directory)
            xml_path = base_directory / "report.xml"
            _write_complete_report(xml_path)
            root = etree.fromstring(xml_path.read_bytes())
            literal_text = (
                '<!DOCTYPE literal [<!ENTITY probe "EXPANSION_SENTINEL">]>' "&probe;"
            )
            root.text = etree.CDATA(literal_text)
            root.insert(0, etree.Comment("<!DOCTYPE comment> <!ENTITY comment>"))
            xml_path.write_bytes(
                etree.tostring(root, xml_declaration=True, encoding="UTF-8")
            )

            with xml_path.open("rb") as xml_file:
                parsed_root = None
                for event, element in streaming_report._iter_report(xml_file):
                    if event == "start" and parsed_root is None:
                        parsed_root = element
                self.assertIsNotNone(parsed_root)
                assert parsed_root is not None
                self.assertEqual(parsed_root.text, literal_text)

            result = streaming_report.process_report_xml(
                xml_path,
                "CUSTOMER",
                base_directory / "assets",
                Mock(),
                CURRENT_TIME,
            )
            self.assertEqual(
                result.transformation.vulnerability_filename,
                "vulnerability-list-CUSTOMER.csv",
            )


if __name__ == "__main__":
    unittest.main()
