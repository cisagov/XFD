"""Tests for production tracker consolidation and update helpers."""

# Standard Python Libraries
from dataclasses import replace
from datetime import date
import unittest
from unittest.mock import MagicMock, Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.data.daily_report_tracker import DailyReportTrackerRow
from was_reports.tracker.item_builder import (
    combined_status_and_result,
    create_tracker_items,
)
from was_reports.tracker.models import TrackerItem, TrackerStakeholder
from was_reports.tracker.update_service import (
    combined_email_value,
    convert_qualys_date,
    has_legacy_execution_overlap,
    tracker_result_fields,
    update_execution,
    update_stakeholder_scan_metadata,
    update_tracker,
)


class TrackerUpdateServiceTests(unittest.TestCase):
    """Validate tracker result and database-row transformations."""

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
        self.assertNotIn("private-response-payload", "".join(logs.output))
        self.assertIsNone(logs.records[0].exc_info)

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
        ), patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
            ["commit", "delete", "commit"],
        )
        self.assertEqual(
            cursor.execute.call_args.args[1],
            ("Targets Removed", "", 17, "MANUAL QUALYS DELETION PENDING"),
        )

    def test_duplicate_and_pending_claims_never_delete(self) -> None:
        """Completed, pending, and report-linked executions are not replayed."""
        for existing in (
            (17, "Finished", "No Web Service", ""),
            (17, "Finished", "No Web Service", "MANUAL QUALYS DELETION FAILED"),
            (
                17,
                "Finished",
                "No Web Service",
                "MANUAL QUALYS DELETION PENDING",
            ),
            (17, "Running", "Running", ""),
        ):
            conn = MagicMock()
            cursor = conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [existing, (True,)]
            with patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
                "was_reports.tracker.update_service.delete_webapp",
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
        ), patch("was_reports.tracker.update_service.delete_webapp"), patch(
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
                (17, "Finished", "No Web Service", "QUALYS DELETION REQUIRED"),
                (report_exists,),
            ]
            cursor.rowcount = 1
            sequence = Mock()
            sequence.attach_mock(conn.commit, "commit")
            with patch(
                "was_reports.tracker.update_service.build_tracker_row",
                return_value=DailyReportTrackerRow(),
            ), patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
                claim = cursor.execute.call_args_list[2]
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
            (17, "Finished", "No Web Service", "QUALYS DELETION REQUIRED"),
            (False,),
        ]
        cursor.rowcount = 0
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(),
        ), patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
        ), patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
            (17, "Running", "Running", ""),
            (False,),
        ]
        with patch(
            "was_reports.tracker.update_service.build_tracker_row",
            return_value=DailyReportTrackerRow(status="Finished"),
        ), patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
        ), patch("was_reports.tracker.update_service.delete_webapp") as delete:
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
        )


if __name__ == "__main__":
    unittest.main()
