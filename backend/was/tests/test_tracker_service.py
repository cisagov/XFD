"""Tests for the production daily tracker orchestration service."""

# Standard Python Libraries
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.tracker import service
from was_reports.tracker.models import TrackerItem, TrackerStakeholder


class TrackerServiceTests(unittest.TestCase):
    """Validate tracker orchestration without external systems."""

    @patch("was_reports.tracker.service.update_tracker")
    @patch("was_reports.tracker.service.create_tracker_items")
    @patch("was_reports.tracker.service.search_scans")
    @patch("was_reports.tracker.service.search_schedules")
    @patch("was_reports.tracker.service.tracker_search_window")
    def test_refresh_returns_without_downstream_work_when_no_schedules(
        self,
        mock_search_window,
        mock_search_schedules,
        mock_search_scans,
        mock_create_items,
        mock_update_tracker,
    ) -> None:
        """Avoid scan and database writes when Qualys has no candidates."""
        input_date = datetime(2026, 9, 1, tzinfo=timezone.utc)
        mock_search_window.return_value = (input_date, {1})
        mock_search_schedules.return_value = {}

        result = service.refresh_daily_tracker(
            client=object(),
            stakeholder_tag="CROSSFEED",
        )

        self.assertEqual(result, 0)
        mock_search_scans.assert_not_called()
        mock_create_items.assert_not_called()
        mock_update_tracker.assert_not_called()

    @patch("was_reports.tracker.service.active_no_deletion_tags")
    @patch("was_reports.tracker.service.update_tracker")
    @patch("was_reports.tracker.service.create_tracker_items")
    @patch("was_reports.tracker.service.search_scans")
    @patch("was_reports.tracker.service.search_schedules")
    @patch("was_reports.tracker.service.tracker_search_window")
    def test_refresh_runs_complete_production_tracker_sequence(
        self,
        mock_search_window,
        mock_search_schedules,
        mock_search_scans,
        mock_create_items,
        mock_update_tracker,
        mock_special_cases,
    ) -> None:
        """Discover, consolidate, and persist tracker rows through src."""
        client = object()
        input_date = datetime(2026, 9, 1, tzinfo=timezone.utc)
        stakeholders = {
            "CROSSFEED": TrackerStakeholder(
                name="Crossfeed",
                tag_id=1,
                next_scan_date="2026-09-10T00:00:00Z",
                launched_date="2026-09-01T00:00:00Z",
                schedule_id=2,
                cadence="MONTHLY",
            )
        }
        scan_groups = {"CROSSFEED": [object()]}
        tracker_items = [
            TrackerItem(
                tag="CROSSFEED",
                scan_name="Crossfeed Run #1",
                status="Finished",
                result="Successful",
                launched_date="2026-09-01T00:00:00Z",
                next_scan_date="2026-09-10T00:00:00Z",
                nws=False,
                recent_nws="",
                removed_nws="",
                manual="",
                fceb=False,
                schedule_id=2,
                qualys_errors="",
            )
        ]
        mock_search_window.return_value = (input_date, {1})
        mock_search_schedules.return_value = stakeholders
        mock_search_scans.return_value = scan_groups
        mock_special_cases.return_value = {"CROSSFEED"}
        mock_create_items.return_value = tracker_items

        result = service.refresh_daily_tracker(
            client=client,
            delete_apps=True,
            stakeholder_tag="CROSSFEED",
        )

        self.assertEqual(result, 1)
        mock_search_schedules.assert_called_once_with(
            client=client,
            input_date=input_date,
            previous_schedule_ids={1},
            stakeholder_tag="CROSSFEED",
        )
        mock_search_scans.assert_called_once_with(
            client=client,
            stakeholders=stakeholders,
            input_date=input_date,
        )
        mock_create_items.assert_called_once_with(
            client=client,
            scan_groups=scan_groups,
            stakeholders=stakeholders,
            keep_nws_tags={"CROSSFEED"},
        )
        mock_update_tracker.assert_called_once_with(
            client=client,
            tracker_items=tracker_items,
            delete_apps=True,
        )


if __name__ == "__main__":
    unittest.main()
