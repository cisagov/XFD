"""Protect existing tracker executions while adopting parent launch timestamps."""

from dataclasses import replace
from datetime import date
import unittest
from unittest.mock import MagicMock, Mock, patch

from was_reports.data.daily_report_tracker import DailyReportTrackerRow
from was_reports.tracker.models import TrackerItem, scheduled_execution_key
from was_reports.tracker.update_service import (
    has_live_numbered_run_overlap,
    numbered_run_identity,
    update_execution,
    update_tracker,
)


def tracker_item() -> TrackerItem:
    """Return a numbered schedule run with a parent launch timestamp."""
    return TrackerItem(
        tag="TAG", scan_name="TAG - Monthly Run #12", status="Finished",
        result="Successful", launched_date="2026-09-21T12:00:00Z",
        next_scan_date="2026-10-21T12:00:00Z", nws=False, recent_nws="",
        removed_nws="", manual="", fceb=False, schedule_id=42, qualys_errors="",
    )


class TrackerExecutionIdentityTests(unittest.TestCase):
    """Validate conservative overlap holds and stable refresh locking."""

    def test_full_numbered_run_normalizes_only_cosmetic_differences(self) -> None:
        """Keep schedule name and run number while ignoring Unicode dashes/slices."""
        self.assertEqual(numbered_run_identity(" TAG – Monthly  Run #12 Slice 2 "),
                         "TAG - Monthly Run #12")
        self.assertNotEqual(numbered_run_identity("TAG - Monthly Run #12"),
                            numbered_run_identity("TAG - Monthly Run #13"))
        self.assertIsNone(numbered_run_identity("TAG - Monthly"))
        self.assertEqual(numbered_run_identity("TAG - Slice Company Run #12 Slice 2"),
                         "TAG - Slice Company Run #12")

    def test_live_old_key_same_run_is_overlap(self) -> None:
        """Parent timestamp migration must not duplicate a numbered slice run."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("TAG – Monthly Run #12 Slice 2",)]
        self.assertTrue(has_live_numbered_run_overlap(tracker_item(), "new-key", conn))
        query, parameters = cursor.execute.call_args.args
        self.assertEqual(parameters, (42, "new-key"))
        self.assertIn("scan_execution_key <> %s", query)
        self.assertIn("NOT LIKE 'legacy-import:%%'", query)
        self.assertNotIn("scan_start_date =", query)

    def test_new_numbered_run_is_not_overlap(self) -> None:
        """A later numbered execution on the same schedule remains eligible."""
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            ("TAG - Monthly Run #11 Slice 1",), ("OTHER - Monthly Run #12",),
        ]
        self.assertFalse(has_live_numbered_run_overlap(tracker_item(), "new-key", conn))

    @patch("was_reports.tracker.update_service.has_legacy_execution_overlap", return_value=False)
    @patch("was_reports.tracker.update_service.build_tracker_row")
    def test_new_numbered_run_can_insert(self, build, legacy) -> None:
        """The safeguard does not suppress a distinct run on the same schedule."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (100,)]
        cursor.fetchall.return_value = [("TAG - Monthly Run #11",)]
        build.return_value = DailyReportTrackerRow(tag="TAG")
        self.assertEqual(
            update_execution(Mock(), tracker_item(), False, date(2026, 9, 21),
                             "Analyst", conn, "new-key"), 1,
        )
        self.assertIn("INSERT INTO", str(cursor.execute.call_args.args[0]))
        conn.commit.assert_called_once_with()

    @patch("was_reports.tracker.update_service.build_tracker_row")
    def test_old_key_overlap_never_reaches_insert_or_external_updates(self, build) -> None:
        """Hold the new identity and leave historical tracker data unchanged."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = [("TAG - Monthly Run #12",)]
        client = Mock()
        with self.assertLogs("was_reports.tracker.update_service", level="WARNING"):
            count = update_execution(client, tracker_item(), False, date(2026, 9, 21),
                                     "Analyst", conn, "new-key")
        self.assertEqual(count, 0)
        build.assert_not_called()
        client.request.assert_not_called()
        for call in cursor.execute.call_args_list:
            self.assertTrue(str(call.args[0]).lstrip().startswith("SELECT"))

    @patch("was_reports.tracker.update_service.has_live_numbered_run_overlap")
    def test_same_key_completed_retry_still_skips_normally(self, overlap) -> None:
        """Existing exact execution-key handling takes precedence over migration."""
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
            99, "Finished", "Successful", "",
        )
        self.assertEqual(
            update_execution(Mock(), tracker_item(), False,
                             date(2026, 9, 21), "Analyst", conn, "same-key"), 0,
        )
        overlap.assert_not_called()

    @patch("was_reports.tracker.update_service.connect")
    @patch("was_reports.tracker.update_service.active_assignees", return_value=["Analyst"])
    @patch("was_reports.tracker.update_service.update_execution", return_value=0)
    def test_schedule_lock_is_stable_across_parent_and_slice_timestamps(
        self, update, assignees, connect
    ) -> None:
        """Concurrent upgraded refreshes serialize even when timestamps differ."""
        conn = connect.return_value
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True,)
        parent = tracker_item()
        slice_item = replace(parent, launched_date="2026-09-21T12:00:05Z")
        self.assertNotEqual(scheduled_execution_key(42, parent.launched_date),
                            scheduled_execution_key(42, slice_item.launched_date))
        update_tracker(Mock(), [parent, slice_item], False)
        lock_calls = [call for call in cursor.execute.call_args_list
                      if "pg_try_advisory_lock" in str(call.args[0])]
        self.assertEqual(len(lock_calls), 2)
        self.assertEqual(lock_calls[0].args[1], lock_calls[1].args[1])
