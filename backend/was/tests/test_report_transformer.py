"""Tests for Qualys WAS XML transformation artifacts."""

# Standard Python Libraries
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

# First-Party Libraries
from was_reports.reporting import report_transformer

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "was_report_sample.xml"


class ReportTransformerTests(unittest.TestCase):
    """Validate legacy-compatible CSV transformation behavior."""

    def test_transform_report_creates_expected_artifacts(self) -> None:
        """Create both CSV files and preserve graph input values."""
        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            result = report_transformer.transform_report_to_csv(
                report_xml=FIXTURE_PATH.read_bytes(),
                stakeholder_tag="CUSTOMER",
                asset_directory=asset_directory,
                current_time=datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc),
            )
            vulnerability_text = (
                asset_directory / result.vulnerability_filename
            ).read_text(encoding="utf-8")
            information_text = (
                asset_directory / result.information_filename
            ).read_text(encoding="utf-8")

        self.assertEqual(result.vulnerability_filename, "vulnerability-list-CUSTOMER.csv")
        self.assertEqual(
            result.information_filename,
            "information-gathered-listCUSTOMER.csv",
        )
        self.assertEqual(result.severities, ["4"])
        self.assertEqual(result.ages, [26])
        self.assertIn(report_transformer.VULNERABILITY_HEADER, vulnerability_text)
        self.assertIn("vuln-1,Test Vulnerability,1001,4", vulnerability_text)
        self.assertNotIn("vuln-fixed", vulnerability_text)
        self.assertIn("Example Application", information_text)

    def test_transform_report_preserves_payload_formatting(self) -> None:
        """Preserve request quoting and decoded byte-string response output."""
        with tempfile.TemporaryDirectory() as directory:
            asset_directory = Path(directory)
            result = report_transformer.transform_report_to_csv(
                report_xml=FIXTURE_PATH.read_bytes(),
                stakeholder_tag="CUSTOMER",
                asset_directory=asset_directory,
                current_time=datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc),
            )
            vulnerability_text = (
                asset_directory / result.vulnerability_filename
            ).read_text(encoding="utf-8")

        self.assertIn('"GET https://example.gov/path,one', vulnerability_text)
        self.assertIn("b'Response body'", vulnerability_text)
        self.assertIn(",Confirmed\n", vulnerability_text)

    def test_parse_qid_definitions_uses_legacy_optional_defaults(self) -> None:
        """Use legacy defaults for optional glossary metadata."""
        report = report_transformer.parse_report(FIXTURE_PATH.read_bytes())

        definitions = report_transformer.parse_qid_definitions(report)

        self.assertEqual(definitions["1002"].group, "")
        self.assertEqual(definitions["1002"].cvss, "None")
        self.assertEqual(definitions["1002"].cve, "None")
        self.assertEqual(definitions["1002"].cwe, "None")

    def test_parse_qid_definitions_rejects_missing_glossary(self) -> None:
        """Report the no-findings condition without creating a PDF side effect."""
        report = report_transformer.parse_report(
            "<WAS_WEBAPP_REPORT><RESULTS /></WAS_WEBAPP_REPORT>"
        )

        with self.assertRaises(LookupError):
            report_transformer.parse_qid_definitions(report)


if __name__ == "__main__":
    unittest.main()
