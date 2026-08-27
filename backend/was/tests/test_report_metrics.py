"""Tests for WAS summary and chart metric calculations."""

# Standard Python Libraries
import unittest
from datetime import datetime, timezone
from pathlib import Path

# First-Party Libraries
from was_reports.reporting import report_metrics

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "was_report_metrics.xml"
CURRENT_TIME = datetime(2026, 8, 27, 13, 0)


class ReportMetricsTests(unittest.TestCase):
    """Validate legacy-compatible report metric calculations."""

    def test_calculate_summary_metrics_preserves_template_values(self) -> None:
        """Extract global summary values and legacy colors."""
        metrics = report_metrics.calculate_summary_metrics(
            FIXTURE_PATH.read_bytes()
        )

        self.assertEqual(metrics.start_date, "26 Aug 2026")
        self.assertEqual(metrics.security_risk, "High")
        self.assertEqual(metrics.total_information_findings, "7")
        self.assertEqual(metrics.web_application_count, "2")
        self.assertEqual(metrics.sensitive_content_count, "1")
        self.assertEqual(metrics.risk_color, "CB0000")
        self.assertEqual(metrics.sensitive_color, "c41230")

    def test_calculate_severity_totals_sums_summary_rows(self) -> None:
        """Sum each severity level across all web application summaries."""
        totals = report_metrics.calculate_severity_totals(
            FIXTURE_PATH.read_bytes()
        )

        self.assertEqual(totals, ("6", "6", "6", "6", "6"))

    def test_calculate_finding_metrics_preserves_status_counts(self) -> None:
        """Count fixed, total, new, reopened, and active findings."""
        metrics = report_metrics.calculate_finding_metrics(
            FIXTURE_PATH.read_bytes(),
            CURRENT_TIME,
        )

        self.assertEqual(metrics.fixed_count, 1)
        self.assertEqual(metrics.total_count, 4)
        self.assertEqual(metrics.new_count, 1)
        self.assertEqual(metrics.reopened_count, 1)
        self.assertEqual(metrics.active_count, 1)
        self.assertEqual(report_metrics.fixed_percentage(1, 4), 25)

    def test_calculate_finding_metrics_maps_groups_and_owasp(self) -> None:
        """Map active QIDs to legacy group and OWASP labels."""
        metrics = report_metrics.calculate_finding_metrics(
            FIXTURE_PATH.read_bytes(),
            CURRENT_TIME,
        )

        self.assertEqual(metrics.group_counts["Path Disclosure"], 1)
        self.assertEqual(metrics.group_counts["Information Disclosure"], 1)
        self.assertEqual(metrics.group_counts["SQL Injection"], 1)
        self.assertEqual(metrics.group_counts["Cross-Site Scripting"], 0)
        self.assertEqual(metrics.owasp_counts["Broken Access Control"], 1)
        self.assertEqual(metrics.owasp_counts["Injection"], 2)
        self.assertEqual(
            metrics.owasp_counts[
                "Identification and Authentication Failures"
            ],
            0,
        )

    def test_calculate_finding_metrics_preserves_cumulative_months(self) -> None:
        """Count findings cumulatively using legacy monthly comparisons."""
        metrics = report_metrics.calculate_finding_metrics(
            FIXTURE_PATH.read_bytes(),
            CURRENT_TIME,
        )

        self.assertEqual(metrics.fixed_monthly["August 2026"], 1)
        self.assertEqual(metrics.fixed_monthly["July 2026"], 0)
        self.assertEqual(metrics.vulnerabilities_monthly["August 2026"], 3)
        self.assertEqual(metrics.vulnerabilities_monthly["July 2026"], 2)
        self.assertEqual(metrics.vulnerabilities_monthly["June 2026"], 1)
        self.assertEqual(metrics.vulnerabilities_monthly["May 2026"], 0)

    def test_fixed_percentage_handles_empty_report(self) -> None:
        """Return zero when the report contains no findings."""
        self.assertEqual(report_metrics.fixed_percentage(0, 0), 0)

    def test_finding_metrics_accept_timezone_aware_current_time(self) -> None:
        """Compare Qualys UTC timestamps with the service UTC clock safely."""
        metrics = report_metrics.calculate_finding_metrics(
            FIXTURE_PATH.read_bytes(),
            datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(metrics.vulnerabilities_monthly["August 2026"], 3)


if __name__ == "__main__":
    unittest.main()
