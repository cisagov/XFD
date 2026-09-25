"""Tests for WAS daily report tracker data access."""

# Standard Python Libraries
from datetime import date, datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.data.daily_report_tracker import (
    DELIVERY_RECONCILIATION,
    MANUAL_WORK,
    DailyReportTrackerRow,
    TRACKER_RECORD_COLUMNS,
    claim_assignee_digest_rows,
    finish_assignee_digest_rows,
    get_tracker_record_by_id,
    insert_daily_report_tracker_row,
    latest_tracker_pull_date,
    list_ready_assignee_digests,
    list_ready_report_candidates,
    list_tracker_rows_for_export,
    list_tracker_table_rows,
    manual_work_classification,
    mark_manual_tracker_report_sent,
    mark_tracker_report_manual,
    record_tracker_digest_failure,
)


class FakeCursor:
    """Small cursor test double for tracker inserts."""

    def __init__(self, fetchone_row=(7,), fetchall_rows=None):
        """Initialize captured query state."""
        self.query = None
        self.parameters = None
        self.fetchone_row = fetchone_row
        self.fetchall_rows = fetchall_rows or []

    def __enter__(self):
        """Return this cursor for context manager usage."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""

    def execute(self, query, parameters=None):
        """Capture query and parameters."""
        self.query = query
        self.parameters = parameters

    def fetchone(self):
        """Return a fake inserted row ID."""
        return self.fetchone_row

    def fetchall(self):
        """Return fake query rows."""
        return self.fetchall_rows


class FakeConnection:
    """Small connection test double for tracker inserts."""

    def __init__(self, fetchone_row=(7,), fetchall_rows=None):
        """Initialize connection state."""
        self.cursor_instance = FakeCursor(
            fetchone_row=fetchone_row,
            fetchall_rows=fetchall_rows,
        )
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        """Return the fake cursor."""
        return self.cursor_instance

    def commit(self):
        """Record commit usage."""
        self.committed = True

    def rollback(self):
        """Record rollback usage."""
        self.rolled_back = True


class DailyReportTrackerTests(unittest.TestCase):
    """Validate daily report tracker persistence helpers."""

    def test_manual_work_classification_separates_legacy_sent_notes(self) -> None:
        """An unreconciled sent marker is not actionable manual generation."""
        self.assertEqual(
            manual_work_classification(
                None,
                "Sent 09/22/2026",
                None,
                "Finished",
                False,
            ),
            DELIVERY_RECONCILIATION,
        )
        self.assertEqual(
            manual_work_classification(
                None,
                "Report sent - 09/21/2026\nLegacy child-tag detail",
                None,
                "Finished",
                False,
            ),
            DELIVERY_RECONCILIATION,
        )
        self.assertEqual(
            manual_work_classification(
                None,
                "MANUAL: PasswordValidationError",
                None,
                "Finished",
                False,
            ),
            MANUAL_WORK,
        )
        self.assertEqual(
            manual_work_classification(
                None,
                "Sent yesterday",
                None,
                "Finished",
                False,
            ),
            MANUAL_WORK,
        )
        self.assertEqual(
            manual_work_classification(
                None,
                "Sent 09/31/2026",
                None,
                "Finished",
                False,
            ),
            MANUAL_WORK,
        )
        self.assertIsNone(
            manual_work_classification(
                date(2026, 9, 22),
                "Sent 09/22/2026",
                None,
                "Finished",
                False,
            )
        )

    def test_manual_candidates_exclude_unreconciled_legacy_sent_notes(self) -> None:
        """Generic manual processing cannot resend a legacy sent-note row."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    7,
                    "TAG",
                    date(2026, 9, 22),
                    123,
                    1,
                    456,
                    "Customer",
                    "Results",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "Sent 09/22/2026",
                    "Finished",
                    False,
                )
            ]
        )
        self.assertEqual(
            list_ready_report_candidates(conn=conn, include_manual=True),
            [],
        )

    def test_insert_preserves_full_execution_timestamps(self) -> None:
        """Persist exact start and end separately from execution identity."""
        conn = FakeConnection()
        started = datetime(2026, 9, 23, 5, 0, 44, tzinfo=timezone.utc)
        ended = datetime(2026, 9, 23, 6, 1, 44, tzinfo=timezone.utc)
        row = DailyReportTrackerRow(
            scan_started_at=started,
            scan_ended_at=ended,
            scan_execution_key="scheduled:123:unchanged",
        )
        insert_daily_report_tracker_row(row=row, conn=conn)
        self.assertEqual(conn.cursor_instance.parameters[-3:],
                         (started, ended, "scheduled:123:unchanged"))
        self.assertEqual(conn.cursor_instance.query.count("%s"),
                         len(conn.cursor_instance.parameters))
        self.assertIn("scan_started_at", conn.cursor_instance.query)
        self.assertIn("scan_ended_at", conn.cursor_instance.query)

    def test_insert_daily_report_tracker_row_maps_workbook_columns(self) -> None:
        """Insert tracker fields in workbook column order."""
        conn = FakeConnection()
        row = DailyReportTrackerRow(
            data_pull_date=date(2026, 8, 26),
            tag="CUSTOMER_TAG",
            scan_name="WAVS - CUSTOMER_TAG",
            assignee_id=3,
            assignee="Analyst",
            status="Finished",
            result="Successful",
            report_sent_date=date(2026, 8, 26),
            report_scan_notes="Sent",
            scan_start_date=date(2026, 8, 25),
            next_scan_date=date(2026, 9, 25),
            poc="Customer POC",
            poc_email="poc@example.gov",
            customer_notes="Scan after hours",
            nws="5, 1, 0",
            template="Results",
            recent_nws="<br>https://example.gov",
            remove_nws="<br>https://old.example.gov",
            legacy_password="STATIC PASSWORD",
            schedule_id=12345,
            tag_id=88,
            qualys_error=None,
            assignee_emailed_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            assignee_email_message_id="message-id",
            assignee_email_error=None,
        )

        row_id = insert_daily_report_tracker_row(row=row, conn=conn)

        self.assertEqual(row_id, 7)
        self.assertTrue(conn.committed)
        self.assertIn("was_daily_report_tracker", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters[0], date(2026, 8, 26))
        self.assertEqual(conn.cursor_instance.parameters[1], "CUSTOMER_TAG")
        self.assertEqual(conn.cursor_instance.parameters[3], 3)
        self.assertEqual(conn.cursor_instance.parameters[14], "5, 1, 0")
        self.assertEqual(conn.cursor_instance.parameters[18], "STATIC PASSWORD")
        self.assertEqual(conn.cursor_instance.parameters[19], 12345)
        self.assertEqual(
            conn.cursor_instance.parameters[22],
            datetime(2026, 8, 26, tzinfo=timezone.utc),
        )
        self.assertEqual(conn.cursor_instance.parameters[23], "message-id")

    def test_get_tracker_record_returns_safe_fields_by_id(self) -> None:
        """Return one row without exposing passwords or active claim tokens."""
        values = tuple(
            "value-{}".format(column_name)
            for column_name in TRACKER_RECORD_COLUMNS
        )
        conn = FakeConnection(fetchone_row=values)

        record = get_tracker_record_by_id(tracker_id=17, conn=conn)

        self.assertEqual(record["id"], "value-id")
        self.assertEqual(record["customer_notes"], "value-customer_notes")
        self.assertNotIn("legacy_password", record)
        self.assertNotIn("assignee_email_claim_token", record)
        self.assertNotIn("legacy_password", conn.cursor_instance.query)
        self.assertNotIn("assignee_email_claim_token", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (17,))

    def test_get_tracker_record_rejects_missing_id(self) -> None:
        """Explain when the requested tracker row does not exist."""
        conn = FakeConnection(fetchone_row=None)

        with self.assertRaisesRegex(KeyError, "Tracker row 17 was not found"):
            get_tracker_record_by_id(tracker_id=17, conn=conn)

    def test_latest_tracker_pull_date_returns_database_value(self) -> None:
        """Return the latest tracker pull date as UTC midnight."""
        conn = FakeConnection(fetchone_row=(date(2026, 8, 26),))

        pull_date = latest_tracker_pull_date(conn)

        self.assertEqual(pull_date, datetime(2026, 8, 26, tzinfo=timezone.utc))

    def test_list_ready_assignee_digests_groups_rows(self) -> None:
        """Group unsent tracker rows by assignee email."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    1,
                    date(2026, 8, 26),
                    "TAG1",
                    "Scan 1",
                    3,
                    "Analyst",
                    "Finished",
                    "Successful",
                    None,
                    "",
                    date(2026, 8, 25),
                    date(2026, 9, 25),
                    "POC",
                    "poc@example.gov",
                    "Notes",
                    "1",
                    "Results",
                    "",
                    "",
                    None,
                    123,
                    None,
                    "analyst@example.gov",
                    "scan:1",
                    0,
                ),
                (
                    2,
                    date(2026, 8, 26),
                    "TAG2",
                    "Scan 2",
                    3,
                    "Analyst",
                    "Error",
                    "Service Error",
                    None,
                    "MANUAL",
                    date(2026, 8, 25),
                    date(2026, 9, 25),
                    "POC",
                    "poc@example.gov",
                    "Notes",
                    "2",
                    "Action Required",
                    "",
                    "",
                    None,
                    124,
                    None,
                    "analyst@example.gov",
                    "scan:2",
                    0,
                ),
            ],
        )

        digests = list_ready_assignee_digests(
            conn=conn,
            data_pull_date=date(2026, 8, 26),
            days_back=30,
        )

        self.assertEqual(len(digests), 1)
        self.assertEqual(digests[0].email, "analyst@example.gov")
        self.assertEqual(len(digests[0].rows), 2)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (["pending"], date(2026, 8, 26), 30),
        )
        self.assertIn(
            "tracker.data_pull_date >= CURRENT_DATE - (%s - 1)",
            conn.cursor_instance.query,
        )
        self.assertEqual([row.id for row in digests[0].rows], [1, 2])

    def test_list_ready_report_candidates_finds_unsent_finished_rows(self) -> None:
        """Find recent tracker rows without sent reports or existing claims."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    7,
                    "TAG1",
                    date(2026, 9, 1),
                    12345,
                    3,
                    88,
                    "Customer Name",
                    "Results",
                    "",
                    "",
                    None,
                    None,
                    None,
                ),
            ]
        )

        candidates = list_ready_report_candidates(
            conn=conn,
            stakeholder_tag="TAG1",
            limit=5,
            days_back=30,
        )

        self.assertEqual(candidates[0].id, 7)
        self.assertEqual(candidates[0].tag, "TAG1")
        self.assertIn("tracker.report_sent_date IS NULL", conn.cursor_instance.query)
        self.assertIn("runs.source_tracker_id", conn.cursor_instance.query)
        self.assertIn(
            "stakeholders.manual_report IS NOT TRUE", conn.cursor_instance.query
        )
        self.assertIn("PARTITION BY tracker.tag", conn.cursor_instance.query)
        self.assertIn("WHERE tracker.candidate_rank = 1", conn.cursor_instance.query)
        self.assertIn(
            "tracker.scan_start_date DESC NULLS LAST",
            conn.cursor_instance.query,
        )
        self.assertIn(
            "tracker.data_pull_date DESC NULLS LAST",
            conn.cursor_instance.query,
        )
        rank_position = conn.cursor_instance.query.index("ROW_NUMBER() OVER")
        delivery_gap_position = conn.cursor_instance.query.index(
            "tracker.report_sent_date IS NULL"
        )
        self.assertLess(rank_position, delivery_gap_position)
        self.assertIn(
            "FROM ranked_tracker AS tracker",
            conn.cursor_instance.query,
        )
        self.assertIn("NOT LIKE %s", conn.cursor_instance.query)
        self.assertIn(
            "tracker.scan_start_date >= CURRENT_DATE - (%s - 1)",
            conn.cursor_instance.query,
        )
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("legacy-import:%", "TAG1", 30, 5),
        )

    def test_list_ready_report_candidates_partitions_tracker_rows(self) -> None:
        """Assign each tracker row to exactly one bounded report worker."""
        conn = FakeConnection()

        list_ready_report_candidates(
            conn=conn,
            worker_count=5,
            worker_index=2,
        )

        self.assertIn(
            "MOD(ABS(HASHTEXT(tracker.tag)::BIGINT), %s) = %s",
            conn.cursor_instance.query,
        )
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("legacy-import:%", 5, 2),
        )

    def test_automated_legacy_overlap_hold_happens_after_ranking(self) -> None:
        """Hold day-only overlaps without falling back to older report rows."""
        conn = FakeConnection()
        list_ready_report_candidates(conn=conn, days_back=7)
        query = conn.cursor_instance.query
        self.assertIn("legacy.id <> tracker.id", query)
        self.assertIn("legacy.schedule_id = tracker.schedule_id", query)
        self.assertIn("legacy.scan_start_date = tracker.scan_start_date", query)
        self.assertIn("legacy.scan_execution_key IS NULL", query)
        self.assertIn("LIKE 'legacy-import:%%'", query)
        self.assertLess(
            query.index("WHERE tracker.candidate_rank = 1"),
            query.index("legacy.id <> tracker.id"),
        )
        self.assertNotIn("legacy.tag = tracker.tag", query)

    def test_manual_reports_do_not_inherit_legacy_overlap_hold(self) -> None:
        """Leave deliberate manual generation unchanged by automated holds."""
        conn = FakeConnection()
        list_ready_report_candidates(conn=conn, include_manual=True)
        self.assertNotIn("legacy.id <> tracker.id", conn.cursor_instance.query)
        self.assertNotIn("sibling.id <> tracker.id", conn.cursor_instance.query)

    def test_same_scan_run_hold_requires_exact_nonblank_run_identity(self) -> None:
        """Do not confuse distinct named runs sharing a schedule and scan day."""
        conn = FakeConnection()
        list_ready_report_candidates(conn=conn)
        query = conn.cursor_instance.query
        self.assertIn("sibling.id <> tracker.id", query)
        self.assertIn("sibling.schedule_id = tracker.schedule_id", query)
        self.assertIn("sibling.scan_start_date = tracker.scan_start_date", query)
        self.assertIn("BTRIM(COALESCE(tracker.scan_name, '')) <> ''", query)
        self.assertIn("sibling.scan_name = tracker.scan_name", query)
        self.assertIn("sibling.report_sent_date IS NOT NULL", query)
        self.assertIn("sibling_run.source_tracker_id = sibling.id", query)
        self.assertNotIn("sibling_run.status =", query)
        self.assertLess(
            query.index("WHERE tracker.candidate_rank = 1"),
            query.index("sibling.id <> tracker.id"),
        )

    def test_list_ready_report_candidates_falls_back_to_stakeholder_tag_id(
        self,
    ) -> None:
        """Use the stakeholder Qualys tag ID when the tracker row lacks one."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    7,
                    "TAG1",
                    date(2026, 9, 1),
                    12345,
                    3,
                    144,
                    "Customer Name",
                    "Results",
                    "",
                    "",
                    None,
                    None,
                    None,
                )
            ]
        )

        candidates = list_ready_report_candidates(conn=conn)

        self.assertEqual(candidates[0].tag_id, 144)
        self.assertIn(
            "COALESCE(tracker.tag_id, stakeholders.qualys_tag_id)",
            conn.cursor_instance.query,
        )

    def test_list_ready_report_candidates_rejects_invalid_partition(self) -> None:
        """Reject worker settings that could overlap or omit tracker rows."""
        conn = FakeConnection()

        with self.assertRaisesRegex(ValueError, "between 1 and 30"):
            list_ready_report_candidates(
                conn=conn,
                worker_count=31,
                worker_index=0,
            )

    def test_mark_tracker_report_manual_updates_unsent_row(self) -> None:
        """Send generation failures to the assigned analyst for manual handling."""
        conn = FakeConnection()

        mark_tracker_report_manual(tracker_id=7, conn=conn)

        self.assertTrue(conn.committed)
        self.assertIn("report_scan_notes = %s", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, ("MANUAL", 7))

    def test_list_ready_report_candidates_includes_manual_failures(self) -> None:
        """Allow a scoped manual run to reclaim failed tracker reports."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    7,
                    "TAG1",
                    date(2026, 9, 1),
                    12345,
                    3,
                    88,
                    "Customer Name",
                    "Results",
                    "",
                    "Qualys internal error",
                    8,
                    "failed",
                    "pending",
                    None,
                    "MANUAL",
                    "Error",
                    False,
                )
            ]
        )

        candidates = list_ready_report_candidates(
            conn=conn,
            stakeholder_tag="TAG1",
            limit=1,
            include_manual=True,
        )

        self.assertEqual(candidates[0].id, 7)
        self.assertEqual(candidates[0].report_run_id, 8)
        self.assertEqual(candidates[0].qualys_error, "Qualys internal error")
        self.assertIn("runs.status = 'failed'", conn.cursor_instance.query)
        self.assertIn("stakeholders.manual_report IS TRUE", conn.cursor_instance.query)
        self.assertNotIn(
            "stakeholders.manual_report IS NOT TRUE",
            conn.cursor_instance.query,
        )
        self.assertNotIn("PARTITION BY tracker.tag", conn.cursor_instance.query)
        self.assertNotIn("tracker.candidate_rank = 1", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("legacy-import:%", "TAG1", 1),
        )

    def test_list_tracker_rows_for_export_filters_rows(self) -> None:
        """Return tracker rows for CSV export."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    date(2026, 8, 26),
                    "TAG1",
                    "Scan 1",
                    3,
                    "Analyst",
                    "Finished",
                    "Successful",
                    None,
                    "",
                    date(2026, 8, 25),
                    date(2026, 9, 25),
                    "POC",
                    "poc@example.gov",
                    "Notes",
                    "1",
                    "Results",
                    "",
                    "",
                    None,
                    123,
                    None,
                    1,
                    "scan:1",
                )
            ]
        )

        rows = list_tracker_rows_for_export(
            conn=conn,
            data_pull_date=date(2026, 8, 26),
            assignee_id=3,
            limit=10,
        )

        self.assertEqual(rows[0].tag, "TAG1")
        self.assertEqual(rows[0].assignee_id, 3)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (date(2026, 8, 26), 3, 10),
        )

    def test_list_tracker_table_rows_filters_recent_assignee_rows(self) -> None:
        """Return safe live tracker fields for one recent assignee window."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    7,
                    date(2026, 9, 1),
                    "TAG1",
                    "Scan 1",
                    "Analyst",
                    "Finished",
                    "Successful",
                    "PENDING",
                    None,
                    "",
                    date(2026, 9, 29),
                )
            ]
        )

        rows = list_tracker_table_rows(
            conn=conn,
            days_back=7,
            assignee_name=" Analyst ",
            limit=25,
        )

        self.assertEqual(rows[0].tag, "TAG1")
        self.assertEqual(rows[0].tracker_id, 7)
        self.assertEqual(rows[0].report_status, "PENDING")
        self.assertNotIn("legacy_password", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (7, "Analyst", 25))

    def test_list_tracker_rows_for_export_filters_assignee_days(self) -> None:
        """Filter CSV rows by recent calendar window and assignee name."""
        conn = FakeConnection(fetchall_rows=[])

        rows = list_tracker_rows_for_export(
            conn=conn,
            days_back=7,
            assignee_name=" Mina Salehi ",
        )

        self.assertEqual(rows, [])
        self.assertIn(
            "data_pull_date >= CURRENT_DATE - %s",
            conn.cursor_instance.query,
        )
        self.assertIn("LOWER(BTRIM(COALESCE(assignee", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (7, "Mina Salehi"))

    def test_list_tracker_table_rows_filters_manual_status(self) -> None:
        """Filter the live tracker table to manual rows across assignees."""
        conn = FakeConnection(fetchall_rows=[])

        rows = list_tracker_table_rows(
            conn=conn,
            days_back=7,
            report_status="manual",
            limit=25,
        )

        self.assertEqual(rows, [])
        self.assertIn("report_status = %s", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (7, "MANUAL", 25))

    def test_list_tracker_table_rows_supports_no_row_limit(self) -> None:
        """Return every matching tracker row when no limit is requested."""
        conn = FakeConnection(fetchall_rows=[])

        rows = list_tracker_table_rows(
            conn=conn,
            days_back=7,
            limit=None,
        )

        self.assertEqual(rows, [])
        self.assertNotIn("LIMIT %s", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (7,))

    def test_mark_manual_tracker_report_sent_updates_unsent_manual_row(self) -> None:
        """Set a manual report sent date using its tracker row ID."""
        conn = FakeConnection(fetchone_row=(7,))

        mark_manual_tracker_report_sent(
            tracker_id=7,
            sent_date=date(2026, 9, 2),
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (date(2026, 9, 2), 7),
        )
        self.assertIn("report_sent_date IS NULL", conn.cursor_instance.query)
        self.assertIn("RETURNING tracker.id", conn.cursor_instance.query)
        self.assertIn("stakeholders.manual_report IS TRUE", conn.cursor_instance.query)


