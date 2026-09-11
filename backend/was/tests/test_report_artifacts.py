"""Tests for WAS report attachment artifact generation."""

# Standard Python Libraries
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
from lxml import etree
from requests import Response
from requests.exceptions import HTTPError

# First-Party Libraries
from was_reports.reporting import report_artifacts

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "was_report_artifacts.xml"
SENSITIVE_RESPONSE = """<ServiceResponse><hasMoreRecords>false</hasMoreRecords><data><Finding><resultList><list>
<Result><payloads><list><PayloadInstance><response>123-45-6789</response>
<request><link>https://example.gov/sensitive</link></request>
</PayloadInstance></list></payloads></Result></list></resultList></Finding>
</data></ServiceResponse>"""
EMPTY_RESPONSE = (
    "<ServiceResponse><hasMoreRecords>false</hasMoreRecords><data /></ServiceResponse>"
)
UNSUPPORTED_MODULE_RESPONSE = """<ServiceResponse>
<responseCode>OTHER_ERROR</responseCode>
<responseErrorDetails><errorMessage>{}</errorMessage></responseErrorDetails>
</ServiceResponse>""".format(
    report_artifacts.UNSUPPORTED_MODULE_MESSAGE
)


def build_http_error(status_code: int, response_body: str) -> HTTPError:
    """Build an HTTP error containing a Qualys XML response."""
    response = Response()
    response.status_code = status_code
    response._content = response_body.encode()
    return HTTPError(response=response)


