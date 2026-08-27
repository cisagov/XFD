"""Tests for the legacy WAS Mustache template-data contract."""

# Standard Python Libraries
import unittest
from datetime import datetime
from pathlib import Path

# First-Party Libraries
from was_reports.reporting import report_template_data
from was_reports.reporting.report_artifacts import ReportArtifactResult

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "was_report_metrics.xml"
TEMPLATE_PATH = Path(__file__).parents[1] / "was_report" / "NEW_BIG.mustache"
CURRENT_TIME = datetime(2026, 8, 27, 13, 0)


class ReportTemplateDataTests(unittest.TestCase):
    """Validate assembly of every field consumed by NEW_BIG.mustache."""

    def setUp(self) -> None:
        """Create representative legacy artifact inputs."""
        generated_artifacts = ReportArtifactResult(
            vulnerabilities_by_webapp="vulns-by-webapp-CUSTOMER.csv",
            application_overview="webapp-overview-CUSTOMER.csv",
            links_crawled="links-crawled-CUSTOMER.csv",
            emails_found="emails-found-CUSTOMER.csv",
            rejected_links="rejected-links-CUSTOMER.csv",
            sensitive_data="ssn-and-cc-found.csv",
        )
        self.artifacts = report_template_data.TemplateArtifactInputs(
            vulnerability_details="vulnerability-list-CUSTOMER.csv",
            information_details="information-gathered-listCUSTOMER.csv",
            generated=generated_artifacts,
            detail_pdf="CUSTOMERDetails.pdf",
        )

    def build_data(self, web_application_count: int = 2):
        """Build template data using the representative fixture."""
        return report_template_data.build_template_data(
            report_xml=FIXTURE_PATH.read_bytes(),
            stakeholder_tag="CUSTOMER",
            organization_name="CISA & Partner",
            artifacts=self.artifacts,
            finding_ages=report_template_data.FindingAgeInputs(
                critical_days=10,
                urgent_days=0,
            ),
            web_application_count=web_application_count,
            current_time=CURRENT_TIME,
        )

    def test_builds_complete_template_contract(self) -> None:
        """Supply every placeholder required by the preserved template."""
        template_data = self.build_data()

        self.assertFalse(
            report_template_data.REQUIRED_TEMPLATE_FIELDS.difference(
                template_data
            )
        )
        self.assertEqual(template_data["OrgName"], "CISA \\& Partner")
        self.assertEqual(template_data["StartDate"], "26 Aug 2026")
        self.assertEqual(template_data["SecurityRisk"], "High")
        self.assertEqual(template_data["RiskColor"], "CB0000")
        self.assertEqual(template_data["lev1"], "6")
        self.assertEqual(template_data["lev5"], "6")

    def test_required_fields_match_preserved_template(self) -> None:
        """Detect placeholder additions or removals in the preserved template."""
        template_fields = report_template_data.find_template_fields(
            TEMPLATE_PATH.read_text(encoding="utf-8")
        )

        self.assertEqual(
            template_fields,
            report_template_data.REQUIRED_TEMPLATE_FIELDS,
        )

    def test_preserves_finding_counts_groups_and_colors(self) -> None:
        """Map extracted metrics to their legacy Mustache field names."""
        template_data = self.build_data()

        self.assertEqual(template_data["PathDisc"], "1")
        self.assertEqual(template_data["InfoDisc"], "1")
        self.assertEqual(template_data["SqlInj"], "1")
        self.assertEqual(template_data["NewVulns"], "1")
        self.assertEqual(template_data["Reopened"], "1")
        self.assertEqual(template_data["TotVulns"], "1")
        self.assertEqual(template_data["TotVulnsColor"], "c41230")

    def test_preserves_report_card_age_positions(self) -> None:
        """Place critical and urgent ages in the legacy coordinate fields."""
        template_data = self.build_data()

        self.assertEqual(template_data["maxurg"], "10")
        self.assertEqual(template_data["UrgColor"], "c41230")
        self.assertEqual(template_data["maxctl"], "0")
        self.assertEqual(template_data["CtlColor"], "5e9732")

    def test_includes_detail_pdf_below_legacy_threshold(self) -> None:
        """Include attachment nine when fewer than 35 applications exist."""
        template_data = self.build_data(web_application_count=34)

        self.assertIn("Attachment 9: Details PDF", template_data["PdfFile"])
        self.assertIn("CUSTOMERDetails.pdf", template_data["PdfFile"])

    def test_omits_detail_pdf_at_legacy_threshold(self) -> None:
        """Omit attachment nine at 35 or more applications."""
        template_data = self.build_data(web_application_count=35)

        self.assertEqual(template_data["PdfFile"], "")

    def test_escapes_attachment_filename_for_latex_display(self) -> None:
        """Provide both raw and escaped filenames to the template."""
        template_data = self.build_data()

        self.assertEqual(
            template_data["DetailsCSV"],
            "vulnerability-list-CUSTOMER.csv",
        )
        self.assertEqual(
            template_data["DetailsCSVTex"],
            "vulnerability-list-CUSTOMER.csv",
        )

    def test_validation_reports_missing_fields(self) -> None:
        """Reject an incomplete template contract before rendering."""
        with self.assertRaisesRegex(ValueError, "Missing WAS template fields"):
            report_template_data.validate_template_data({"OrgName": "Customer"})


if __name__ == "__main__":
    unittest.main()