class DigestLifecycleTests(unittest.TestCase):
    """Exercise managed transactions at the database connection boundary."""

    def setUp(self) -> None:
        """Provide deterministic row ownership responses."""
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.cursor.fetchall.return_value = [(7,), (8,)]
        connect = patch(
            "was_reports.utils.database.connect", return_value=self.connection
        )
        close = patch("was_reports.utils.database.close")
        connect.start()
        close.start()
        self.addCleanup(connect.stop)
        self.addCleanup(close.stop)

    def test_claim_locks_exact_snapshot(self) -> None:
        """Claim every row in deterministic lock order before changing status."""
        self.assertTrue(claim_assignee_digest_rows([8, 7], "token"))
        self.assertIn(
            "ORDER BY id FOR UPDATE", self.cursor.execute.call_args_list[0].args[0]
        )
        self.assertEqual(self.cursor.execute.call_args.args[1], ("token", [7, 8]))
        self.connection.commit.assert_called_once()

    def test_partial_claim_rolls_back(self) -> None:
        """A busy or missing row prevents delivery of the entire snapshot."""
        self.cursor.fetchall.return_value = [(7,)]
        self.assertFalse(claim_assignee_digest_rows([7, 8], "token"))
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_finish_uses_exact_ids_and_token(self) -> None:
        """A newly added same-date row is never included in completion."""
        finish_assignee_digest_rows([7, 8], "token", message_id="message")
        self.assertEqual(
            self.cursor.execute.call_args.args[1],
            ("sent", "sent", "sent", "message", None, [7, 8], "token"),
        )
        self.connection.commit.assert_called_once()

    def test_stale_finish_cannot_change_rows(self) -> None:
        """A stale sender must not complete any part of another claim."""
        self.cursor.fetchall.return_value = []
        with self.assertRaises(RuntimeError):
            finish_assignee_digest_rows([7, 8], "stale", message_id="message")
        self.assertEqual(self.cursor.execute.call_count, 1)
        self.connection.rollback.assert_called_once()

    def test_payload_revision_must_match_at_claim(self) -> None:
        """A failure between listing and claim cannot be acknowledged by old content."""
        self.cursor.fetchall.return_value = [(7, 2), (8, 0)]
        self.assertFalse(
            claim_assignee_digest_rows([7, 8], "token", expected_revisions={7: 1, 8: 0})
        )
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_called_once()

    def test_claim_captures_payload_revision(self) -> None:
        """Store the revision only after matching the delivered payload snapshot."""
        self.cursor.fetchall.return_value = [(7, 2), (8, 0)]
        self.assertTrue(
            claim_assignee_digest_rows([7, 8], "token", expected_revisions={7: 2, 8: 0})
        )
        self.assertIn(
            "digest_claimed_revision = digest_revision",
            self.cursor.execute.call_args.args[0],
        )

    def test_finish_requeues_changed_revision(self) -> None:
        """Only a matching revision can become sent, while the SES ID is retained."""
        finish_assignee_digest_rows([7, 8], "token", message_id="message")
        query = self.cursor.execute.call_args.args[0]
        self.assertIn("digest_revision IS DISTINCT FROM digest_claimed_revision", query)
        self.assertIn("THEN 'pending'", query)
        self.assertIn("digest_revision = digest_claimed_revision", query)
        self.assertIn("assignee_email_message_id = %s", query)

    def test_failure_revision_preserves_active_and_held_delivery(self) -> None:
        """Failure notification joins the caller transaction and never steals a claim."""
        record_tracker_digest_failure(7, self.connection)
        query, parameters = self.cursor.execute.call_args.args
        self.assertEqual(parameters, (None, None, None, 7))
        self.assertIn("digest_revision = digest_revision + 1", query)
        self.assertIn("IN ('sending', 'held')", query)
        self.assertNotIn("assignee_email_claim_token =", query)
        self.assertNotIn("digest_claimed_revision =", query)
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_not_called()

    def test_uncertain_delivery_is_held(self) -> None:
        """Timeouts and ambiguous delivery stay outside automatic retries."""
        finish_assignee_digest_rows(
            [7, 8], "token", error_message="failed", uncertain=True
        )
        self.assertEqual(self.cursor.execute.call_args.args[1][0], "held")

    def test_known_failure_can_be_explicitly_retried(self) -> None:
        """Pre-send errors become failed rather than held."""
        finish_assignee_digest_rows([7, 8], "token", error_message="failed")
        self.assertEqual(self.cursor.execute.call_args.args[1][0], "failed")

    def test_invalid_snapshot_fails_before_connect(self) -> None:
        """Reject duplicate, missing, and invalid IDs and empty tokens."""
        for row_ids, token in (
            ([], "token"),
            ([7, 7], "token"),
            ([0], "token"),
            ([7], ""),
        ):
            with self.subTest(row_ids=row_ids), self.assertRaises(ValueError):
                claim_assignee_digest_rows(row_ids, token)
        self.connection.cursor.assert_not_called()

    def test_digest_retry_selection_excludes_held_and_sending(self) -> None:
        """Failed rows require an explicit retry flag and never include uncertainty."""
        for include_failures, expected in (
            (False, ["pending"]),
            (True, ["pending", "failed"]),
        ):
            conn = FakeConnection()
            list_ready_assignee_digests(
                conn, include_previous_failures=include_failures
            )
            self.assertEqual(conn.cursor_instance.parameters[0], expected)

    def test_scan_conflict_preserves_metadata(self) -> None:
        """Upserts return the existing ID without replacing delivery or analyst metadata."""
        conn = FakeConnection()
        self.assertEqual(
            insert_daily_report_tracker_row(
                DailyReportTrackerRow(
                    scan_execution_key="scan:123", report_scan_notes="new"
                ),
                conn,
            ),
            7,
        )
        query = conn.cursor_instance.query
        self.assertIn("ON CONFLICT (scan_execution_key)", query)
        self.assertIn("WHERE scan_execution_key IS NOT NULL", query)
        update = query.split("DO UPDATE SET", 1)[1].split("RETURNING", 1)[0]
        self.assertNotIn("report_scan_notes", update)
        self.assertNotIn("assignee_email", update)
        self.assertEqual(conn.cursor_instance.parameters[-1], "scan:123")


if __name__ == "__main__":
    unittest.main()
