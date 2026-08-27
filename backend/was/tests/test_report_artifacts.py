"""Tests for WAS report attachment artifact generation."""

# Standard Python Libraries
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

# First-Party Libraries
from was_reports import report_artifacts

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "was_report_artifacts.xml"
SENSITIVE_RESPONSE = """<ServiceResponse><data><Finding><resultList><list>
<Result><payloads><list><PayloadInstance><response>123-45-6789</response>
<request><link>https://example.gov/sensitive</link></request>
</PayloadInstance></list></payloads></Result></list></resultList></Finding>
</data></ServiceResponse>"""
EMPTY_RESPONSE = "<ServiceResponse><data /></ServiceResponse>"


class ReportArtifactTests(unittest.TestCase):
    """Validate legacy-compatible report attachment generation."""

    def test_writes_xml_derived_artifacts(self) -> None:
        """Preserve filenames, headings, totals, decoded values, and OS default."""
        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            vulnerability_filename = (
                report_artifacts.write_vulnerabilities_by_webapp(
                    FIXTURE_PATH.read_bytes(), "CUSTOMER", asset_directory
                )
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
            vulnerability_text = (
                asset_directory / vulnerability_filename
            ).read_text()
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
