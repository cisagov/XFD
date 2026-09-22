"""Tests for Qualys WAS XML transformation artifacts."""

# Standard Python Libraries
import csv
from datetime import datetime, timezone
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# Third-Party Libraries
from lxml import etree

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

        self.assertEqual(
            result.vulnerability_filename, "vulnerability-list-CUSTOMER.csv"
        )
        self.assertEqual(
            result.information_filename,
            "information-gathered-listCUSTOMER.csv",
        )
        self.assertEqual(result.severities, ["4"])
        self.assertEqual(result.ages, [26])
        self.assertIn(report_transformer.VULNERABILITY_HEADER, vulnerability_text)
        self.assertIn('vuln-1,"Test, Vulnerability",1001,4', vulnerability_text)
        self.assertNotIn("vuln-fixed", vulnerability_text)
        self.assertIn('"Example, Application"', information_text)

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
        self.assertIn("Response, body", vulnerability_text)
        self.assertIn(",Confirmed\n", vulnerability_text)

    def test_parse_qid_definitions_uses_legacy_optional_defaults(self) -> None:
        """Use legacy defaults for optional glossary metadata."""
        report = report_transformer.parse_report(FIXTURE_PATH.read_bytes())

        definitions = report_transformer.parse_qid_definitions(report)

        self.assertEqual(definitions["1002"].group, "")
        self.assertEqual(definitions["1002"].cvss, "None")
        self.assertEqual(definitions["1002"].cve, "None")
        self.assertEqual(definitions["1002"].cwe, "None")

    def test_csv_round_trip_preserves_special_characters(self) -> None:
        """Keep commas, quotes, and line breaks inside their original cell."""
        values = ["first, second", 'a"quote', "line\nnext", "carriage\rreturn"]
        serialized = report_transformer.csv_row(values)
        self.assertEqual(next(csv.reader(io.StringIO(serialized, newline=""))), values)

    def test_csv_neutralizes_formula_prefixes(self) -> None:
        """Neutralize formulas including whitespace-prefixed spreadsheet input."""
        for value in (
            "=1+1",
            "+SUM(1)",
            "-1+2",
            "@SUM(1)",
            "  =1",
            "\ttext",
            "\rtext",
            "\ntext",
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    report_transformer.spreadsheet_safe_field(value), "'" + value
                )

    def test_formula_neutralization_is_idempotent(self) -> None:
        """Avoid adding duplicate apostrophes to already-neutralized cells."""
        for value in ("=1+1", " -1", "'@SUM(1)", "'plain", "plain"):
            with self.subTest(value=value):
                safe_value = report_transformer.spreadsheet_safe_field(value)
                self.assertEqual(
                    report_transformer.spreadsheet_safe_field(safe_value), safe_value
                )

    def test_csv_serialization_does_not_mutate_report_source(self) -> None:
        """Keep formula defenses out of the XML consumed by PDF metrics."""
        report = report_transformer.parse_report(FIXTURE_PATH.read_bytes())
        report.RESULTS.WEB_APPLICATION.NAME = "=Research, Organization"
        with tempfile.TemporaryDirectory() as directory:
            result = report_transformer.transform_report_to_csv(
                report, "CUSTOMER", Path(directory)
            )
            with (Path(directory) / result.information_filename).open(
                newline="", encoding="utf-8"
            ) as source:
                records = list(csv.reader(source))
        self.assertEqual(records[1][3], "'=Research, Organization")
        self.assertEqual(
            str(report.RESULTS.WEB_APPLICATION.NAME), "=Research, Organization"
        )

    def test_parse_qid_definitions_rejects_missing_glossary(self) -> None:
        """Report the no-findings condition without creating a PDF side effect."""
        report = report_transformer.parse_report(
            "<WAS_WEBAPP_REPORT><RESULTS /></WAS_WEBAPP_REPORT>"
        )

        with self.assertRaises(LookupError):
            report_transformer.parse_qid_definitions(report)

    def test_parse_report_accepts_qualys_text_node_above_default_limit(self) -> None:
        """Parse a Qualys report containing a text node larger than 10 MB."""
        oversized_text = b"A" * 10_000_001
        report_xml = b"<WAS_WEBAPP_REPORT><PAYLOAD>" + oversized_text + (
            b"</PAYLOAD></WAS_WEBAPP_REPORT>"
        )

        report = report_transformer.parse_report(report_xml)

        self.assertEqual(len(str(report.PAYLOAD)), len(oversized_text))

    def test_parse_report_does_not_expand_entities(self) -> None:
        """Keep internal and network entities unresolved with large-tree parsing."""
        report_xml = b"""<!DOCTYPE WAS_WEBAPP_REPORT [
        <!ENTITY internal "sensitive-value">
        <!ENTITY external SYSTEM "http://127.0.0.1:9/sensitive-value">
        ]>
        <WAS_WEBAPP_REPORT>
          <INTERNAL>&internal;</INTERNAL>
          <EXTERNAL>&external;</EXTERNAL>
        </WAS_WEBAPP_REPORT>
        """

        report = report_transformer.parse_report(report_xml)
        serialized_report = etree.tostring(report)

        self.assertIn(b"&internal;", serialized_report)
        self.assertIn(b"&external;", serialized_report)
        self.assertNotIn(b"sensitive-value</INTERNAL>", serialized_report)

    def test_parse_report_rejects_document_above_safety_limit(self) -> None:
        """Bound memory use even when large-tree parsing is required."""
        with patch.object(report_transformer, "MAX_REPORT_XML_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "exceeds the 10 byte safety limit"):
                report_transformer.parse_report(b"<REPORT>large</REPORT>")


if __name__ == "__main__":
    unittest.main()
