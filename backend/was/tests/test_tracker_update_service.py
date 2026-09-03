"""Tests for production tracker consolidation and update helpers."""

# Standard Python Libraries
from datetime import date
import unittest

# First-Party Libraries
from was_reports.tracker.item_builder import combined_status_and_result
from was_reports.tracker.models import TrackerItem
from was_reports.tracker.update_service import (
    combined_email_value,
    convert_qualys_date,
    tracker_result_fields,
)


class TrackerUpdateServiceTests(unittest.TestCase):
    """Validate tracker result and database-row transformations."""

    def test_combined_status_prioritizes_running_scan(self) -> None:
        """Treat any running slice as a running multi-scan."""
        result = combined_status_and_result(
            ["FINISHED", "RUNNING"],
            ["SUCCESSFUL", "PROCESSING"],
        )

        self.assertEqual(result, ("Running", "Running"))

    def test_combined_email_value(self) -> None:
        """Preserve both technical and distribution recipients."""
        self.assertEqual(
            combined_email_value("tech@example.gov", "team@example.gov"),
            "tech@example.gov; team@example.gov",
        )

    def test_convert_qualys_date_uses_eastern_calendar_day(self) -> None:
        """Convert early UTC timestamps to the prior Eastern day."""
        converted = convert_qualys_date("2026-09-03T01:00:00Z")

        self.assertEqual(converted, date(2026, 9, 2))

    def test_tracker_result_fields_selects_results_template(self) -> None:
        """Select the results template for a successful accessible scan."""
        item = TrackerItem(
            tag="TAG",
            scan_name="Scan",
            status="Finished",
            result="Successful",
            launched_date="2026-09-01T00:00:00Z",
            next_scan_date="2026-10-01T00:00:00Z",
            nws=False,
            recent_nws="",
            removed_nws="",
            manual="",
            fceb=False,
            schedule_id=1,
            qualys_errors="",
        )

        fields = tracker_result_fields(item, 10, True, "")

        self.assertEqual(fields, ("10", "Results", ""))


if __name__ == "__main__":
    unittest.main()
