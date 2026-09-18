"""Tests for recent-scan batch preflight reporting."""

# Standard Python Libraries
from datetime import date
import logging
import unittest

# First-Party Libraries
from was_reports.commands.batch_progress import (
    log_candidate_progress,
    log_preflight_summary,
    summarize_candidates,
)
from was_reports.data.daily_report_tracker import TrackerReportCandidate


class BatchProgressTests(unittest.TestCase):
    """Validate stable and operator-readable batch preflight counts."""

    def test_summarize_candidates_counts_templates_and_qualys_overlays(self) -> None:
        """Count each selected template and nonblank Qualys error overlay."""
        candidates = [
            TrackerReportCandidate(
                id=1,
                tag="TAG1",
                data_pull_date=date(2026, 9, 18),
                schedule_id=11,
                assignee_id=1,
                template="Results",
            ),
            TrackerReportCandidate(
                id=2,
                tag="TAG2",
                data_pull_date=date(2026, 9, 18),
                schedule_id=12,
                assignee_id=1,
                template="Action Required",
                qualys_error="Scan Internal Error",
            ),
            TrackerReportCandidate(
                id=3,
                tag="TAG3",
                data_pull_date=date(2026, 9, 18),
                schedule_id=13,
                assignee_id=2,
                template="Results",
                qualys_error="   ",
            ),
            TrackerReportCandidate(
                id=4,
                tag="TAG4",
                data_pull_date=date(2026, 9, 18),
                schedule_id=14,
                assignee_id=2,
            ),
        ]

        summary = summarize_candidates(candidates)

        self.assertEqual(summary.candidates, 4)
        self.assertEqual(
            summary.template_counts,
            (
                ("Action Required", 1),
                ("Results", 2),
                ("Unspecified", 1),
            ),
        )
        self.assertEqual(summary.qualys_error_overlays, 1)

    def test_log_preflight_summary_reports_scope_and_counts(self) -> None:
        """Provide the report mix before any candidate is claimed."""
        summary = summarize_candidates(
            [
                TrackerReportCandidate(
                    id=1,
                    tag="TAG1",
                    data_pull_date=date(2026, 9, 18),
                    schedule_id=11,
                    assignee_id=1,
                    template="All NWS",
                )
            ]
        )
        logger = logging.getLogger("was-tests.batch-progress")

        with self.assertLogs(logger, level="INFO") as captured:
            log_preflight_summary(logger, summary, days_back=7)

        output = "\n".join(captured.output)
        self.assertIn("Report preflight", output)
        self.assertIn("1 candidate(s)", output)
        self.assertIn("last 7 calendar days", output)
        self.assertIn("All NWS=1", output)
        self.assertIn("Qualys error overlays: 0", output)

    def test_log_candidate_progress_reports_phase_and_fraction(self) -> None:
        """Show each worker's current candidate and its partition total."""
        logger = logging.getLogger("was-tests.batch-progress")

        with self.assertLogs(logger, level="INFO") as captured:
            log_candidate_progress(
                logger,
                candidate_index=3,
                candidate_count=8,
                stakeholder_tag="TAG3",
            )

        output = "\n".join(captured.output)
        self.assertIn("Phase 3/5", output)
        self.assertIn("3/8", output)
        self.assertIn("TAG3", output)


if __name__ == "__main__":
    unittest.main()
