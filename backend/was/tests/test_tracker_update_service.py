"""Tests for production tracker consolidation and update helpers."""

# Standard Python Libraries
from datetime import date
import unittest
from unittest.mock import Mock, patch

# First-Party Libraries
from was_reports.data.daily_report_tracker import DailyReportTrackerRow
from was_reports.tracker.item_builder import combined_status_and_result
from was_reports.tracker.models import TrackerItem
from was_reports.tracker.update_service import (
    combined_email_value,
    convert_qualys_date,
    tracker_result_fields,
    update_tracker,
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

    @patch("was_reports.tracker.update_service.insert_daily_report_tracker_row")
    @patch("was_reports.tracker.update_service.build_tracker_row")
    @patch("was_reports.tracker.update_service.active_assignees")
    @patch("was_reports.tracker.update_service.connect")
    def test_deletion_required_stays_manual_when_deletion_disabled(
        self,
        mock_connect,
        mock_active_assignees,
        mock_build_tracker_row,
        mock_insert_tracker_row,
    ) -> None:
        """Do not claim targets were removed when deletion is disabled."""
        mock_connect.return_value = Mock()
        mock_active_assignees.return_value = ["Analyst"]
        mock_build_tracker_row.return_value = DailyReportTrackerRow(
            tag="TAG",
            template="Targets Removed",
        )
        item = TrackerItem(
            tag="TAG",
            scan_name="Scan",
            status="Finished",
            result="No Web Service",
            launched_date="2026-09-01T00:00:00Z",
            next_scan_date="2026-10-01T00:00:00Z",
            nws=True,
            recent_nws="<br>https://example.gov",
            removed_nws="<br>https://example.gov",
            manual="",
            fceb=False,
            schedule_id=1,
            qualys_errors="",
        )

        update_tracker(Mock(), [item], delete_apps=False)

        inserted_row = mock_insert_tracker_row.call_args.kwargs["row"]
        self.assertEqual(inserted_row.template, "Action Required")
        self.assertEqual(
            inserted_row.report_scan_notes,
            "QUALYS DELETION REQUIRED",
        )

    @patch("was_reports.tracker.update_service.delete_webapp")
    @patch("was_reports.tracker.update_service.insert_daily_report_tracker_row")
    @patch("was_reports.tracker.update_service.build_tracker_row")
    @patch("was_reports.tracker.update_service.active_assignees")
    @patch("was_reports.tracker.update_service.connect")
    def test_successful_deletion_is_recorded_before_tracker_insert(
        self,
        mock_connect,
        mock_active_assignees,
        mock_build_tracker_row,
        mock_insert_tracker_row,
        mock_delete_webapp,
    ) -> None:
        """Record Targets Removed only after Qualys deletion succeeds."""
        sequence = Mock()
        sequence.attach_mock(mock_delete_webapp, "delete")
        sequence.attach_mock(mock_insert_tracker_row, "insert")
        mock_connect.return_value = Mock()
        mock_active_assignees.return_value = ["Analyst"]
        mock_build_tracker_row.return_value = DailyReportTrackerRow(
            tag="TAG",
            template="Deactivated",
            report_scan_notes="DEACTIVATE",
        )
        item = self.removal_item(fceb=False)

        update_tracker(Mock(), [item], delete_apps=True)

        self.assertEqual(
            [call[0] for call in sequence.mock_calls],
            ["delete", "insert"],
        )
        inserted_row = mock_insert_tracker_row.call_args.kwargs["row"]
        self.assertEqual(inserted_row.template, "Targets Removed")
        self.assertEqual(inserted_row.report_scan_notes, "")

    @patch("was_reports.tracker.update_service.delete_webapp")
    @patch("was_reports.tracker.update_service.insert_daily_report_tracker_row")
    @patch("was_reports.tracker.update_service.build_tracker_row")
    @patch("was_reports.tracker.update_service.active_assignees")
    @patch("was_reports.tracker.update_service.connect")
    def test_fceb_removal_candidate_is_never_deleted(
        self,
        mock_connect,
        mock_active_assignees,
        mock_build_tracker_row,
        mock_insert_tracker_row,
        mock_delete_webapp,
    ) -> None:
        """Preserve FCEB applications even when destructive mode is enabled."""
        mock_connect.return_value = Mock()
        mock_active_assignees.return_value = ["Analyst"]
        mock_build_tracker_row.return_value = DailyReportTrackerRow(
            tag="TAG",
            template="FCEB All NWS",
        )

        update_tracker(Mock(), [self.removal_item(fceb=True)], delete_apps=True)

        mock_delete_webapp.assert_not_called()
        inserted_row = mock_insert_tracker_row.call_args.kwargs["row"]
        self.assertEqual(inserted_row.template, "FCEB All NWS")

    @staticmethod
    def removal_item(fceb: bool) -> TrackerItem:
        """Return a repeated-inaccessible tracker item for safety tests."""
        return TrackerItem(
            tag="TAG",
            scan_name="Scan",
            status="Finished",
            result="No Web Service",
            launched_date="2026-09-01T00:00:00Z",
            next_scan_date="2026-10-01T00:00:00Z",
            nws=True,
            recent_nws="<br>https://example.gov",
            removed_nws="<br>https://example.gov",
            manual="",
            fceb=fceb,
            schedule_id=1,
            qualys_errors="",
        )


if __name__ == "__main__":
    unittest.main()
