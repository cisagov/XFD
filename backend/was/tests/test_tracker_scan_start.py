"""Actual scan start must remain independent of stable schedule identity."""

from datetime import datetime, timezone
from dataclasses import replace
import unittest
from unittest.mock import patch

from lxml import etree

from was_reports.tracker.item_builder import create_tracker_items, earliest_slice_start
from was_reports.tracker.models import TrackerStakeholder, scheduled_execution_key, scan_time_bounds


class ScanStartTests(unittest.TestCase):
    """Verify actual launch extraction without inventing historical timestamps."""

    def test_end_bounds_require_all_valid_target_ends(self):
        """Select the latest real end, preserving unknown and contradictory times."""
        for ending, expected in (
            ("2026-09-01T15:00:00+02:00", datetime(2026, 9, 1, 13, tzinfo=timezone.utc)),
            ("", None), ("2026-09-01T11:59:00Z", None), ("2026-09-01T13:00:00", None),
        ):
            with self.subTest(ending=ending):
                scans = [etree.fromstring(
                    "<WasScan><launchedDate>2026-09-01T12:00:00Z</launchedDate>"
                    "<endScanDate>{}</endScanDate></WasScan>".format(value)
                ) for value in ("2026-09-01T12:30:00Z", ending)]
                start, end = scan_time_bounds(scans)
                self.assertEqual(start, datetime(2026, 9, 1, 12, tzinfo=timezone.utc))
                self.assertEqual(end, expected)

    def test_missing_or_naive_timestamp_is_unknown(self):
        """One missing or invalid slice time prevents an asserted aggregate start."""
        for value in ("", "invalid", "2026-09-01T12:00:00"):
            scan = etree.fromstring("<WasScan><launchedDate>{}</launchedDate></WasScan>".format(value))
            self.assertIsNone(earliest_slice_start([scan]))
        self.assertIsNone(earliest_slice_start([]))

    @patch("was_reports.tracker.item_builder.stakeholder_flags", return_value=("", False))
    def test_actual_start_does_not_change_parent_execution_key(self, flags):
        """Use earliest target launch for display and parent launch for identity."""
        parent = "2026-09-01T14:00:00Z"
        stakeholder = TrackerStakeholder("Customer", 1, "2026-10-01T12:00:00Z", parent,
                                         2, "MONTHLY", "TAG")
        scans = [etree.fromstring(
            "<WasScan><name>Customer Run #1 Slice 1</name><status>FINISHED</status>"
            "<summary><resultsStatus>SUCCESSFUL</resultsStatus></summary>"
            "<target><webApp><url>https://example.gov</url></webApp></target>"
            "<launchedDate>{}</launchedDate></WasScan>".format(value)
        ) for value in ("2026-09-01T13:00:00Z", "2026-09-01T08:00:00-04:00")]
        item = create_tracker_items(object(), {"run": scans}, {"run": stakeholder}, set())[0]
        self.assertEqual(item.launched_date, parent)
        self.assertEqual(item.scan_execution_key, scheduled_execution_key(2, parent))
        self.assertEqual(item.scan_started_at, datetime(2026, 9, 1, 12, tzinfo=timezone.utc))
        self.assertIsNone(item.scan_ended_at)
        parent_details = replace(
            stakeholder,
            scan_started_at=datetime(2026, 9, 1, 11, tzinfo=timezone.utc),
            scan_ended_at=datetime(2026, 9, 1, 16, tzinfo=timezone.utc),
        )
        item = create_tracker_items(object(), {"run": scans}, {"run": parent_details}, set())[0]
        self.assertEqual(item.scan_started_at, parent_details.scan_started_at)
        self.assertEqual(item.scan_ended_at, parent_details.scan_ended_at)
        self.assertEqual(item.scan_execution_key, scheduled_execution_key(2, parent))
