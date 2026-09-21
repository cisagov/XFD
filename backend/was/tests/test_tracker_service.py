"""Tests for the production daily tracker orchestration service."""

# Standard Python Libraries
from datetime import date, datetime, timezone
import unittest
from unittest.mock import ANY, DEFAULT, MagicMock, patch

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.tracker import service
from was_reports.tracker.models import TrackerItem, TrackerStakeholder


class TrackerServiceTests(unittest.TestCase):
    """Validate tracker orchestration without external systems."""

    def test_preflight_stops_before_enrichment_and_writes(self) -> None:
        """Discovery counts must never assign, enrich, or persist candidates."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
        )
        with patch.multiple(
            service,
            tracker_search_window=DEFAULT,
            search_schedules=DEFAULT,
            search_scans=DEFAULT,
            pending_scan_groups=DEFAULT,
            create_tracker_items=DEFAULT,
            active_no_deletion_tags=DEFAULT,
            update_tracker=DEFAULT,
            print_discovery_breakdown=DEFAULT,
        ) as mocks:
            mocks["tracker_search_window"].return_value = (datetime(2026, 9, 1), set())
            mocks["search_schedules"].return_value = {"run": stakeholder}
            mocks["search_scans"].return_value = {"run": [object()]}
            mocks["pending_scan_groups"].return_value = {"run": [object()]}
            with patch("builtins.print") as mock_print:
                count = service.refresh_daily_tracker(object(), preflight_only=True)
            self.assertEqual(count, 1)
            self.assertIn("1 pending runs", mock_print.call_args_list[0].args[0])
            for operation in (
                "create_tracker_items",
                "active_no_deletion_tags",
                "update_tracker",
            ):
                mocks[operation].assert_not_called()

    def test_preflight_rejects_webapp_deletion(self) -> None:
        """Reject conflicting preflight options before contacting any service."""
        with self.assertRaises(ValueError):
            service.refresh_daily_tracker(
                object(), delete_apps=True, preflight_only=True
            )

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_discovery_breakdown_counts_overlapping_flags(
        self, mock_connect, mock_close
    ):
        """Pending flags are diagnostic counts and do not mutate tracker data."""
        connection = MagicMock()
        mock_connect.return_value = connection
        connection.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            ("TAG", True, True)
        ]
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2020-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
        )
        with patch("builtins.print") as mock_print:
            service.print_discovery_breakdown(
                {"run": []}, {"run": []}, {"run": stakeholder}
            )
        output = " ".join(call.args[0] for call in mock_print.call_args_list)
        self.assertIn("1 manual; 1 retired; 0 unknown", output)
        self.assertIn("1 older than", output)
        connection.set_session.assert_called_once_with(readonly=True)

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_recorded_runs_filtered_before_enrichment(self, mock_connect, mock_close):
        """Skip completed/imported runs while preserving delayed pending runs."""
        connection = MagicMock()
        mock_connect.return_value = connection
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
        )
        scan = etree.fromstring(
            b"<WasScan><name>Customer Run #2 Slice 1</name></WasScan>"
        )
        group = {"current": [scan]}
        cursor = connection.cursor.return_value.__enter__.return_value
        for key, start_day, status, expected_count in (
            ("legacy-import:2:2026-09-03", date(2026, 9, 3), "Finished", 0),
            (None, date(2026, 9, 2), "Finished", 1),
            ("current", date(2026, 9, 3), "Finished", 0),
            ("current", date(2026, 9, 3), "Running", 1),
        ):
            cursor.fetchall.return_value = [
                (
                    2,
                    start_day,
                    key,
                    "Customer Run #2",
                    status,
                    "Successful",
                    None,
                    None,
                    False,
                )
            ]
            result = service.pending_scan_groups(group, {"current": stakeholder})
            self.assertEqual(len(result), expected_count)
        connection.set_session.assert_called_with(readonly=True)

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
        mock_search_window.assert_called_once_with(lookback_days=3)
        mock_search_scans.assert_not_called()
        mock_create_items.assert_not_called()
        mock_update_tracker.assert_not_called()

    @patch("was_reports.tracker.service.active_no_deletion_tags")
    @patch("was_reports.tracker.service.pending_scan_groups")
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
        mock_pending_groups,
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
        history = {"older": [object()], **scan_groups}

        def populate_history(**arguments):
            """Keep fetched historical slices available without selecting them."""
            arguments["history_groups"].update(history)
            return scan_groups

        mock_search_scans.side_effect = populate_history
        mock_pending_groups.return_value = scan_groups
        mock_special_cases.return_value = {"CROSSFEED"}
        mock_create_items.return_value = tracker_items
        mock_update_tracker.return_value = 0

        result = service.refresh_daily_tracker(
            client=client,
            delete_apps=True,
            stakeholder_tag="CROSSFEED",
            tracker_lookback_days=7,
        )

        self.assertEqual(result, 0)
        mock_search_window.assert_called_once_with(lookback_days=7)
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
            counts=ANY,
            history_groups=history,
        )
        mock_create_items.assert_called_once_with(
            client=client,
            scan_groups=scan_groups,
            stakeholders=stakeholders,
            keep_nws_tags={"CROSSFEED"},
            previous_scan_groups=history,
        )
        mock_update_tracker.assert_called_once_with(
            client=client,
            tracker_items=tracker_items,
            delete_apps=True,
        )


if __name__ == "__main__":
    unittest.main()
