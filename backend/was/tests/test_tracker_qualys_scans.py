"""Tests for production tracker Qualys discovery helpers."""

# Standard Python Libraries
from datetime import datetime, timedelta
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
from lxml import etree
from was_reports.tracker.item_builder import create_multiscan, previous_run_name

# First-Party Libraries
from was_reports.tracker.models import TrackerStakeholder, scheduled_execution_key
from was_reports.tracker.qualys_scans import (
    base_stakeholder_tag,
    build_schedule_search_payload,
    build_scan_search_payload,
    get_previous_nws,
    normalize_schedule_name,
    parse_stakeholder_schedule_name,
    parse_xml,
    response_count,
    response_has_more_records,
    scan_matches_stakeholder,
    search_scans,
    search_schedules,
    tracker_search_window,
)


class TrackerQualysScansTests(unittest.TestCase):
    """Validate tracker schedule parsing and matching."""

    def test_schedule_payload_excludes_running_last_scan(self) -> None:
        """Ask Qualys to omit schedules whose last scan is still running."""
        payload = build_schedule_search_payload(datetime(2026, 9, 20), 1)
        root = etree.fromstring(payload.encode("utf-8"))

        criteria = root.xpath('./filters/Criteria[@field="lastScan.status"]')
        self.assertEqual(len(criteria), 1)
        self.assertEqual(criteria[0].get("operator"), "NOT EQUALS")
        self.assertEqual(criteria[0].text, "RUNNING")

    @patch("was_reports.tracker.qualys_scans.close")
    @patch("was_reports.tracker.qualys_scans.recent_schedule_ids")
    @patch("was_reports.tracker.qualys_scans.latest_tracker_pull_date")
    @patch("was_reports.tracker.qualys_scans.connect")
    def test_tracker_search_window_defaults_to_three_days(
        self,
        mock_connect,
        mock_latest_pull_date,
        mock_recent_schedule_ids,
        mock_close,
    ) -> None:
        """Revisit three days of Qualys schedules by default."""
        latest_pull_date = datetime(2026, 9, 18, 12, 0, 0)
        mock_latest_pull_date.return_value = latest_pull_date
        mock_recent_schedule_ids.return_value = [1, 2]

        input_date, schedule_ids = tracker_search_window()

        self.assertEqual(input_date, latest_pull_date - timedelta(days=3))
        self.assertEqual(schedule_ids, {1, 2})
        mock_recent_schedule_ids.assert_called_once_with(
            mock_connect.return_value,
            input_date,
        )
        mock_close.assert_called_once_with(mock_connect.return_value)

    @patch("was_reports.tracker.qualys_scans.close")
    @patch("was_reports.tracker.qualys_scans.recent_schedule_ids")
    @patch("was_reports.tracker.qualys_scans.latest_tracker_pull_date")
    @patch("was_reports.tracker.qualys_scans.connect")
    def test_tracker_search_window_accepts_custom_days(
        self,
        mock_connect,
        mock_latest_pull_date,
        mock_recent_schedule_ids,
        mock_close,
    ) -> None:
        """Allow operators to expand the Qualys discovery window."""
        latest_pull_date = datetime(2026, 9, 18, 12, 0, 0)
        mock_latest_pull_date.return_value = latest_pull_date
        mock_recent_schedule_ids.return_value = []

        input_date, schedule_ids = tracker_search_window(lookback_days=7)

        self.assertEqual(input_date, latest_pull_date - timedelta(days=7))
        self.assertEqual(schedule_ids, set())
        mock_close.assert_called_once_with(mock_connect.return_value)

    def test_tracker_search_window_rejects_nonpositive_days(self) -> None:
        """Reject an invalid discovery window before opening a connection."""
        with self.assertRaises(ValueError) as raised:
            tracker_search_window(lookback_days=0)
        self.assertEqual(
            str(raised.exception),
            "Tracker lookback days must be at least 1.",
        )

    @patch(
        "was_reports.tracker.item_builder.stakeholder_flags",
        return_value=("", False),
    )
    def test_qualys_error_list_uses_only_internal_error_results(
        self,
        mock_flags,
    ) -> None:
        """Exclude processing scans from the customer Qualys-error block."""
        for result, expected_error in (
            ("SCAN_INTERNAL_ERROR", "https://example.gov<br>"),
            ("SCAN_RESULTS_INVALID", "https://example.gov<br>"),
            ("PROCESSING", ""),
        ):
            with self.subTest(result=result):
                scan = etree.fromstring(
                    (
                        "<WasScan><status>FINISHED</status><summary>"
                        "<resultsStatus>{}</resultsStatus></summary><target>"
                        "<webApp><url>https://example.gov</url></webApp>"
                        "</target></WasScan>"
                    )
                    .format(result)
                    .encode("utf-8")
                )
                fields = create_multiscan(
                    Mock(),
                    "TAG",
                    "Customer",
                    "Customer Run #1",
                    [scan],
                    "2026-09-02T00:00:00Z",
                    set(),
                )
                self.assertEqual(fields[7], expected_error)
        self.assertEqual(mock_flags.call_count, 3)

    def test_xml_entities_are_not_expanded(self) -> None:
        """Leave declared entities unresolved rather than exposing their contents."""
        root = parse_xml(
            '<!DOCTYPE response [<!ENTITY private "private-payload">]>'
            "<response>&private;</response>",
            "test parsing",
        )
        self.assertNotIn("private-payload", etree.tostring(root, encoding="unicode"))

    def test_xml_external_entity_is_not_loaded(self) -> None:
        """External network entities remain unresolved without network access."""
        root = parse_xml(
            '<!DOCTYPE response [<!ENTITY remote SYSTEM "https://example.invalid/private">]>'
            "<response>&remote;</response>",
            "test parsing",
        )
        self.assertEqual(root[0].name, "remote")

    def test_malformed_xml_has_bounded_error(self) -> None:
        """Invalid XML raises an operation-only error without response contents."""
        with self.assertRaises(RuntimeError) as raised:
            parse_xml("<private-payload>", "test parsing")
        self.assertEqual(
            str(raised.exception), "Qualys returned invalid XML during test parsing."
        )

    def test_execution_key_normalizes_timezone(self) -> None:
        """Equivalent instants deduplicate without merging separate runs."""
        first = scheduled_execution_key(2, "2026-09-01T00:00:00Z")
        self.assertEqual(first, scheduled_execution_key(2, "2026-08-31T20:00:00-04:00"))
        self.assertNotEqual(first, scheduled_execution_key(2, "2026-09-02T00:00:00Z"))
        with self.assertRaises(ValueError):
            scheduled_execution_key(2, "2026-09-01T00:00:00")

    def test_recurring_schedule_uses_actual_launch(self) -> None:
        """Previously recorded schedules remain eligible for later executions."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><data><WasScanSchedule><id>2</id>"
            "<name>WAVS - TAG - Customer - Monthly</name>"
            "<lastScan><name>WAVS - TAG - Customer - Monthly Run #71</name>"
            "<launchedDate>2026-09-03T00:00:00Z</launchedDate></lastScan>"
            "<nextLaunchDate>2026-10-03T00:00:00Z</nextLaunchDate>"
            "<target><tags><included><tagList><list><Tag><id>1</id>"
            "</Tag></list></tagList></included></tags></target>"
            "</WasScanSchedule></data></ServiceResponse>"
        )
        candidates = search_schedules(client, datetime(2026, 9, 1), {2})
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            next(iter(candidates.values())).launched_date, "2026-09-03T00:00:00Z"
        )
        self.assertEqual(
            next(iter(candidates.values())).latest_scan_name,
            "WAVS - TAG - Customer - Monthly Run #71",
        )

    def test_schedule_search_uses_tag_ids_in_schedule_response(self) -> None:
        """Use schedule target data without an Asset Management tag lookup."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><data>"
            "<WasScanSchedule><id>2</id>"
            "<name>WAVS - TAG - Customer - Monthly</name>"
            "<lastScan><launchedDate>2026-09-03T00:00:00Z</launchedDate>"
            "</lastScan><nextLaunchDate>2026-10-03T00:00:00Z</nextLaunchDate>"
            "<target><tags><included><tagList><list><Tag><id>9</id>"
            "</Tag></list></tagList></included></tags></target>"
            "</WasScanSchedule>"
            "<WasScanSchedule><id>3</id>"
            "<name>WAVS - TAG - Customer - Daily</name>"
            "<lastScan><launchedDate>2026-09-04T00:00:00Z</launchedDate>"
            "</lastScan><nextLaunchDate>2026-09-05T00:00:00Z</nextLaunchDate>"
            "<target><tags><included><tagList><list><Tag><id>9</id>"
            "</Tag></list></tagList></included></tags></target>"
            "</WasScanSchedule>"
            "</data></ServiceResponse>"
        )

        candidates = search_schedules(client, datetime(2026, 9, 1), set())

        self.assertEqual(len(candidates), 2)
        self.assertTrue(all(candidate.tag_id == 9 for candidate in candidates.values()))

    def test_running_schedule_without_launch_is_quietly_skipped(self) -> None:
        """A running Qualys scan without a launch date is not a warning."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><data><WasScanSchedule><id>2</id>"
            "<name>WAVS - KUHS - Kuakini Health System - Monthly</name>"
            "<lastScan><status>RUNNING</status></lastScan>"
            "<nextLaunchDate>2026-10-22T00:00:00Z</nextLaunchDate>"
            "</WasScanSchedule></data></ServiceResponse>"
        )

        with patch("was_reports.tracker.qualys_scans.LOGGER.warning") as warning:
            candidates = search_schedules(client, datetime(2026, 9, 20), set())

        self.assertEqual(candidates, {})
        warning.assert_not_called()
        client.request.assert_called_once()

    def test_nonrunning_schedule_without_launch_still_warns(self) -> None:
        """Missing launch dates remain visible for terminal or unknown status."""
        for status in ("FINISHED", "UNKNOWN", ""):
            with self.subTest(status=status):
                client = Mock()
                client.request.return_value = (
                    "<ServiceResponse><data><WasScanSchedule><id>2</id>"
                    "<name>WAVS - KUHS - Kuakini Health System - Monthly</name>"
                    "<lastScan><status>{}</status></lastScan>"
                    "<nextLaunchDate>2026-10-22T00:00:00Z</nextLaunchDate>"
                    "</WasScanSchedule></data></ServiceResponse>"
                ).format(status)

                with patch("was_reports.tracker.qualys_scans.LOGGER.warning") as warning:
                    candidates = search_schedules(
                        client, datetime(2026, 9, 20), set()
                    )

                self.assertEqual(candidates, {})
                warning.assert_called_once()
                self.assertIn("no actual launch timestamp", warning.call_args.args[0])

    def test_schedule_without_any_next_launch_date_is_skipped(self) -> None:
        """Continue schedule discovery when an ad hoc next date is unavailable."""
        client = Mock()
        client.request.side_effect = [
            (
                "<ServiceResponse><data><WasScanSchedule><id>2</id>"
                "<name>WAVS - TAG - Customer - Ad-Hoc</name>"
                "<lastScan><launchedDate>2026-09-03T00:00:00Z</launchedDate>"
                "</lastScan></WasScanSchedule></data></ServiceResponse>"
            ),
            "<ServiceResponse><data></data></ServiceResponse>",
        ]

        with self.assertLogs(
            "was_reports.tracker.qualys_scans",
            level="WARNING",
        ) as captured_logs:
            candidates = search_schedules(client, datetime(2026, 9, 1), set())

        self.assertEqual(candidates, {})
        self.assertEqual(client.request.call_count, 2)
        self.assertIn(
            "neither it nor its primary schedule has a next launch date",
            captured_logs.output[0],
        )

    def test_only_latest_execution_for_same_schedule(self) -> None:
        """Older finished runs are excluded before evaluating completion."""
        client = Mock()
        client.request.return_value = "<ServiceResponse><data>{}</data></ServiceResponse>".format(
            "".join(
                "<WasScan><name>WAVS - TAG - Customer - Monthly Run #{} Slice 1</name>"
                "<status>FINISHED</status><launchedDate>2026-09-0{}T00:00:00Z</launchedDate></WasScan>".format(
                    number, number
                )
                for number in (1, 2)
            )
        )
        stakeholders = {
            "TAG": TrackerStakeholder(
                "Customer",
                1,
                "2026-10-01T00:00:00Z",
                "2026-09-02T00:00:00Z",
                2,
                "MONTHLY",
                "TAG",
                "WAVS - TAG - Customer - Monthly",
            )
        }
        counts = {}
        history_groups = {}
        groups = search_scans(
            client, stakeholders, datetime(2026, 9, 1), counts, history_groups
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(history_groups), 2)
        self.assertEqual(counts["older_runs_excluded"], 1)
        self.assertEqual(counts["incomplete_runs"], 0)
        self.assertEqual(list(groups), [scheduled_execution_key(2, "2026-09-02T00:00:00Z")])
        self.assertTrue(all(len(scans) == 1 for scans in groups.values()))
        client.request.return_value = client.request.return_value.replace(
            "<status>FINISHED</status>", "<status>RUNNING</status>", 1
        )
        groups = search_scans(client, stakeholders, datetime(2026, 9, 1))
        self.assertEqual(len(groups), 1)

    def test_named_latest_run_controls_selection_before_completion(self) -> None:
        """Named runs survive timestamp drift, without older or incomplete fallback."""
        for latest_name, run_status, results_status, expected_count, expected_missing in (
            ("WAVS – TAG - Customer - Monthly Run #71 Slice 5", "FINISHED", "OK", 1, 0),
            ("WAVS - TAG - Customer - Monthly Run #72", "FINISHED", "OK", 0, 1),
            ("WAVS - TAG - Customer - Monthly Run #71", "RUNNING", "OK", 0, 0),
            ("WAVS - TAG - Customer - Monthly Run #71", "FINISHED", "PROCESSING", 0, 0),
        ):
            with self.subTest(latest_name=latest_name, run_status=run_status):
                client = Mock()
                # Run70 has a later timestamp, but is not the schedule's named run.
                client.request.return_value = (
                    "<ServiceResponse><data>"
                    "<WasScan><name>WAVS - TAG - Customer - Monthly Run #70 Slice 1</name>"
                    "<status>FINISHED</status>"
                    "<launchedDate>2026-09-02T03:00:00Z</launchedDate></WasScan>"
                    "<WasScan><name>WAVS - TAG - Customer - Monthly Run #71 Slice 1</name>"
                    "<status>{}</status>"
                    "<summary><resultsStatus>{}</resultsStatus></summary>"
                    "<launchedDate>2026-09-02T01:01:00Z</launchedDate></WasScan>"
                    "<WasScan><name>WAVS - TAG - Customer - Monthly Run #71 Slice 2</name>"
                    "<status>FINISHED</status>"
                    "<launchedDate>2026-09-02T01:02:00Z</launchedDate></WasScan>"
                    "</data></ServiceResponse>"
                ).format(run_status, results_status)
                stakeholders = {"TAG": TrackerStakeholder(
                    "Customer", 1, "2026-10-01T00:00:00Z", "2026-09-02T02:45:40Z",
                    2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly", latest_name,
                )}
                counts = {}
                history_groups = {}
                groups = search_scans(
                    client, stakeholders, datetime(2026, 9, 1), counts, history_groups
                )
                self.assertEqual(len(groups), expected_count)
                self.assertEqual(counts["missing_latest_runs"], expected_missing)
                self.assertEqual(
                    counts["incomplete_runs"],
                    int(run_status == "RUNNING" or results_status == "PROCESSING"),
                )
                self.assertIn("2:WAVS - TAG - Customer - Monthly Run #70", history_groups)
                if groups:
                    self.assertEqual(
                        list(groups), [scheduled_execution_key(2, "2026-09-02T02:45:40Z")]
                    )
                    self.assertEqual(len(next(iter(groups.values()))), 2)

    def test_missing_scan_groups_are_counted(self) -> None:
        """A schedule with no visible matching scans remains visible in diagnostics."""
        client = Mock()
        client.request.return_value = "<ServiceResponse><data/></ServiceResponse>"
        stakeholders = {"TAG": TrackerStakeholder(
            "Customer", 1, "2026-10-01T00:00:00Z", "2026-09-02T00:00:00Z",
            2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly",
        )}
        counts = {}
        self.assertEqual(search_scans(client, stakeholders, datetime(2026, 9, 1), counts), {})
        self.assertEqual(counts["missing_latest_runs"], 1)

    def test_tied_latest_launches_are_held(self) -> None:
        """Do not arbitrarily choose between distinct run names with tied launches."""
        client = Mock()
        client.request.return_value = "<ServiceResponse><data>{}</data></ServiceResponse>".format(
            "".join(
                "<WasScan><name>WAVS - TAG - Customer - Monthly Run #{} Slice 1</name>"
                "<status>FINISHED</status><launchedDate>2026-09-02T00:00:00Z</launchedDate>"
                "</WasScan>".format(number)
                for number in (1, 2)
            )
        )
        stakeholders = {"TAG": TrackerStakeholder(
            "Customer", 1, "2026-10-01T00:00:00Z", "2026-09-02T00:00:00Z",
            2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly",
        )}
        counts = {}
        history_groups = {}
        self.assertEqual(
            search_scans(client, stakeholders, datetime(2026, 9, 1), counts, history_groups),
            {},
        )
        self.assertEqual(counts["ambiguous_latest_runs"], 1)
        self.assertEqual(len(history_groups), 2)

    def test_latest_incomplete_never_falls_back_to_finished_run(self) -> None:
        """An older run finishing later is not the schedule's newest execution."""
        for latest_status, results_status in (
            ("RUNNING", "SUCCESSFUL"),
            ("FINISHED", "PROCESSING"),
        ):
            client = Mock()
            client.request.return_value = (
                "<ServiceResponse><data>"
                "<WasScan><name>WAVS - TAG - Customer - Monthly Run #1 Slice 1</name>"
                "<status>FINISHED</status><launchedDate>2026-09-01T00:00:00Z</launchedDate>"
                "<endDate>2026-09-04T00:00:00Z</endDate></WasScan>"
                "<WasScan><name>WAVS - TAG - Customer - Monthly Run #2 Slice 1</name>"
                "<status>{}</status><launchedDate>2026-09-02T00:00:00Z</launchedDate>"
                "<summary><resultsStatus>{}</resultsStatus></summary></WasScan>"
                "</data></ServiceResponse>"
            ).format(latest_status, results_status)
            stakeholders = {"TAG": TrackerStakeholder(
                "Customer", 1, "2026-10-01T00:00:00Z", "2026-09-02T00:00:00Z",
                2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly",
            )}
            counts = {}
            self.assertEqual(
                search_scans(client, stakeholders, datetime(2026, 9, 1), counts), {}
            )
            self.assertEqual(counts["incomplete_runs"], 1)
            self.assertEqual(counts["older_runs_excluded"], 1)

    def test_schedule_newer_than_visible_scans_holds_older_run(self) -> None:
        """A newer schedule anchor prevents fallback during scan visibility lag."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><data><WasScan>"
            "<name>WAVS - TAG - Customer - Monthly Run #1 Slice 1</name>"
            "<status>FINISHED</status><launchedDate>2026-09-01T00:00:00Z</launchedDate>"
            "</WasScan></data></ServiceResponse>"
        )
        stakeholders = {"TAG": TrackerStakeholder(
            "Customer", 1, "2026-10-01T00:00:00Z", "2026-09-02T00:00:00Z",
            2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly",
        )}
        counts = {}
        self.assertEqual(search_scans(client, stakeholders, datetime(2026, 9, 1), counts), {})
        self.assertEqual(counts["missing_latest_runs"], 1)
        self.assertEqual(counts["incomplete_runs"], 0)

    def test_scan_pagination_reuses_immutable_unique_tag_filter(self) -> None:
        """Do not expand the scan filter when an earlier page adds executions."""
        client = Mock()
        client.request.side_effect = [
            (
                "<ServiceResponse><count>1</count><hasMoreRecords>true"
                "</hasMoreRecords><data><WasScan>"
                "<name>WAVS - TAG - Customer - Monthly Run #2 Slice 1</name>"
                "<status>FINISHED</status>"
                "<launchedDate>2026-09-03T00:00:00Z</launchedDate>"
                "</WasScan></data></ServiceResponse>"
            ),
            (
                "<ServiceResponse><count>0</count><hasMoreRecords>false"
                "</hasMoreRecords><data></data></ServiceResponse>"
            ),
        ]
        stakeholders = {
            scheduled_execution_key(2, "2026-09-02T00:00:00Z"): (
                TrackerStakeholder(
                    name="Customer",
                    tag_id=1,
                    next_scan_date="2026-10-01T00:00:00Z",
                    launched_date="2026-09-02T00:00:00Z",
                    schedule_id=2,
                    cadence="MONTHLY",
                    tag="TAG",
                    schedule_name="WAVS - TAG - Customer - Monthly",
                )
            )
        }

        search_scans(client, stakeholders, datetime(2026, 9, 1))

        self.assertEqual(client.request.call_count, 2)
        for request_call in client.request.call_args_list:
            payload = request_call.args[0].payload
            root = etree.fromstring(payload.encode("utf-8"))
            tag_filter = root.xpath(
                './filters/Criteria[@field="webApp.tags.id"]/text()'
            )
            self.assertEqual(tag_filter, ["1"])

    def test_scan_payload_deduplicates_and_orders_tag_ids(self) -> None:
        """Build a stable Qualys tag filter from unique sorted IDs."""
        payload = build_scan_search_payload(
            tag_ids=(3, 1, 3, 2),
            input_date=datetime(2026, 9, 1),
            offset=1,
        )
        root = etree.fromstring(payload.encode("utf-8"))

        self.assertEqual(
            root.xpath('./filters/Criteria[@field="webApp.tags.id"]/text()'),
            ["1,2,3"],
        )

    def test_slices_across_pages_share_one_run_and_wait_for_processing(self) -> None:
        """Different slice timestamps must not make partial report executions."""
        stakeholder = TrackerStakeholder(
            "Customer",
            1,
            "2026-10-01T00:00:00Z",
            "2026-09-03T00:00:02Z",
            2,
            "MONTHLY",
            "TAG",
            "WAVS - TAG - Customer - Monthly",
        )
        for second_status, expected_count in (("FINISHED", 1), ("RUNNING", 0)):
            client = Mock()
            client.request.side_effect = [
                "<ServiceResponse><count>1</count><hasMoreRecords>{}</hasMoreRecords>"
                "<data><WasScan><name>WAVS - TAG - Customer - Monthly Run #2 Slice {}</name>"
                "<status>{}</status><launchedDate>2026-09-03T00:00:0{}Z</launchedDate>"
                "</WasScan></data></ServiceResponse>".format(
                    more, number, status, number
                )
                for more, number, status in (
                    ("true", 2, "FINISHED"),
                    ("false", 1, second_status),
                )
            ]
            stakeholders = {"TAG": stakeholder}
            groups = search_scans(client, stakeholders, datetime(2026, 9, 1))
            self.assertEqual(len(groups), expected_count)
            if groups:
                self.assertEqual(len(next(iter(groups.values()))), 2)
                self.assertEqual(
                    next(iter(groups)),
                    scheduled_execution_key(2, "2026-09-03T00:00:02Z"),
                )

    def test_detail_timing_uses_one_lowercase_get_and_duration(self) -> None:
        """Use FINISHED duration without per-target requests or guessed ends."""
        from was_reports.tracker.qualys_scans import execution_detail_bounds
        scan = etree.fromstring(
            "<WasScan><id>123</id><status>FINISHED</status>"
            "<launchedDate>2026-09-03T05:00:44Z</launchedDate></WasScan>"
        )
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><data><WasScan><id>123</id><status>FINISHED</status>"
            "<launchedDate>2026-09-03T05:00:44Z</launchedDate>"
            "<scanDuration>3660</scanDuration></WasScan></data></ServiceResponse>"
        )
        start, end = execution_detail_bounds(client, scan)
        self.assertEqual(start.isoformat(), "2026-09-03T05:00:44+00:00")
        self.assertEqual(end.isoformat(), "2026-09-03T06:01:44+00:00")
        client.request.assert_called_once()
        self.assertEqual(client.request.call_args.args[0].http_method, "get")
        self.assertEqual(client.request.call_args.args[0].endpoint, "/get/was/wasscan/123")
        client.reset_mock()
        etree.SubElement(scan, "endScanDate").text = "2026-09-03T06:00:00Z"
        self.assertIsNotNone(execution_detail_bounds(client, scan)[1])
        client.request.assert_not_called()

    def test_timing_detail_failure_preserves_start(self) -> None:
        """Optional metadata failures must not fail report selection."""
        from was_reports.tracker.qualys_scans import execution_detail_bounds
        scan = etree.fromstring(
            "<WasScan><id>123</id><status>FINISHED</status>"
            "<launchedDate>2026-09-03T05:00:44Z</launchedDate></WasScan>"
        )
        client = Mock()
        client.request.side_effect = RuntimeError("unavailable")
        start, end = execution_detail_bounds(client, scan)
        self.assertIsNotNone(start)
        self.assertIsNone(end)

    def test_parent_identity_stable_across_slice_order_and_subset(self) -> None:
        """Retrying with different returned slices preserves the schedule launch key."""
        parent_launch = "2026-09-03T04:01:00Z"
        stakeholder = TrackerStakeholder(
            "Customer", 1, "2026-10-01T00:00:00Z", parent_launch,
            2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly",
            "WAVS - TAG - Customer - Monthly Run #2",
        )
        expected_key = scheduled_execution_key(2, parent_launch)
        for slice_numbers in ((1, 2), (2, 1), (1,), (2,)):
            with self.subTest(slice_numbers=slice_numbers):
                client = Mock()
                client.request.return_value = (
                    "<ServiceResponse><data>{}</data></ServiceResponse>"
                ).format("".join(
                    "<WasScan><name>WAVS - TAG - Customer - Monthly Run #2 Slice {}</name>"
                    "<status>FINISHED</status><summary><resultsStatus>SUCCESSFUL</resultsStatus>"
                    "</summary><launchedDate>2026-09-03T03:59:0{}Z</launchedDate>"
                    "</WasScan>".format(number, number)
                    for number in slice_numbers
                ))
                stakeholders = {"TAG": stakeholder}
                groups = search_scans(client, stakeholders, datetime(2026, 9, 1))
                self.assertEqual(list(groups), [expected_key])
                self.assertEqual(stakeholders[expected_key].launched_date, parent_launch)
                self.assertEqual(len(groups[expected_key]), len(slice_numbers))

    def test_multi_parent_is_not_a_target_slice(self) -> None:
        """Aggregate child targets once and require any visible MULTI parent to finish."""
        for child_count, parent_status, schedule_status, expected in (
            (50, "FINISHED", "FINISHED", 1),
            (0, "FINISHED", "FINISHED", 0),
            (50, "RUNNING", "FINISHED", 0),
            (50, "FINISHED", "RUNNING", 0),
            (50, "ERROR", "FINISHED", 0),
            (50, "CANCELED", "FINISHED", 0),
            (50, "FINISHED", "ERROR", 0),
            (50, "FINISHED", "CANCELED", 0),
        ):
            with self.subTest(child_count=child_count, parent_status=parent_status,
                              schedule_status=schedule_status):
                parent = (
                    "<WasScan><name>WAVS - TAG - Customer - Monthly Run #2</name>"
                    "<multi>true</multi><status>{}</status>"
                    "<launchedDate>2026-09-03T04:01:00Z</launchedDate>"
                    "<endScanDate>2026-09-03T06:01:00Z</endScanDate></WasScan>"
                ).format(parent_status)
                children = "".join(
                    "<WasScan><name>WAVS - TAG - Customer - Monthly Run #2 Slice {}</name>"
                    "<multi>false</multi><status>FINISHED</status><summary>"
                    "<resultsStatus>SUCCESSFUL</resultsStatus></summary>"
                    "<launchedDate>2026-09-03T04:01:01Z</launchedDate></WasScan>".format(number)
                    for number in range(child_count)
                )
                client = Mock()
                client.request.return_value = (
                    "<ServiceResponse><data>{}{}</data></ServiceResponse>"
                ).format(parent, children)
                stakeholders = {"TAG": TrackerStakeholder(
                    "Customer", 1, "2026-10-01T00:00:00Z", "2026-09-03T04:01:00Z",
                    2, "MONTHLY", "TAG", "WAVS - TAG - Customer - Monthly",
                    "WAVS - TAG - Customer - Monthly Run #2", schedule_status,
                )}
                groups = search_scans(client, stakeholders, datetime(2026, 9, 1))
                self.assertEqual(len(groups), expected)
                if groups:
                    self.assertEqual(len(next(iter(groups.values()))), 50)
                    selected = stakeholders[next(iter(groups))]
                    self.assertEqual(selected.scan_started_at.isoformat(), "2026-09-03T04:01:00+00:00")
                    self.assertEqual(selected.scan_ended_at.isoformat(), "2026-09-03T06:01:00+00:00")

    def test_previous_run_matches_full_name(self) -> None:
        """Run one must not match run ten or another schedule."""
        previous = previous_run_name("WAVS - TAG - Customer - Monthly Run #2")
        client = Mock()
        client.request.return_value = "<ServiceResponse><data>{}</data></ServiceResponse>".format(
            "".join(
                "<WasScan><name>{}</name><summary><resultsStatus>NO_WEB_SERVICE</resultsStatus>"
                "</summary><target><webApp><url>{}</url></webApp></target></WasScan>".format(
                    name, url
                )
                for name, url in (
                    (previous + " Slice 1", "accepted"),
                    (previous + "0 Slice 1", "excluded"),
                )
            )
        )
        self.assertEqual(
            get_previous_nws(
                client, "TAG", "Customer", previous, "2026-09-02T00:00:00Z"
            ),
            ["accepted"],
        )

    @patch(
        "was_reports.tracker.item_builder.stakeholder_flags", return_value=("", False)
    )
    @patch("was_reports.tracker.item_builder.get_previous_nws")
    def test_exempt_tags_retain_inaccessible_data(
        self, mock_previous, mock_flags
    ) -> None:
        """Deletion exemptions retain inaccessible URLs without removal candidates."""
        scan = etree.fromstring(
            b"<WasScan><status>FINISHED</status><summary><resultsStatus>NO_WEB_SERVICE</resultsStatus>"
            b"</summary><target><webApp><url>https://example.gov</url></webApp></target></WasScan>"
        )
        fields = create_multiscan(
            Mock(),
            "TAG",
            "Customer",
            "Customer Run #2",
            [scan],
            "2026-09-02T00:00:00Z",
            {"TAG"},
        )
        self.assertTrue(fields[2])
        self.assertIn("https://example.gov", fields[3])
        self.assertEqual(fields[4], "")
        mock_previous.assert_not_called()

    def test_normalize_schedule_name_replaces_unicode_dash(self) -> None:
        """Normalize schedule punctuation without regular expressions."""
        normalized = normalize_schedule_name("WAVS – TAG -- Customer")

        self.assertEqual(normalized, "WAVS - TAG - Customer")

    @patch(
        "was_reports.tracker.item_builder.stakeholder_flags", return_value=("", False)
    )
    @patch("was_reports.tracker.item_builder.get_previous_nws")
    def test_previous_nws_cache_avoids_repeated_api_lookup(
        self, mock_previous, mock_flags
    ):
        """A discovered previous run supplies NWS evidence without another request."""
        scan = etree.fromstring(
            b"<WasScan><status>FINISHED</status><summary><resultsStatus>NO_WEB_SERVICE</resultsStatus>"
            b"</summary><target><webApp><url>https://example.gov</url></webApp></target></WasScan>"
        )
        result = create_multiscan(
            Mock(),
            "TAG",
            "Customer",
            "Customer Run #2",
            [scan],
            "2026-09-03T00:00:00Z",
            set(),
            {"Customer Run #1": ["https://example.gov"]},
        )
        self.assertIn("https://example.gov", result[4])
        mock_previous.assert_not_called()

    def test_parse_stakeholder_schedule_name(self) -> None:
        """Extract the stakeholder tag and name from a schedule name."""
        tag, name = parse_stakeholder_schedule_name(
            "WAVS - CROSSFEED - Crossfeed Program - Monthly"
        )

        self.assertEqual(tag, "CROSSFEED")
        self.assertEqual(name, "Crossfeed Program")

    def test_base_stakeholder_tag_removes_adhoc_suffix(self) -> None:
        """Resolve the primary tag from an ad hoc child tag."""
        self.assertEqual(base_stakeholder_tag("CROSSFEED_ADHOC"), "CROSSFEED")

    def test_response_pagination_fields(self) -> None:
        """Parse Qualys pagination metadata defensively."""
        root = etree.fromstring(
            b"<ServiceResponse><count>50</count>"
            b"<hasMoreRecords>true</hasMoreRecords></ServiceResponse>"
        )

        self.assertEqual(response_count(root), 50)
        self.assertTrue(response_has_more_records(root))

    def test_scan_matches_expected_stakeholder_and_cadence(self) -> None:
        """Match a scan only to its stakeholder and configured cadence."""
        stakeholder = TrackerStakeholder(
            name="Crossfeed Program",
            tag_id=1,
            next_scan_date="2026-09-10T00:00:00Z",
            launched_date="2026-09-01T00:00:00Z",
            schedule_id=2,
            cadence="MONTHLY",
        )

        self.assertTrue(
            scan_matches_stakeholder(
                "WAVS - CROSSFEED - Crossfeed Program - Monthly Run #1",
                "CROSSFEED",
                stakeholder,
            )
        )
        self.assertFalse(
            scan_matches_stakeholder(
                "WAVS - CROSSFEED - Crossfeed Program - Ad-Hoc Run #1",
                "CROSSFEED",
                stakeholder,
            )
        )


if __name__ == "__main__":
    unittest.main()