class ReportArtifactTests(unittest.TestCase):
    """Validate legacy-compatible report attachment generation."""

    def test_unsupported_module_response_does_not_expand_entities(self) -> None:
        """Do not let an XML entity turn a failure into an unavailable marker."""
        response = '<!DOCTYPE ServiceResponse [<!ENTITY probe "{}">]><ServiceResponse><responseErrorDetails><errorMessage>&probe;</errorMessage></responseErrorDetails></ServiceResponse>'.format(
            report_artifacts.UNSUPPORTED_MODULE_MESSAGE
        )
        self.assertFalse(
            report_artifacts.is_unsupported_module_error(
                build_http_error(400, response)
            )
        )

    def test_sensitive_findings_follow_pagination(self) -> None:
        """Retrieve subsequent finding pages using the last-ID cursor."""
        client = Mock()
        client.request.side_effect = [
            SENSITIVE_RESPONSE.replace("false", "true").replace(
                "<data>", "<lastId>1000</lastId><data>"
            ),
            SENSITIVE_RESPONSE,
        ]
        links, values = report_artifacts.retrieve_sensitive_findings(
            client, "CUSTOMER", report_artifacts.SSN_QIDS
        )
        self.assertEqual(len(links), 2)
        self.assertEqual(len(values), 2)
        payload = client.request.call_args.args[0].payload
        root = etree.fromstring(payload.encode())
        self.assertEqual(root.xpath("./filters/Criteria[@field='id']/text()"), ["1000"])
        self.assertEqual(
            root.xpath("./filters/Criteria[@field='id']/@operator"), ["GREATER"]
        )

    def test_sensitive_findings_reject_stalled_pagination(self) -> None:
        """Fail explicitly rather than returning incomplete or repeated findings."""
        client = Mock()
        client.request.return_value = EMPTY_RESPONSE.replace("false", "true").replace(
            "<data />", "<lastId>1000</lastId><data/>"
        )
        with self.assertRaisesRegex(ValueError, "did not advance"):
            report_artifacts.retrieve_sensitive_findings(
                client, "CUSTOMER", report_artifacts.SSN_QIDS
            )
        self.assertEqual(client.request.call_count, 2)

    def test_sensitive_findings_reject_missing_pagination_metadata(self) -> None:
        """Do not treat malformed responses as complete empty reports."""
        for metadata in (
            "",
            "<hasMoreRecords>maybe</hasMoreRecords>",
            "<hasMoreRecords>true</hasMoreRecords>",
        ):
            client = Mock()
            client.request.return_value = (
                "<ServiceResponse>{}<data/></ServiceResponse>".format(metadata)
            )
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                report_artifacts.retrieve_sensitive_findings(
                    client, "CUSTOMER", report_artifacts.SSN_QIDS
                )
            self.assertEqual(client.request.call_count, 1)

    @patch.object(report_artifacts, "MAX_SENSITIVE_FINDING_PAGES", 2)
    def test_sensitive_findings_bound_continuously_advancing_pages(self) -> None:
        """Raise rather than returning partial data from an endless feed."""
        client = Mock()
        client.request.side_effect = [
            EMPTY_RESPONSE.replace("false", "true").replace(
                "<data />", "<lastId>{}</lastId><data/>".format(cursor)
            )
            for cursor in (1000, 2000)
        ]
        with self.assertRaises(RuntimeError):
            report_artifacts.retrieve_sensitive_findings(
                client, "CUSTOMER", report_artifacts.SSN_QIDS
            )
        self.assertEqual(client.request.call_count, 2)

    def test_sensitive_attachment_preserves_multiline_cells_and_neutralizes_once(
        self,
    ) -> None:
        """Quote complete payload cells without double-prefixing formulas."""
        client = Mock()
        payload_value = '=SUM(1,2)\n"quoted"\rnext'
        root = etree.fromstring(SENSITIVE_RESPONSE.encode())
        root.find(".//response").text = payload_value
        client.request.side_effect = [etree.tostring(root).decode(), EMPTY_RESPONSE]
        with tempfile.TemporaryDirectory() as directory:
            filename = report_artifacts.write_sensitive_data_attachment(
                client, "CUSTOMER", Path(directory)
            )
            with (Path(directory) / filename).open(
                newline="", encoding="utf-8"
            ) as source:
                records = list(csv.reader(source))
        self.assertEqual(records[1][1], "'" + payload_value)
        self.assertEqual(len(records[1]), 5)

    def test_sensitive_findings_preserve_all_payload_instances(self) -> None:
        """Do not discard later payloads belonging to the same finding."""
        root = etree.fromstring(SENSITIVE_RESPONSE.encode())
        payload_list = root.find(".//payloads/list")
        payload_list.append(etree.fromstring(etree.tostring(payload_list[0])))
        links, values = report_artifacts.parse_sensitive_findings(
            etree.tostring(root).decode()
        )
        self.assertEqual(len(links), 2)
        self.assertEqual(len(values), 2)

    def test_writes_xml_derived_artifacts(self) -> None:
        """Preserve filenames, headings, totals, decoded values, and OS default."""
        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            vulnerability_filename = report_artifacts.write_vulnerabilities_by_webapp(
                FIXTURE_PATH.read_bytes(), "CUSTOMER", asset_directory
            )
            overview_filename = report_artifacts.write_application_overview(
                FIXTURE_PATH.read_bytes(), "CUSTOMER", asset_directory
            )
            links_filename = report_artifacts.write_information_attachment(
                FIXTURE_PATH.read_bytes(),
                "CUSTOMER",
                asset_directory,
                "links-crawled",
                "Links for web application",
                report_artifacts.LINKS_CRAWLED_QID,
            )
            vulnerability_text = (asset_directory / vulnerability_filename).read_text()
            overview_text = (asset_directory / overview_filename).read_text()
            links_text = (asset_directory / links_filename).read_text()

        self.assertIn("Example Application,1,2,3,4,5,15", vulnerability_text)
        self.assertIn(
            "Example Application,https://example.gov,ALL,Linux",
            overview_text,
        )
        self.assertIn(
            "No OS Application,https://no-os.example.gov,LIMITED,N/A",
            overview_text,
        )
        self.assertIn("Links for web application Example Application:", links_text)
        self.assertIn("https://example.gov/one", links_text)
        self.assertEqual(links_filename, "links-crawled-CUSTOMER.csv")

    def test_sensitive_payload_preserves_filters(self) -> None:
        """Request only active, non-false-positive findings for the customer tag."""
        payload = report_artifacts.build_sensitive_finding_payload(
            "CUSTOMER", report_artifacts.SSN_QIDS
        )

        self.assertIn("150034, 150603", payload)
        self.assertIn("CUSTOMER", payload)
        self.assertIn("ignoredReason", payload)
        self.assertIn("FALSE_POSITIVE", payload)
        self.assertIn("status", payload)
        self.assertIn("FIXED", payload)

    def test_writes_sensitive_data_artifact(self) -> None:
        """Combine the two sensitive-finding responses into the legacy CSV."""
        client = Mock()
        client.request.side_effect = [SENSITIVE_RESPONSE, EMPTY_RESPONSE]

        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            filename = report_artifacts.write_sensitive_data_attachment(
                client, "CUSTOMER", asset_directory
            )
            output_text = (asset_directory / filename).read_text()

        self.assertEqual(filename, "ssn-and-cc-found.csv")
        self.assertEqual(client.request.call_count, 2)
        self.assertIn("SSN URL,SSN FOUND,,CC URL,CREDIT CARD FOUND", output_text)
        self.assertIn("https://example.gov/sensitive,123-45-6789", output_text)
        self.assertIn("No Credit Card data found.", output_text)

    def test_sensitive_data_unsupported_module_logs_and_continues(self) -> None:
        """Mark unavailable data and continue for the known Qualys response."""
        client = Mock()
        client.request.side_effect = [
            build_http_error(400, UNSUPPORTED_MODULE_RESPONSE),
            build_http_error(400, UNSUPPORTED_MODULE_RESPONSE),
        ]

        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            with self.assertLogs(report_artifacts.LOGGER, level="WARNING") as logs:
                filename = report_artifacts.write_sensitive_data_attachment(
                    client,
                    "CUSTOMER",
                    asset_directory,
                )
            output_text = (asset_directory / filename).read_text()

        self.assertEqual(client.request.call_count, 2)
        self.assertEqual(len(logs.output), 2)
        self.assertIn("SSN data unavailable from Qualys.", output_text)
        self.assertIn("Credit Card data unavailable from Qualys.", output_text)

    def test_sensitive_data_unsupported_module_continues_after_server_error(
        self,
    ) -> None:
        """Recognize the exact unsupported-module response from a server error."""
        client = Mock()
        client.request.side_effect = [
            build_http_error(500, UNSUPPORTED_MODULE_RESPONSE),
            EMPTY_RESPONSE,
        ]

        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            with self.assertLogs(report_artifacts.LOGGER, level="WARNING"):
                filename = report_artifacts.write_sensitive_data_attachment(
                    client,
                    "CUSTOMER",
                    asset_directory,
                )
            output_text = (asset_directory / filename).read_text()

        self.assertIn("SSN data unavailable from Qualys.", output_text)
        self.assertIn("No Credit Card data found.", output_text)

    def test_sensitive_data_unexpected_http_error_is_raised(self) -> None:
        """Do not suppress Qualys errors outside the approved fallback."""
        client = Mock()
        client.request.side_effect = build_http_error(
            500,
            "<ServiceResponse><responseErrorDetails><errorMessage>"
            "Unexpected Qualys failure."
            "</errorMessage></responseErrorDetails></ServiceResponse>",
        )

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(HTTPError):
                report_artifacts.write_sensitive_data_attachment(
                    client,
                    "CUSTOMER",
                    Path(directory),
                )

    def test_generate_report_artifacts_returns_all_filenames(self) -> None:
        """Create every active attachment through one orchestration call."""
        client = Mock()
        client.request.side_effect = [EMPTY_RESPONSE, EMPTY_RESPONSE]

        with tempfile.TemporaryDirectory() as directory:
            result = report_artifacts.generate_report_artifacts(
                FIXTURE_PATH.read_bytes(), "CUSTOMER", Path(directory), client
            )

        self.assertEqual(
            result,
            report_artifacts.ReportArtifactResult(
                vulnerabilities_by_webapp="vulns-by-webapp-CUSTOMER.csv",
                application_overview="webapp-overview-CUSTOMER.csv",
                links_crawled="links-crawled-CUSTOMER.csv",
                emails_found="emails-found-CUSTOMER.csv",
                rejected_links="rejected-links-CUSTOMER.csv",
                sensitive_data="ssn-and-cc-found.csv",
            ),
        )


if __name__ == "__main__":
    unittest.main()
