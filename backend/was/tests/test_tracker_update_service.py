"""Tests for production tracker consolidation and update helpers."""

# Standard Python Libraries
from dataclasses import fields, replace
from datetime import date, datetime, timezone
import unittest
from unittest.mock import MagicMock, Mock, patch

# Third-Party Libraries
from lxml import etree
import requests

# First-Party Libraries
from was_reports.data.daily_report_tracker import DailyReportTrackerRow
from was_reports.qualys.qualys_admin import WebAppIdentity
from was_reports.tracker.item_builder import (
    combined_status_and_result,
    create_tracker_items,
)
from was_reports.tracker.models import (
    MISSING_QUALYS_FIELD_NOTE_PREFIX,
    TrackerItem,
    TrackerStakeholder,
)
from was_reports.tracker.update_service import (
    build_tracker_row,
    combined_email_value,
    convert_qualys_date,
    delete_validated_webapp,
    has_legacy_execution_overlap,
    tracker_result_fields,
    update_execution,
    update_stakeholder_scan_metadata,
    update_tracker,
    validate_latest_deletion_execution,
    validate_webapp_tags,
)


class TrackerUpdateServiceTests(unittest.TestCase):
    """Validate tracker result and database-row transformations."""

    def test_actual_scan_bounds_do_not_change_parent_execution_identity(self) -> None:
        """Persist real timing separately from parent-based identity and scan day."""
        started = datetime(2026, 8, 30, 23, tzinfo=timezone.utc)
        ended = datetime(2026, 9, 1, 1, tzinfo=timezone.utc)
        item = replace(
            self.removal_item(False), scan_started_at=started, scan_ended_at=ended
        )
        stakeholder = Mock(
            was_report_poc="POC",
            tech_poc_email=None,
            distro_email=None,
            comments=None,
            report_password=None,
        )
        with patch(
            "was_reports.tracker.update_service.resolve_stakeholder_details",
            return_value=stakeholder,
        ), patch(
            "was_reports.tracker.update_service.count_webapps", return_value=2
        ), patch(
            "was_reports.tracker.update_service.upsert_assignee",
            return_value=Mock(id=1, name="Analyst"),
        ), patch(
            "was_reports.tracker.update_service.update_stakeholder_scan_metadata"
        ):
            row = build_tracker_row(
                Mock(), item, "Analyst", MagicMock(), date(2026, 9, 2)
            )
        self.assertEqual(row.scan_started_at, started)
        self.assertEqual(row.scan_ended_at, ended)
        self.assertEqual(row.scan_start_date, date(2026, 8, 31))
        self.assertEqual(row.scan_execution_key, "schedule:1:2026-09-01T00:00:00+00:00")

    def test_insert_and_incomplete_update_persist_both_actual_bounds(self) -> None:
        """Future refreshes bind start and end on both persistence branches."""
        started = datetime(2026, 9, 1, tzinfo=timezone.utc)
        ended = datetime(2026, 9, 1, 1, tzinfo=timezone.utc)
        row = DailyReportTrackerRow(
            tag="TAG", scan_started_at=started, scan_ended_at=ended
        )
        item = replace(
            self.removal_item(False),
            removed_nws="",
            scan_started_at=started,
            scan_ended_at=ended,
        )
        for existing in (False, True):
            with self.subTest(existing=existing):
                conn = MagicMock()
                cursor = conn.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = (
                    [(17, "Running", "PROCESSING", "", "schedule-review:1"), (False,)]
                    if existing
                    else [None, (17,)]
                )
                cursor.rowcount = 1
                with patch(
                    "was_reports.tracker.update_service.build_tracker_row",
                    return_value=row,
                ), patch(
                    "was_reports.tracker.update_service.has_live_numbered_run_overlap",
                    return_value=False,
                ):
                    count = update_execution(
                        Mock(),
                        item,
                        False,
                        date(2026, 9, 2),
                        "Analyst",
                        conn,
                        "stable-parent-key",
                    )
                self.assertEqual(count, 1)
                first_query, first_parameters = cursor.execute.call_args_list[0].args
                self.assertIn("pg_advisory_xact_lock", str(first_query))
                self.assertEqual(first_parameters, ("was-tracker-tag:TAG",))
                query, parameters = cursor.execute.call_args.args
                self.assertIn("scan_started_at", str(query))
                self.assertIn("scan_ended_at", str(query))
                if existing:
                    self.assertEqual(parameters[5:7], [started, ended])
                else:
                    names = [field.name for field in fields(row) if field.name != "id"]
                    bindings = dict(zip(names, parameters))
                    self.assertEqual(bindings["scan_started_at"], started)
                    self.assertEqual(bindings["scan_ended_at"], ended)
                    self.assertEqual(
                        bindings["scan_execution_key"], "stable-parent-key"
                    )

    def test_missing_schedule_dates_preserve_manual_without_metadata(self) -> None:
        """Persist unknown dates without altering stakeholder execution metadata."""
        note = "MANUAL: Missing required Qualys schedule field: lastScan/launchedDate."
        item = replace(
            self.removal_item(False),
            launched_date=None,
            next_scan_date=None,
            status="Unknown",
            result="Unknown",
            manual=note,
            removed_nws="",
            qualys_errors="Missing required Qualys schedule field: lastScan/launchedDate.",
            scan_execution_key="schedule-review:1",
        )
        details = Mock(
            was_report_poc=None,
            tech_poc_email=None,
            distro_email=None,
            comments=None,
            report_password=None,
        )
        with patch(
            "was_reports.tracker.update_service.resolve_stakeholder_details",
            return_value=details,
        ), patch(
            "was_reports.tracker.update_service.count_webapps", return_value=2
        ) as count, patch(
            "was_reports.tracker.update_service.upsert_assignee",
            return_value=Mock(id=1, name="Analyst"),
        ), patch(
            "was_reports.tracker.update_service.update_stakeholder_scan_metadata"
        ) as metadata:
            row = build_tracker_row(Mock(), item, "Analyst", MagicMock(), date.today())
        self.assertIsNone(row.scan_start_date)
        self.assertIsNone(row.next_scan_date)
        self.assertEqual(row.report_scan_notes, note)
        self.assertEqual(row.scan_execution_key, "schedule-review:1")
        self.assertIn("lastScan/launchedDate", row.qualys_error)
        metadata.assert_not_called()
        count.assert_not_called()
        self.assertIsNone(row.template)

    def test_unidentified_schedule_review_persists_nullable_identity_without_enrichment(
        self,
    ) -> None:
        """Unknown schedule records persist their stable review key without inventing IDs."""
        item = replace(
            self.removal_item(False),
            tag="",
            launched_date=None,
            next_scan_date=None,
            schedule_id=None,
            status="Unknown",
            result="Unknown",
            removed_nws="",
            manual="MANUAL: Missing required Qualys schedule field: id.",
            scan_execution_key="schedule-review:unidentified:stablehash",
        )
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(True,), None, (17,)]
        details = Mock(
            was_report_poc=None,
            tech_poc_email=None,
            distro_email=None,
            comments=None,
            report_password=None,
        )
        with patch(
            "was_reports.tracker.update_service.connect", return_value=conn
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.resolve_stakeholder_details",
            return_value=details,
        ), patch(
            "was_reports.tracker.update_service.count_webapps"
        ) as count, patch(
            "was_reports.tracker.update_service.upsert_assignee",
            return_value=Mock(id=1, name="Analyst"),
        ), patch(
            "was_reports.tracker.update_service.update_stakeholder_scan_metadata"
        ) as metadata, patch(
            "was_reports.tracker.update_service.has_live_numbered_run_overlap"
        ) as overlap:
            self.assertEqual(update_tracker(Mock(), [item], False), 1)
        count.assert_not_called()
        metadata.assert_not_called()
        overlap.assert_not_called()
        insert_call = next(
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO" in str(call.args[0])
        )
        names = [
            field.name for field in fields(DailyReportTrackerRow) if field.name != "id"
        ]
        values = dict(zip(names, insert_call.args[1]))
        self.assertIsNone(values["schedule_id"])
        self.assertIsNone(values["scan_start_date"])
        self.assertEqual(values["scan_execution_key"], item.scan_execution_key)

    def test_unidentified_review_lock_uses_stable_key_not_shared_null_schedule(
        self,
    ) -> None:
        """Different unidentified records do not share a lock while repeats do."""
        base = replace(
            self.removal_item(False),
            schedule_id=None,
            launched_date=None,
            status="Unknown",
            result="Unknown",
            manual="MANUAL: Missing required Qualys schedule field: id.",
        )
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True,)
        items = [
            replace(
                base, scan_execution_key="schedule-review:unidentified:{}".format(value)
            )
            for value in ("first", "second", "first")
        ]
        with patch(
            "was_reports.tracker.update_service.connect", return_value=conn
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.update_execution", return_value=1
        ):
            self.assertEqual(update_tracker(Mock(), items, False), 3)
        locks = [
            call.args[1][0]
            for call in cursor.execute.call_args_list
            if "pg_try_advisory_lock" in str(call.args[0])
        ]
        self.assertEqual(locks[0], locks[2])
        self.assertNotEqual(locks[0], locks[1])

    def test_missing_next_date_clears_stale_next_metadata(self) -> None:
        """Keep the actual last launch while clearing an absent next date."""
        with patch(
            "was_reports.tracker.update_service.update_scan_metadata_for_tag"
        ) as metadata:
            update_stakeholder_scan_metadata("TAG", "2026-09-01T00:00:00Z", None, 2)
        self.assertEqual(metadata.call_args.kwargs["last_scanned"], 1788220800)
        self.assertIsNone(metadata.call_args.kwargs["next_scheduled"])
        self.assertIsNone(convert_qualys_date(None))

    def test_schedule_review_manual_admitted_with_explicit_identity(self) -> None:
        """Schedule exceptions enter the tracker without invented execution dates."""
        item = replace(
            self.removal_item(False),
            launched_date=None,
            status="Unknown",
            result="Unknown",
            manual="MANUAL: Missing required Qualys schedule field: lastScan/launchedDate.",
            scan_execution_key="schedule-review:1",
        )
        with patch(
            "was_reports.tracker.update_service.connect", return_value=MagicMock()
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.update_execution", return_value=1
        ) as update:
            self.assertEqual(update_tracker(Mock(), [item], False), 1)
        self.assertEqual(update.call_args.args[-1], "schedule-review:1")

    def test_schedule_review_manual_recovery_promotes_identity_safely(self) -> None:
        """Update a recoverable schedule review in place using the actual execution key."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = "MANUAL: Missing required Qualys schedule field: lastScan/launchedDate."
        cursor.fetchone.side_effect = [
            (17, "Unknown", "Unknown", note, "schedule-review:1"),
            (False,),
        ]
        cursor.rowcount = 1
        item = replace(
            self.removal_item(False), removed_nws="", scan_name="Customer Run #1"
        )
        cursor.fetchall.return_value = []
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(
                tag="RECOVERED",
                poc="Contact",
                poc_email="contact@example.test",
                customer_notes="Rebuilt customer notes",
                legacy_password="STATIC PASSWORD",
                report_scan_notes="",
            ),
        ):
            self.assertEqual(
                update_execution(
                    Mock(), item, False, date.today(), "Analyst", conn, "actual-key"
                ),
                1,
            )
        query, values = cursor.execute.call_args.args
        overlap_queries = [
            str(call.args[0])
            for call in cursor.execute.call_args_list
            if "SELECT scan_name" in str(call.args[0])
        ]
        self.assertEqual(len(overlap_queries), 1)
        self.assertIn("NOT LIKE 'schedule-review:%%'", overlap_queries[0])
        self.assertIn("scan_execution_key", str(query))
        self.assertIn("NOT EXISTS (SELECT 1 FROM was_report_runs", str(query))
        self.assertEqual(
            values[-8:],
            [
                "RECOVERED",
                "Contact",
                "contact@example.test",
                "Rebuilt customer notes",
                "STATIC PASSWORD",
                "actual-key",
                17,
                note,
            ],
        )

    def test_schedule_review_promotion_holds_conflicting_numbered_execution(
        self,
    ) -> None:
        """An unrelated recorded numbered run prevents promotion into a duplicate run."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = "MANUAL: Missing required Qualys schedule field: lastScan/launchedDate."
        cursor.fetchone.side_effect = [
            (17, "Unknown", "Unknown", note, "schedule-review:1"),
            (False,),
        ]
        item = replace(
            self.removal_item(False), removed_nws="", scan_name="Customer Run #1"
        )
        with patch(
            "was_reports.tracker.update_service.build_tracker_row"
        ) as build, patch(
            "was_reports.tracker.update_service.has_live_numbered_run_overlap",
            return_value=True,
        ) as overlap, self.assertLogs(
            "was_reports.tracker.update_service", level="WARNING"
        ):
            self.assertEqual(
                update_execution(
                    Mock(), item, False, date.today(), "Analyst", conn, "actual-key"
                ),
                0,
            )
        overlap.assert_called_once_with(item, "actual-key", conn)
        build.assert_not_called()
        self.assertNotIn(
            "UPDATE was_daily_report_tracker", str(cursor.execute.call_args_list)
        )

    def test_actual_key_schedule_manual_is_not_treated_as_review_promotion(
        self,
    ) -> None:
        """Schedule notes alone do not trigger identity or contact rewriting."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = "MANUAL: Missing required Qualys schedule field: nextLaunchDate."
        cursor.fetchone.side_effect = [
            (17, "Finished", "Successful", note, "actual-key"),
            (False,),
        ]
        cursor.rowcount = 1
        item = replace(self.removal_item(False), removed_nws="")
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(report_scan_notes=""),
        ), patch(
            "was_reports.tracker.update_service.has_live_numbered_run_overlap"
        ) as overlap:
            self.assertEqual(
                update_execution(
                    Mock(), item, False, date.today(), "Analyst", conn, "actual-key"
                ),
                1,
            )
        overlap.assert_not_called()
        query = str(cursor.execute.call_args.args[0])
        self.assertNotIn("scan_execution_key", query)
        self.assertNotIn("poc_email", query)

    def test_repeated_schedule_review_updates_without_changing_identity(self) -> None:
        """Repeated discovery exceptions refresh one review row with unknown dates."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = "MANUAL: Missing required Qualys schedule field: lastScan/launchedDate."
        cursor.fetchone.side_effect = [
            (17, "Unknown", "Unknown", note, "schedule-review:1"),
            (False,),
        ]
        cursor.rowcount = 1
        item = replace(
            self.removal_item(False),
            launched_date=None,
            removed_nws="",
            manual=note,
            status="Unknown",
            result="Unknown",
            scan_execution_key="schedule-review:1",
        )
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(report_scan_notes=note),
        ):
            self.assertEqual(
                update_execution(
                    Mock(),
                    item,
                    False,
                    date.today(),
                    "Analyst",
                    conn,
                    "schedule-review:1",
                ),
                1,
            )
        query, values = cursor.execute.call_args.args
        self.assertIn("UPDATE was_daily_report_tracker", str(query))
        self.assertNotIn("scan_execution_key", str(query))
        self.assertEqual(values[-2:], [17, note])

    def test_schedule_manual_does_not_admit_running_candidate(self) -> None:
        """A schedule field diagnosis cannot manufacture a completed running scan."""
        item = replace(
            self.removal_item(False),
            status="Running",
            result="Processing",
            manual="MANUAL: Missing required Qualys schedule field: nextLaunchDate.",
            scan_execution_key="schedule-review:1",
        )
        with patch(
            "was_reports.tracker.update_service.connect"
        ) as connect_db, self.assertLogs(
            "was_reports.tracker.update_service", level="WARNING"
        ):
            self.assertEqual(update_tracker(Mock(), [item], False), 0)
        connect_db.assert_not_called()

    def test_unknown_date_schedule_review_bypasses_completed_run_overlap(self) -> None:
        """A metadata investigation stays visible alongside an existing completed run."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (17,)]
        item = replace(
            self.removal_item(False),
            launched_date=None,
            removed_nws="",
            scan_name="Customer Run #1",
            status="Unknown",
            result="Unknown",
            manual="MANUAL: Missing required Qualys schedule field: lastScan/launchedDate.",
            scan_execution_key="schedule-review:1",
        )
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(report_scan_notes=item.manual),
        ), patch(
            "was_reports.tracker.update_service.has_live_numbered_run_overlap",
            return_value=True,
        ) as overlap:
            self.assertEqual(
                update_execution(
                    Mock(),
                    item,
                    False,
                    date.today(),
                    "Analyst",
                    conn,
                    "schedule-review:1",
                ),
                1,
            )
        overlap.assert_not_called()
        self.assertIn("INSERT INTO", str(cursor.execute.call_args.args[0]))

    def test_actual_launch_schedule_manual_retains_completed_run_overlap_guard(
        self,
    ) -> None:
        """A real execution with missing metadata still requires overlap reconciliation."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        item = replace(
            self.removal_item(False),
            removed_nws="",
            scan_name="Customer Run #1",
            manual="MANUAL: Missing required Qualys schedule field: nextLaunchDate.",
        )
        with patch(
            "was_reports.tracker.update_service.build_tracker_row"
        ) as build, patch(
            "was_reports.tracker.update_service.has_live_numbered_run_overlap",
            return_value=True,
        ) as overlap, self.assertLogs(
            "was_reports.tracker.update_service", level="WARNING"
        ):
            self.assertEqual(
                update_execution(
                    Mock(), item, False, date.today(), "Analyst", conn, "actual-key"
                ),
                0,
            )
        overlap.assert_called_once()
        build.assert_not_called()

    def test_claimed_schedule_review_blocks_identity_promotion(self) -> None:
        """A claimed or sent review cannot be replaced with a duplicate execution."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = "MANUAL: Missing required Qualys schedule field: lastScan/launchedDate."
        cursor.fetchone.side_effect = [
            (17, "Unknown", "Unknown", note, "schedule-review:1"),
            (True,),
        ]
        with patch("was_reports.tracker.update_service.build_tracker_row") as build:
            self.assertEqual(
                update_execution(
                    Mock(),
                    self.removal_item(False),
                    False,
                    date.today(),
                    "Analyst",
                    conn,
                    "actual-key",
                ),
                0,
            )
        build.assert_not_called()
        self.assertNotIn("INSERT INTO", str(cursor.execute.call_args_list))

    def test_metadata_error_log_omits_exception_payload(self) -> None:
        """Retain safe operation context without SQL values or tracebacks."""
        with patch(
            "was_reports.tracker.update_service.update_scan_metadata_for_tag",
            side_effect=ValueError("private-query-value"),
        ), self.assertLogs("was_reports.tracker.update_service", level="ERROR") as logs:
            update_stakeholder_scan_metadata(
                "TAG", "2026-09-01T00:00:00Z", "2026-10-01T00:00:00Z", 1
            )
        self.assertIn("TAG: ValueError", logs.output[0])
        self.assertNotIn("private-query-value", "".join(logs.output))
        self.assertIsNone(logs.records[0].exc_info)

    def test_consolidation_error_log_omits_exception_payload(self) -> None:
        """Consolidation failures log only safe metadata and error details."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-01T00:00:00Z",
            1,
            "MONTHLY",
        )
        with patch(
            "was_reports.tracker.item_builder.element_text",
            side_effect=ValueError("private-response-payload"),
        ), self.assertLogs("was_reports.tracker.item_builder", level="ERROR") as logs:
            items = create_tracker_items(
                Mock(), {"TAG": [Mock()]}, {"TAG": stakeholder}, set()
            )
        self.assertEqual(items[0].manual, "MANUAL")
        self.assertIn("ValueError", logs.output[0])
        self.assertIn("holding the execution for a later refresh", logs.output[0])
        self.assertNotIn("marking it manual", logs.output[0])
        self.assertNotIn("private-response-payload", "".join(logs.output))
        self.assertIsNone(logs.records[0].exc_info)

    @patch(
        "was_reports.tracker.item_builder.stakeholder_flags",
        return_value=("", False),
    )
    def test_ordinary_result_tolerates_missing_webapp_url(
        self,
        mock_flags,
    ) -> None:
        """Do not hold an ordinary result when its unused URL is absent."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-01T00:00:00Z",
            1,
            "MONTHLY",
            "TAG",
        )
        for result, expected_result in (
            ("SUCCESSFUL", "Successful"),
            ("SERVICE_ERROR", "Service Error"),
            ("TIME_LIMIT_REACHED", "Time Limit Reached"),
        ):
            with self.subTest(result=result):
                scan = etree.fromstring(
                    (
                        "<WasScan><name>Customer Run #1</name>"
                        "<status>FINISHED</status><summary>"
                        "<resultsStatus>{}</resultsStatus></summary>"
                        "</WasScan>"
                    )
                    .format(result)
                    .encode("utf-8")
                )

                item = create_tracker_items(
                    Mock(), {"run": [scan]}, {"run": stakeholder}, set()
                )[0]

                self.assertEqual(item.status, "Finished")
                self.assertEqual(item.result, expected_result)
                self.assertEqual(item.manual, "")
                self.assertEqual(item.qualys_errors, "")

    def test_customer_list_results_still_require_webapp_url(self) -> None:
        """Record terminal scans as manual when their required URL is absent."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-01T00:00:00Z",
            1,
            "MONTHLY",
            "TAG",
        )
        for status, result in (
            ("FINISHED", "NO_WEB_SERVICE"),
            ("ERROR", "SCAN_INTERNAL_ERROR"),
            ("ERROR", "SCAN_RESULTS_INVALID"),
        ):
            with self.subTest(result=result):
                scan = etree.fromstring(
                    (
                        "<WasScan><name>Customer Run #1</name><status>{}</status>"
                        "<summary><resultsStatus>{}</resultsStatus></summary>"
                        "</WasScan>"
                    )
                    .format(status, result)
                    .encode("utf-8")
                )
                with self.assertLogs(
                    "was_reports.tracker.item_builder", level="ERROR"
                ) as logs:
                    item = create_tracker_items(
                        Mock(), {"run": [scan]}, {"run": stakeholder}, set()
                    )[0]

                self.assertEqual(item.scan_name, "Customer Run #1")
                self.assertEqual(
                    item.status, "Error" if status == "ERROR" else "Finished"
                )
                self.assertTrue(item.result)
                self.assertEqual(
                    item.manual,
                    "{}target/webApp/url.".format(MISSING_QUALYS_FIELD_NOTE_PREFIX),
                )
                self.assertIn("target/webApp/url", item.qualys_errors)
                self.assertIn("marking the completed execution manual", logs.output[0])
                with patch(
                    "was_reports.tracker.update_service.connect",
                    return_value=MagicMock(),
                ), patch(
                    "was_reports.tracker.update_service.active_assignees",
                    return_value=["Analyst"],
                ), patch(
                    "was_reports.tracker.update_service.update_execution",
                    return_value=1,
                ) as update:
                    self.assertEqual(update_tracker(Mock(), [item], False), 1)
                self.assertEqual(update.call_args.args[1], item)

    def test_missing_summary_is_inserted_with_manual_reason(self) -> None:
        """Persist known scan identity and timing without guessing a result."""
        scan = etree.fromstring(
            b"<WasScan><name>Customer Run #1 Slice 1</name><status>FINISHED</status>"
            b"<launchedDate>2026-09-01T00:00:00Z</launchedDate>"
            b"<endScanDate>2026-09-01T01:00:00Z</endScanDate></WasScan>"
        )
        stakeholder = TrackerStakeholder(
            "Customer",
            9,
            "2026-10-01T00:00:00Z",
            "2026-09-01T00:00:00Z",
            1,
            "MONTHLY",
            "TAG",
        )
        with self.assertLogs("was_reports.tracker.item_builder", level="ERROR"):
            item = create_tracker_items(
                Mock(), {"run": [scan]}, {"run": stakeholder}, set()
            )[0]
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(True,), None, (17,)]
        details = Mock(
            was_report_poc="POC",
            tech_poc_email=None,
            distro_email=None,
            comments=None,
            report_password=None,
        )
        with patch(
            "was_reports.tracker.update_service.connect", return_value=conn
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.resolve_stakeholder_details",
            return_value=details,
        ), patch(
            "was_reports.tracker.update_service.count_webapps", return_value=1
        ), patch(
            "was_reports.tracker.update_service.upsert_assignee",
            return_value=Mock(id=1, name="Analyst"),
        ), patch(
            "was_reports.tracker.update_service.update_stakeholder_scan_metadata"
        ), patch(
            "was_reports.tracker.update_service.has_live_numbered_run_overlap",
            return_value=False,
        ):
            self.assertEqual(update_tracker(Mock(), [item], False), 1)
        insert = next(
            call
            for call in cursor.execute.call_args_list
            if "INSERT INTO was_daily_report_tracker" in str(call.args[0])
        )
        names = [
            field.name for field in fields(DailyReportTrackerRow) if field.name != "id"
        ]
        values = dict(zip(names, insert.args[1]))
        self.assertEqual(values["scan_name"], "Customer Run #1")
        self.assertEqual(values["status"], "Finished")
        self.assertEqual(values["result"], "Unknown")
        self.assertEqual(
            values["report_scan_notes"],
            "{}summary.".format(MISSING_QUALYS_FIELD_NOTE_PREFIX),
        )
        self.assertEqual(
            values["qualys_error"], "Missing required Qualys scan field: summary"
        )
        self.assertEqual(
            values["scan_execution_key"], "schedule:1:2026-09-01T00:00:00+00:00"
        )
        self.assertEqual(values["tag_id"], 9)
        self.assertEqual(
            values["scan_started_at"], datetime(2026, 9, 1, tzinfo=timezone.utc)
        )
        self.assertEqual(
            values["scan_ended_at"], datetime(2026, 9, 1, 1, tzinfo=timezone.utc)
        )
        self.assertIsNone(values["template"])

    def test_missing_result_field_distinguishes_present_summary(self) -> None:
        """Name the missing child field rather than blaming a present summary."""
        for summary in (
            "<summary/>",
            "<summary><resultsStatus> </resultsStatus></summary>",
        ):
            with self.subTest(summary=summary):
                scan = etree.fromstring(
                    (
                        "<WasScan><name>Customer Run #1</name><status>FINISHED</status>"
                        "{}</WasScan>".format(summary)
                    ).encode("utf-8")
                )
                stakeholder = TrackerStakeholder(
                    "Customer",
                    1,
                    "2026-10-01T00:00:00Z",
                    "2026-09-01T00:00:00Z",
                    1,
                    "MONTHLY",
                    "TAG",
                )
                with self.assertLogs("was_reports.tracker.item_builder", level="ERROR"):
                    item = create_tracker_items(
                        Mock(), {"run": [scan]}, {"run": stakeholder}, set()
                    )[0]
                self.assertIn("summary/resultsStatus", item.manual)
                self.assertIn("summary/resultsStatus", item.qualys_errors)
                self.assertEqual(item.result, "Unknown")

    def test_missing_fields_on_nonterminal_scans_remain_unclaimed(self) -> None:
        """Missing fields cannot make running or unknown executions terminal."""
        for status in ("RUNNING", "PROCESSING", "", "UNKNOWN"):
            with self.subTest(status=status):
                scan = etree.fromstring(
                    (
                        "<WasScan><name>Customer Run #1</name><status>{}</status></WasScan>".format(
                            status
                        )
                    ).encode("utf-8")
                )
                stakeholder = TrackerStakeholder(
                    "Customer",
                    1,
                    "2026-10-01T00:00:00Z",
                    "2026-09-01T00:00:00Z",
                    1,
                    "MONTHLY",
                    "TAG",
                )
                with self.assertLogs("was_reports.tracker.item_builder", level="ERROR"):
                    item = create_tracker_items(
                        Mock(), {"run": [scan]}, {"run": stakeholder}, set()
                    )[0]
                with patch(
                    "was_reports.tracker.update_service.connect"
                ) as connect, self.assertLogs(
                    "was_reports.tracker.update_service", level="WARNING"
                ):
                    self.assertEqual(update_tracker(Mock(), [item], False), 0)
                connect.assert_not_called()

    def test_missing_field_does_not_override_processing_result(self) -> None:
        """A terminal status with processing results must remain unclaimed."""
        scan = etree.fromstring(
            b"<WasScan><status>FINISHED</status>"
            b"<summary><resultsStatus>PROCESSING</resultsStatus></summary></WasScan>"
        )
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-01T00:00:00Z",
            1,
            "MONTHLY",
            "TAG",
        )
        with self.assertLogs("was_reports.tracker.item_builder", level="ERROR"):
            item = create_tracker_items(
                Mock(), {"run": [scan]}, {"run": stakeholder}, set()
            )[0]
        self.assertEqual(item.status, "")
        self.assertEqual(item.result, "")

    def test_http_failure_is_held_without_exposing_response(self) -> None:
        """Request failures cannot be relabeled as missing-field manuals."""
        scan = etree.fromstring(
            b"<WasScan><name>Customer Run #1</name><status>FINISHED</status>"
            b"<summary><resultsStatus>SUCCESSFUL</resultsStatus></summary></WasScan>"
        )
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-01T00:00:00Z",
            1,
            "MONTHLY",
            "TAG",
        )
        with patch(
            "was_reports.tracker.item_builder.create_multiscan",
            side_effect=requests.HTTPError("private response contents"),
        ), self.assertLogs("was_reports.tracker.item_builder", level="ERROR") as logs:
            item = create_tracker_items(
                Mock(), {"run": [scan]}, {"run": stakeholder}, set()
            )[0]
        self.assertEqual(item.status, "")
        self.assertEqual(item.result, "")
        self.assertNotIn("private response contents", "".join(logs.output))
        self.assertIn("holding the execution for a later refresh", logs.output[0])

    def setUp(self) -> None:
        """Keep legacy database inspection isolated from update flow tests."""
        legacy_patch = patch(
            "was_reports.tracker.update_service.has_legacy_execution_overlap",
            return_value=False,
        )
        self.mock_legacy_overlap = legacy_patch.start()
        self.addCleanup(legacy_patch.stop)

    def test_legacy_overlap_uses_actual_eastern_scan_day(self) -> None:
        """Check legacy schedule/day without manufacturing an execution key."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (True,)
        self.assertTrue(has_legacy_execution_overlap(self.removal_item(False), conn))
        query, parameters = cursor.execute.call_args.args
        self.assertIn("scan_execution_key IS NULL", query)
        self.assertIn("scan_execution_key LIKE 'legacy-import:%%'", query)
        self.assertEqual(parameters, (1, date(2026, 8, 31)))
        cursor.fetchone.return_value = (False,)
        self.assertFalse(has_legacy_execution_overlap(self.removal_item(False), conn))

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

    def test_qualys_error_webapps_remain_eligible_for_results(self) -> None:
        """Keep a completed scan with error webapps in the automated flow."""
        item = replace(
            self.removal_item(False),
            status="Error",
            result="Scan Internal Error",
            nws=False,
            recent_nws="",
            removed_nws="",
            qualys_errors="https://error.example.gov<br>",
        )

        fields = tracker_result_fields(item, 10, True, "")

        self.assertEqual(fields, ("10", "Results", ""))

    def test_error_without_qualys_error_webapps_uses_legacy_results_flow(self) -> None:
        """Do not make status alone a manual trigger under legacy rules."""
        item = replace(
            self.removal_item(False),
            status="Error",
            result="Scan Internal Error",
            nws=False,
            recent_nws="",
            removed_nws="",
        )

        fields = tracker_result_fields(item, 10, True, "")

        self.assertEqual(fields, ("10", "Results", ""))

    def test_explicit_manual_overrides_qualys_error_automation(self) -> None:
        """Preserve an explicit legacy manual classification for error scans."""
        item = replace(
            self.removal_item(False),
            status="Error",
            result="Scan Results Invalid",
            nws=False,
            recent_nws="",
            removed_nws="",
            manual="MANUAL",
            qualys_errors="https://error.example.gov<br>",
        )

        fields = tracker_result_fields(item, 10, True, item.manual)

        self.assertEqual(fields, (None, None, "MANUAL"))

    def test_failed_inventory_does_not_deactivate_stakeholder(self) -> None:
        """Unknown inventory must not select an automatic NWS template."""
        fields = tracker_result_fields(self.removal_item(False), 0, False, "MANUAL")
        self.assertEqual(fields, (None, None, "MANUAL"))

    def test_claim_precedes_deletion_and_success_finalization(self) -> None:
        """Commit a new claim before deletion and finalize only after success."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (17,)]
        row = DailyReportTrackerRow(tag="TAG")
        cursor.rowcount = 1
        sequence = Mock()
        sequence.attach_mock(conn.commit, "commit")
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=row,
        ), patch(
            "was_reports.tracker.update_service.delete_validated_webapp"
        ) as delete, patch(
            "was_reports.tracker.update_service.lock_tracker_tag"
        ) as tag_lock:
            sequence.attach_mock(tag_lock, "lock")
            sequence.attach_mock(delete, "delete")
            update_execution(
                Mock(),
                self.removal_item(False),
                True,
                date.today(),
                "Analyst",
                conn,
                "execution",
            )
        self.assertEqual(
            [entry[0] for entry in sequence.mock_calls],
            ["lock", "commit", "lock", "delete", "commit"],
        )
        self.assertEqual(tag_lock.call_count, 2)
        self.assertEqual(
            cursor.execute.call_args.args[1],
            ("Targets Removed", "", 17, "MANUAL QUALYS DELETION PENDING"),
        )

    @patch("was_reports.tracker.update_service.delete_webapp")
    @patch("was_reports.tracker.update_service.validate_deletion_claim")
    @patch("was_reports.tracker.update_service.validate_latest_deletion_execution")
    @patch("was_reports.tracker.update_service.validate_webapp_tags")
    @patch("was_reports.tracker.update_service.find_webapp_identity")
    def test_deletion_revalidates_stable_identity_immediately_before_delete(
        self, find_identity, validate_tags, validate_latest, validate_claim, delete
    ) -> None:
        """Bind deletion to two matching identity reads and all current guards."""
        identity = WebAppIdentity("42", "https://example.gov", ("9",))
        find_identity.side_effect = [identity, identity]
        conn = MagicMock()
        item = self.removal_item(False)

        delete_validated_webapp(
            Mock(), conn, 17, item, "execution", "https://example.gov"
        )

        self.assertEqual(find_identity.call_count, 2)
        validate_tags.assert_called_once_with(conn, identity, 9)
        validate_latest.assert_called_once()
        validate_claim.assert_called_once_with(conn, 17, item, "execution")
        delete.assert_called_once_with(
            unittest.mock.ANY,
            "https://example.gov",
            webapp_id="42",
        )

    @patch("was_reports.tracker.update_service.delete_webapp")
    @patch("was_reports.tracker.update_service.find_webapp_identity")
    def test_changed_webapp_identity_routes_to_manual_without_delete(
        self, find_identity, delete
    ) -> None:
        """Reject a URL whose Qualys object identity changed between reads."""
        find_identity.side_effect = [
            WebAppIdentity("42", "https://example.gov", ("9",)),
            WebAppIdentity("43", "https://example.gov", ("9",)),
        ]

        with self.assertRaisesRegex(RuntimeError, "identity changed"):
            delete_validated_webapp(
                Mock(),
                MagicMock(),
                17,
                self.removal_item(False),
                "execution",
                "https://example.gov",
            )
        delete.assert_not_called()

    @patch("was_reports.tracker.update_service.delete_webapp")
    @patch("was_reports.tracker.update_service.validate_deletion_claim")
    @patch("was_reports.tracker.update_service.validate_latest_deletion_execution")
    @patch("was_reports.tracker.update_service.validate_webapp_tags")
    @patch("was_reports.tracker.update_service.find_webapp_identity")
    def test_changed_tag_or_execution_never_reaches_delete(
        self, find_identity, validate_tags, validate_latest, validate_claim, delete
    ) -> None:
        """Stop the destructive call when either current safety guard changes."""
        identity = WebAppIdentity("42", "https://example.gov", ("9",))
        find_identity.side_effect = [identity, identity, identity, identity]
        for guard, message in (
            (validate_tags, "tag changed"),
            (validate_latest, "execution changed"),
        ):
            with self.subTest(message=message):
                validate_tags.reset_mock(side_effect=True)
                validate_latest.reset_mock(side_effect=True)
                validate_claim.reset_mock(side_effect=True)
                guard.side_effect = RuntimeError(message)
                with self.assertRaisesRegex(RuntimeError, message):
                    delete_validated_webapp(
                        Mock(),
                        MagicMock(),
                        17,
                        self.removal_item(False),
                        "execution",
                        "https://example.gov",
                    )
        delete.assert_not_called()

    def test_changed_or_multiple_stakeholder_tags_block_deletion(self) -> None:
        """Require the expected tag and no second configured stakeholder tag."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        for identity, configured, message in (
            (
                WebAppIdentity("42", "https://example.gov", ("10",)),
                [],
                "tag changed",
            ),
            (
                WebAppIdentity("42", "https://example.gov", ("9", "10")),
                [(9,), (10,)],
                "multiple stakeholder tags",
            ),
        ):
            with self.subTest(message=message):
                cursor.fetchall.return_value = configured
                with self.assertRaisesRegex(RuntimeError, message):
                    validate_webapp_tags(conn, identity, 9)

    @patch("was_reports.tracker.update_service.search_schedules")
    def test_changed_latest_execution_blocks_deletion(self, search) -> None:
        """Reject deletion after Qualys advances the schedule execution."""
        search.return_value = {
            "new": TrackerStakeholder(
                name="Customer",
                tag_id=9,
                next_scan_date=None,
                launched_date="2026-09-02T00:00:00Z",
                schedule_id=1,
                cadence="MONTHLY",
                tag="TAG",
                latest_scan_status="FINISHED",
            )
        }

        with self.assertRaisesRegex(RuntimeError, "execution changed"):
            validate_latest_deletion_execution(
                Mock(), self.removal_item(False), "execution"
            )

    def test_duplicate_and_pending_claims_never_delete(self) -> None:
        """Completed, pending, and report-linked executions are not replayed."""
        for existing in (
            (17, "Finished", "No Web Service", "", "existing-key"),
            (
                17,
                "Finished",
                "No Web Service",
                "MANUAL QUALYS DELETION FAILED",
                "existing-key",
            ),
            (
                17,
                "Finished",
                "No Web Service",
                "MANUAL QUALYS DELETION PENDING",
                "existing-key",
            ),
            (17, "Running", "Running", "", "existing-key"),
        ):
            conn = MagicMock()
            cursor = conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [existing, (True,)]
            with patch(
                "was_reports.tracker.update_service.delete_validated_webapp"
            ) as delete:
                update_execution(
                    Mock(),
                    self.removal_item(False),
                    True,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                )
                delete.assert_not_called()

    def test_failure_remains_manual_and_default_does_not_delete(self) -> None:
        """Failures cannot claim removal and default mode has no deletion."""
        for enabled in (False, True):
            conn = MagicMock()
            cursor = conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [None, (17,)]
            cursor.rowcount = 1
            with patch(
                "was_reports.tracker.update_service.build_tracker_row",
                return_value=DailyReportTrackerRow(tag="TAG"),
            ), patch(
                "was_reports.tracker.update_service.delete_validated_webapp",
                side_effect=RuntimeError("failure"),
            ) as delete, patch(
                "was_reports.tracker.update_service.record_tracker_digest_failure"
            ) as digest_failure:
                if enabled:
                    with self.assertRaises(RuntimeError):
                        update_execution(
                            Mock(),
                            self.removal_item(False),
                            enabled,
                            date.today(),
                            "Analyst",
                            conn,
                            "execution",
                        )
                    self.assertEqual(
                        cursor.execute.call_args.args[1],
                        (
                            "MANUAL QUALYS DELETION FAILED",
                            17,
                            "MANUAL QUALYS DELETION PENDING",
                        ),
                    )
                    digest_failure.assert_called_once_with(17, conn)
                else:
                    update_execution(
                        Mock(),
                        self.removal_item(False),
                        enabled,
                        date.today(),
                        "Analyst",
                        conn,
                        "execution",
                    )
                    delete.assert_not_called()

    def test_changed_deletion_note_is_not_overwritten_or_reported_successful(
        self,
    ) -> None:
        """Lost finalization ownership preserves operator changes and raises."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (17,)]
        cursor.rowcount = 0
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(tag="TAG"),
        ), patch("was_reports.tracker.update_service.delete_validated_webapp"), patch(
            "was_reports.tracker.update_service.record_tracker_digest_failure"
        ) as digest_failure, self.assertLogs(
            "was_reports.tracker.update_service", level="ERROR"
        ):
            with self.assertRaisesRegex(RuntimeError, "manual reconciliation"):
                update_execution(
                    Mock(),
                    self.removal_item(False),
                    True,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                )
        digest_failure.assert_not_called()
        self.assertIn("AND report_scan_notes = %s", cursor.execute.call_args.args[0])

    def test_saved_required_row_can_be_explicitly_claimed(self) -> None:
        """Only explicit opt-in without a report may transition REQUIRED to PENDING."""
        for enabled, report_exists in ((True, False), (True, True), (False, False)):
            conn = MagicMock()
            cursor = conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [
                (
                    17,
                    "Finished",
                    "No Web Service",
                    "QUALYS DELETION REQUIRED",
                    "existing-key",
                ),
                (report_exists,),
            ]
            cursor.rowcount = 1
            sequence = Mock()
            sequence.attach_mock(conn.commit, "commit")
            with patch(
                "was_reports.tracker.update_service.build_tracker_row",
                return_value=DailyReportTrackerRow(),
            ), patch(
                "was_reports.tracker.update_service.delete_validated_webapp"
            ) as delete:
                sequence.attach_mock(delete, "delete")
                count = update_execution(
                    Mock(),
                    self.removal_item(False),
                    enabled,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                )
            if enabled and not report_exists:
                self.assertEqual(count, 1)
                self.assertEqual(
                    [entry[0] for entry in sequence.mock_calls],
                    ["commit", "delete", "commit"],
                )
                claim = next(
                    call
                    for call in cursor.execute.call_args_list
                    if "UPDATE was_daily_report_tracker SET" in str(call.args[0])
                )
                self.assertEqual(claim.args[1][-2:], [17, "QUALYS DELETION REQUIRED"])
                self.assertIn("MANUAL QUALYS DELETION PENDING", claim.args[1])
            else:
                self.assertEqual(count, 0)
                delete.assert_not_called()

    def test_changed_preview_claim_never_deletes(self) -> None:
        """An operator change between inspection and claim prevents deletion."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (
                17,
                "Finished",
                "No Web Service",
                "QUALYS DELETION REQUIRED",
                "existing-key",
            ),
            (False,),
        ]
        cursor.rowcount = 0
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(),
        ), patch(
            "was_reports.tracker.update_service.delete_validated_webapp"
        ) as delete:
            self.assertEqual(
                update_execution(
                    Mock(),
                    self.removal_item(False),
                    True,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                ),
                0,
            )
            delete.assert_not_called()
        conn.commit.assert_not_called()

    def test_lost_insert_claim_does_not_delete(self) -> None:
        """A conflicting insert cannot grant ownership of destructive work."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, None]
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(tag="TAG"),
        ), patch(
            "was_reports.tracker.update_service.delete_validated_webapp"
        ) as delete:
            update_execution(
                Mock(),
                self.removal_item(False),
                True,
                date.today(),
                "Analyst",
                conn,
                "execution",
            )
            delete.assert_not_called()

    def test_incomplete_existing_row_can_transition_before_report_claim(
        self,
    ) -> None:
        """An unreported running row accepts the final scan result."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (17, "Running", "Running", "", "existing-key"),
            (False,),
        ]
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(status="Finished"),
        ), patch(
            "was_reports.tracker.update_service.delete_validated_webapp"
        ) as delete:
            update_execution(
                Mock(),
                self.removal_item(False),
                False,
                date.today(),
                "Analyst",
                conn,
                "execution",
            )
            delete.assert_not_called()
        self.assertEqual(cursor.execute.call_args.args[1][-2], 17)
        update_sql = repr(cursor.execute.call_args.args[0])
        for protected_field in (
            "digest_revision",
            "assignee_emailed_at",
            "assignee_email_message_id",
            "assignee_email_error",
            "assignee_id",
            "data_pull_date",
        ):
            self.assertNotIn(protected_field, update_sql)
        conn.commit.assert_called_once()

    def test_missing_field_manual_can_recover_in_the_same_row(self) -> None:
        """Replace an unclaimed missing-field manual with a complete result."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        note = "{}summary.".format(MISSING_QUALYS_FIELD_NOTE_PREFIX)
        cursor.fetchone.side_effect = [
            (17, "Finished", "Unknown", note, "existing-key"),
            (False,),
        ]
        cursor.rowcount = 1
        item = replace(self.removal_item(False), removed_nws="")
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(
                status="Finished",
                result="Successful",
                report_scan_notes="",
            ),
        ), patch(
            "was_reports.tracker.update_service.delete_validated_webapp"
        ) as delete:
            self.assertEqual(
                update_execution(
                    Mock(),
                    item,
                    False,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                ),
                1,
            )
        query, values = cursor.execute.call_args.args
        self.assertIn("UPDATE was_daily_report_tracker", str(query))
        self.assertIn("NOT EXISTS (SELECT 1 FROM was_report_runs", str(query))
        self.assertEqual(values[1:4], ["Finished", "Successful", ""])
        self.assertEqual(values[-2:], [17, note])
        delete.assert_not_called()
        conn.commit.assert_called_once()

    def test_missing_field_manual_claim_prevents_recovery(self) -> None:
        """Keep a manual row intact when a report claim or sent marker exists."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (
                17,
                "Finished",
                "Unknown",
                "{}summary.".format(MISSING_QUALYS_FIELD_NOTE_PREFIX),
                "existing-key",
            ),
            (True,),
        ]
        with patch("was_reports.tracker.update_service.build_tracker_row") as build:
            self.assertEqual(
                update_execution(
                    Mock(),
                    self.removal_item(False),
                    False,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                ),
                0,
            )
        build.assert_not_called()
        self.assertNotIn(
            "UPDATE was_daily_report_tracker", str(cursor.execute.call_args_list)
        )

    def test_missing_field_manual_retains_reason_when_app_count_is_missing(
        self,
    ) -> None:
        """A second enrichment failure must not erase the original diagnosis."""
        note = "{}summary.".format(MISSING_QUALYS_FIELD_NOTE_PREFIX)
        item = replace(self.removal_item(False), manual=note, removed_nws="")
        details = Mock(
            was_report_poc=None,
            tech_poc_email=None,
            distro_email=None,
            comments=None,
            report_password=None,
        )
        with patch(
            "was_reports.tracker.update_service.resolve_stakeholder_details",
            return_value=details,
        ), patch(
            "was_reports.tracker.update_service.count_webapps",
            side_effect=AttributeError("missing count"),
        ), patch(
            "was_reports.tracker.update_service.upsert_assignee",
            return_value=Mock(id=1, name="Analyst"),
        ), patch(
            "was_reports.tracker.update_service.update_stakeholder_scan_metadata"
        ), self.assertLogs(
            "was_reports.tracker.update_service", level="ERROR"
        ):
            row = build_tracker_row(Mock(), item, "Analyst", MagicMock(), date.today())
        self.assertEqual(row.report_scan_notes, note)
        self.assertIsNone(row.template)

    def test_update_count_excludes_skipped_claims(self) -> None:
        """Only committed inserted or updated executions contribute to the count."""
        with patch(
            "was_reports.tracker.update_service.connect",
            return_value=MagicMock(),
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.update_execution",
            side_effect=[1, 0, 1],
        ):
            self.assertEqual(
                update_tracker(Mock(), [self.removal_item(False)] * 3, False),
                2,
            )

    def test_session_lock_is_released_after_failure(self) -> None:
        """Release the execution session lock even when processing fails."""
        conn = MagicMock()
        with patch(
            "was_reports.tracker.update_service.connect", return_value=conn
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.update_execution",
            side_effect=RuntimeError("failure"),
        ):
            with self.assertRaises(RuntimeError):
                update_tracker(Mock(), [self.removal_item(False)], True)
        statements = (
            conn.cursor.return_value.__enter__.return_value.execute.call_args_list
        )
        self.assertEqual(statements[0].args[0], "SELECT pg_try_advisory_lock(%s)")
        self.assertEqual(statements[-1].args[0], "SELECT pg_advisory_unlock(%s)")
        self.assertEqual(statements[0].args[1], statements[-1].args[1])
        conn.close.assert_called_once()

    def test_contended_execution_is_skipped_without_counting_or_unlocking(
        self,
    ) -> None:
        """Contention does not process, count, or unlock another execution."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (False,)
        with patch(
            "was_reports.tracker.update_service.connect", return_value=conn
        ), patch(
            "was_reports.tracker.update_service.active_assignees",
            return_value=["Analyst"],
        ), patch(
            "was_reports.tracker.update_service.update_execution"
        ) as update, self.assertLogs(
            "was_reports.tracker.update_service", level="INFO"
        ) as logs:
            count = update_tracker(Mock(), [self.removal_item(False)], True)
        self.assertEqual(count, 0)
        update.assert_not_called()
        self.assertEqual(cursor.execute.call_count, 1)
        self.assertIn("another refresh holds its lock", logs.output[0])
        conn.rollback.assert_called_once()
        conn.close.assert_called_once()

    def test_preliminary_commit_failure_never_deletes(self) -> None:
        """A failed claim commit cannot authorize a Qualys deletion."""
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchone.side_effect = [
            None,
            (17,),
        ]
        conn.commit.side_effect = RuntimeError("commit failed")
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(),
        ), patch(
            "was_reports.tracker.update_service.delete_validated_webapp"
        ) as delete:
            with self.assertRaises(RuntimeError):
                update_execution(
                    Mock(),
                    self.removal_item(False),
                    True,
                    date.today(),
                    "Analyst",
                    conn,
                    "execution",
                )
            delete.assert_not_called()

    def test_incomplete_input_never_opens_database(self) -> None:
        """Running input cannot reserve the completed execution identity."""
        with patch(
            "was_reports.tracker.update_service.connect"
        ) as connect, self.assertLogs(
            "was_reports.tracker.update_service", level="WARNING"
        ) as logs:
            count = update_tracker(
                Mock(),
                [replace(self.removal_item(False), status="Running")],
                True,
            )
            connect.assert_not_called()
        self.assertEqual(count, 0)
        self.assertIn("Skipping incomplete tracker candidate", logs.output[0])

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
            tag_id=9,
        )


if __name__ == "__main__":
    unittest.main()
