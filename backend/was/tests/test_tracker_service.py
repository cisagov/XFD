"""Tests for the production daily tracker orchestration service."""

# Standard Python Libraries
from datetime import date, datetime, timezone
import unittest
from unittest.mock import ANY, DEFAULT, MagicMock, patch

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.tracker import service
from was_reports.tracker.models import (
    MISSING_QUALYS_FIELD_NOTE_PREFIX,
    MISSING_QUALYS_SCHEDULE_NOTE_PREFIX,
    QUALYS_DELETION_RETRYABLE_NOTE,
    RESOLVED_QUALYS_SCHEDULE_NOTE_PREFIX,
    TrackerItem,
    TrackerStakeholder,
)
from was_reports.tracker.service import reconcile_known_schedule_reviews


class TrackerServiceTests(unittest.TestCase):
    """Validate tracker orchestration without external systems."""

    def setUp(self) -> None:
        """Isolate refresh orchestration from the separately tested database boundary."""
        reconciliation = patch.object(
            service, "reconcile_known_schedule_reviews", return_value=0
        )
        self.mock_reconciliation = reconciliation.start()
        self.addCleanup(reconciliation.stop)

    def test_existing_execution_resolves_schedule_review_under_claim_guards(
        self,
    ) -> None:
        """Close the metadata exception without changing the already tracked run."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
        )
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = MISSING_QUALYS_SCHEDULE_NOTE_PREFIX + "lastScan.launchedDate"
        cursor.fetchall.return_value = [(2,)]
        cursor.fetchone.side_effect = [(True,), (17, note, 18)]
        cursor.rowcount = 1
        with patch.object(service, "connect", return_value=conn), patch.object(
            service, "close"
        ):
            self.assertEqual(
                reconcile_known_schedule_reviews({"execution": stakeholder}), 1
            )
        update = next(
            call
            for call in cursor.execute.call_args_list
            if "UPDATE was_daily_report_tracker" in call.args[0]
        )
        self.assertIn("status = 'Resolved'", update.args[0])
        self.assertIn("report_sent_date IS NULL", update.args[0])
        self.assertIn("NOT EXISTS (SELECT 1 FROM was_report_runs", update.args[0])
        self.assertEqual(update.args[1][1:], (17, note))
        self.assertTrue(
            update.args[1][0].startswith(RESOLVED_QUALYS_SCHEDULE_NOTE_PREFIX)
        )
        self.assertIn("tracker row 18", update.args[1][0])
        self.assertIn(note, update.args[1][0])

    def test_schedule_review_without_matching_execution_remains_open(self) -> None:
        """Recovery does not close an exception until an actual tracker row exists."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
        )
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [(2,)]
        cursor.fetchone.side_effect = [(True,), None]
        with patch.object(service, "connect", return_value=conn), patch.object(
            service, "close"
        ):
            self.assertEqual(
                reconcile_known_schedule_reviews({"execution": stakeholder}), 0
            )
        self.assertNotIn(
            "UPDATE was_daily_report_tracker", str(cursor.execute.call_args_list)
        )

    def test_schedule_review_is_not_resolved_while_metadata_is_missing(self) -> None:
        """A restored last date alone does not resolve a still-missing next date."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            None,
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
            discovery_notes=MISSING_QUALYS_SCHEDULE_NOTE_PREFIX + "nextLaunchDate",
        )
        with patch.object(service, "connect") as connect:
            self.assertEqual(
                reconcile_known_schedule_reviews({"execution": stakeholder}), 0
            )
        connect.assert_not_called()

    def test_discovery_exception_is_persisted_without_scan_candidates(self) -> None:
        """A deactivated schedule cannot disappear through an early return."""
        issue = TrackerItem(
            tag="TAG",
            scan_name="Customer Monthly",
            status="Unknown",
            result="Unknown",
            launched_date=None,
            next_scan_date=None,
            nws=False,
            recent_nws="",
            removed_nws="",
            manual=MISSING_QUALYS_SCHEDULE_NOTE_PREFIX + "lastScan.launchedDate",
            fceb=False,
            schedule_id=2,
            qualys_errors="lastScan.launchedDate",
            scan_execution_key="schedule-review:2",
        )

        def discover(**kwargs):
            """Return only a schedule issue, as the real discovery output does."""
            kwargs["discovery_issues"].append(issue)
            return {}

        with patch.multiple(
            service,
            tracker_search_window=DEFAULT,
            search_schedules=DEFAULT,
            search_scans=DEFAULT,
            update_tracker=DEFAULT,
        ) as mocks:
            mocks["tracker_search_window"].return_value = (datetime(2026, 9, 1), set())
            mocks["search_schedules"].side_effect = discover
            mocks["update_tracker"].return_value = 1
            self.assertEqual(service.refresh_daily_tracker(object()), 1)
            mocks["search_scans"].assert_not_called()
            self.assertEqual(
                mocks["update_tracker"].call_args.kwargs["tracker_items"], [issue]
            )

    def test_discovery_exception_preflight_never_writes(self) -> None:
        """Report schedule exceptions without assigning or persisting anything."""
        issue = TrackerItem(
            tag="TAG",
            scan_name="Customer Monthly",
            status="Unknown",
            result="Unknown",
            launched_date=None,
            next_scan_date=None,
            nws=False,
            recent_nws="",
            removed_nws="",
            manual=MISSING_QUALYS_SCHEDULE_NOTE_PREFIX + "lastScan.launchedDate",
            fceb=False,
            schedule_id=2,
            qualys_errors="lastScan.launchedDate",
            scan_execution_key="schedule-review:2",
        )

        def discover(**kwargs):
            """Capture an unresolved schedule without fabricating a scan."""
            kwargs["discovery_issues"].append(issue)
            return {}

        with patch.multiple(
            service,
            tracker_search_window=DEFAULT,
            search_schedules=DEFAULT,
            search_scans=DEFAULT,
            update_tracker=DEFAULT,
        ) as mocks, patch("builtins.print") as output:
            mocks["tracker_search_window"].return_value = (datetime(2026, 9, 1), set())
            mocks["search_schedules"].side_effect = discover
            self.assertEqual(
                service.refresh_daily_tracker(object(), preflight_only=True), 1
            )
            mocks["update_tracker"].assert_not_called()
            mocks["search_scans"].assert_not_called()
            self.mock_reconciliation.assert_not_called()
            self.assertIn("1 manual exceptions; no writes", output.call_args.args[0])

    def test_missing_next_date_notes_flow_to_completed_tracker_item(self) -> None:
        """Completed scans remain manual when their schedule lacks a next date."""
        # Third-Party Libraries
        from was_reports.tracker.item_builder import create_tracker_items

        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            None,
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
            discovery_notes=MISSING_QUALYS_SCHEDULE_NOTE_PREFIX + "nextLaunchDate",
        )
        scan = etree.fromstring(
            b"<WasScan><name>Customer Run #2</name><status>FINISHED</status>"
            b"<summary><resultsStatus>SUCCESSFUL</resultsStatus></summary></WasScan>"
        )
        with patch(
            "was_reports.tracker.item_builder.stakeholder_flags",
            return_value=("", False),
        ):
            item = create_tracker_items(
                object(), {"run": [scan]}, {"run": stakeholder}, set()
            )[0]
        self.assertEqual(item.status, "Finished")
        self.assertEqual(item.result, "Successful")
        self.assertIsNone(item.next_scan_date)
        self.assertEqual(item.manual, stakeholder.discovery_notes)
        self.assertIn("nextLaunchDate", item.qualys_errors)

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_captured_schedule_rows_never_open_database(self, mock_connect, mock_close):
        """Replay empty, handled, and unresolved snapshots with production rules."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T02:00:00Z",
            2,
            "MONTHLY",
            "TAG",
            latest_scan_name="Customer Run #2 Slice 1",
        )
        handled = (
            2,
            date(2026, 9, 2),
            "Customer Run #2",
            "Finished",
            "Successful",
            None,
            None,
            False,
            False,
        )
        unresolved = handled[:7] + (True, False)
        for rows, expected in (
            ([], 1),
            ([handled], 0),
            ([unresolved], 1),
            ([handled, unresolved], 1),
        ):
            with self.subTest(rows=rows):
                counts: dict[str, int] = {}
                result = service.pending_schedules(
                    {"run": stakeholder}, counts, tracker_rows=rows
                )
                self.assertEqual(len(result), expected)
                self.assertEqual(counts["early_excluded_schedules"], 1 - expected)
        mock_connect.assert_not_called()
        mock_close.assert_not_called()

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_early_exclusion_requires_handled_exact_execution(
        self, mock_connect, mock_close
    ):
        """Retain uncertain records and recurring runs before expensive searches."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T02:00:00Z",
            2,
            "MONTHLY",
            "TAG",
            latest_scan_name="Customer Run #2 Slice 1",
        )
        connection = mock_connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        baseline = [
            2,
            date(2026, 9, 2),
            "Customer Run #2",
            "Finished",
            "Successful",
            None,
            None,
            False,
            False,
        ]
        cases = [
            ({}, 0),
            ({2: "Customer Run #1"}, 1),
            ({0: 3}, 1),
            ({1: date(2026, 9, 3)}, 1),
            ({2: None}, 1),
            ({3: "Error", 4: "Failed"}, 1),
            ({3: "Error", 4: "Scan Internal Error"}, 0),
            ({4: "PROCESSING"}, 1),
            ({4: " "}, 1),
            ({6: "QUALYS DELETION REQUIRED"}, 1),
            ({7: True}, 1),
            ({7: True, 8: True}, 0),
            ({7: True, 5: date(2026, 9, 4)}, 0),
        ]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                row = baseline.copy()
                for position, value in changes.items():
                    row[position] = value
                cursor.fetchall.return_value = [row]
                counts: dict[str, int] = {}
                result = service.pending_schedules({"run": stakeholder}, counts)
                self.assertEqual(len(result), expected)
                self.assertEqual(counts["early_excluded_schedules"], 1 - expected)
        connection.set_session.assert_called_with(readonly=True)
        connection.commit.assert_not_called()

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_unresolved_sibling_requires_delivery_evidence(
        self, mock_connect, mock_close
    ):
        """Only customer delivery evidence overrides an unresolved same-run sibling."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
            latest_scan_name="Customer Run #2",
        )
        cursor = mock_connect.return_value.cursor.return_value.__enter__.return_value
        completed = [
            2,
            date(2026, 9, 3),
            "Customer Run #2",
            "Finished",
            "Successful",
            None,
            None,
            False,
            False,
        ]
        unresolved = completed.copy()
        unresolved[7] = True
        cursor.fetchall.return_value = [completed, unresolved]
        self.assertEqual(len(service.pending_schedules({"run": stakeholder})), 1)
        completed[8] = True
        self.assertEqual(len(service.pending_schedules({"run": stakeholder})), 0)
        unresolved[6] = "QUALYS DELETION REQUIRED"
        self.assertEqual(
            len(service.pending_schedules({"run": stakeholder}, delete_apps=True)), 1
        )
        unresolved[6] = QUALYS_DELETION_RETRYABLE_NOTE
        self.assertEqual(
            len(service.pending_schedules({"run": stakeholder}, delete_apps=True)), 1
        )

    def test_early_exclusion_prevents_all_downstream_calls(self):
        """An entirely handled schedule set must not fetch slices or write rows."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T12:00:00Z",
            2,
            "MONTHLY",
            "TAG",
            latest_scan_name="Customer Run #2",
        )
        with patch.multiple(
            service,
            tracker_search_window=DEFAULT,
            search_schedules=DEFAULT,
            pending_schedules=DEFAULT,
            search_scans=DEFAULT,
            update_tracker=DEFAULT,
        ) as mocks:
            mocks["tracker_search_window"].return_value = (datetime(2026, 9, 1), set())
            mocks["search_schedules"].return_value = {"run": stakeholder}
            mocks["pending_schedules"].return_value = {}
            self.assertEqual(service.refresh_daily_tracker(object()), 0)
            mocks["search_scans"].assert_not_called()
            mocks["update_tracker"].assert_not_called()

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
            ("current", date(2026, 9, 3), "Error", 0),
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

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_missing_field_manual_retries_only_before_claim_or_delivery(
        self, mock_connect, mock_close
    ) -> None:
        """Retry missing-field rows without reclaiming delivered or linked work."""
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
        scan_groups = {"current": [scan]}
        connection = mock_connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        missing_notes = MISSING_QUALYS_FIELD_NOTE_PREFIX + "summary"
        cases = (
            ("recoverable", missing_notes, None, False, True),
            ("linked", missing_notes, None, True, False),
            ("sent", missing_notes, date(2026, 9, 4), False, False),
            ("linked_and_sent", missing_notes, date(2026, 9, 4), True, False),
            ("ordinary_manual", "MANUAL: Review required.", None, False, False),
        )
        for case_name, notes, sent, linked, expected_pending in cases:
            with self.subTest(case=case_name):
                cursor.fetchall.return_value = [
                    (
                        2,
                        date(2026, 9, 3),
                        "current",
                        "Customer Run #2",
                        "Error",
                        "Missing required Qualys scan field",
                        sent,
                        notes,
                        linked,
                    )
                ]
                counts: dict[str, int] = {}
                result = service.pending_scan_groups(
                    scan_groups, {"current": stakeholder}, counts=counts
                )
                self.assertEqual(result, scan_groups if expected_pending else {})
                self.assertEqual(counts["pending_runs"], int(expected_pending))
                self.assertEqual(counts["recorded_runs"], int(not expected_pending))
        connection.set_session.assert_called_with(readonly=True)
        connection.commit.assert_not_called()

    @patch("was_reports.tracker.service.close")
    @patch("was_reports.tracker.service.connect")
    def test_retryable_deletion_requires_explicit_deletion_mode(
        self, mock_connect, mock_close
    ) -> None:
        """Enrich retryable deletion rows only for a deletion-enabled refresh."""
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
        scan_groups = {"current": [scan]}
        connection = mock_connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            (
                2,
                date(2026, 9, 3),
                "current",
                "Customer Run #2",
                "Finished",
                "No Web Service",
                None,
                QUALYS_DELETION_RETRYABLE_NOTE,
                False,
            )
        ]

        self.assertEqual(
            service.pending_scan_groups(
                scan_groups,
                {"current": stakeholder},
                delete_apps=False,
            ),
            {},
        )
        self.assertEqual(
            service.pending_scan_groups(
                scan_groups,
                {"current": stakeholder},
                delete_apps=True,
            ),
            scan_groups,
        )
        connection.set_session.assert_called_with(readonly=True)
        connection.commit.assert_not_called()

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
            discovery_issues=[],
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
