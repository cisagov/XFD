"""Tests for WAS daily report tracker data access."""

# Standard Python Libraries
from datetime import date, datetime, timezone
import unittest

# Third-Party Libraries
# First-Party Libraries
from was_reports.data.daily_report_tracker import (
    DailyReportTrackerRow,
    insert_daily_report_tracker_row,
    latest_tracker_pull_date,
    list_ready_assignee_digests,
    list_ready_report_candidates,
    list_tracker_rows_for_export,
    list_tracker_table_rows,
    mark_assignee_digest_emailed,
    mark_manual_tracker_report_sent,
    mark_tracker_report_manual,
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

    def test_insert_daily_report_tracker_row_maps_workbook_columns(self) -> None:
        """Insert tracker fields in workbook column order."""
        conn = FakeConnection()
        row = DailyReportTrackerRow(
            source_row_number=2,
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
            qualys_error=None,
            assignee_emailed_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            assignee_email_message_id="message-id",
            assignee_email_error=None,
        )

        row_id = insert_daily_report_tracker_row(row=row, conn=conn)

        self.assertEqual(row_id, 7)
        self.assertTrue(conn.committed)
        self.assertIn("was_daily_report_tracker", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters[0], 2)
        self.assertEqual(conn.cursor_instance.parameters[1], date(2026, 8, 26))
        self.assertEqual(conn.cursor_instance.parameters[2], "CUSTOMER_TAG")
        self.assertEqual(conn.cursor_instance.parameters[4], 3)
        self.assertEqual(conn.cursor_instance.parameters[15], "5, 1, 0")
        self.assertEqual(conn.cursor_instance.parameters[19], "STATIC PASSWORD")
        self.assertEqual(conn.cursor_instance.parameters[20], 12345)
        self.assertEqual(
            conn.cursor_instance.parameters[22],
            datetime(2026, 8, 26, tzinfo=timezone.utc),
        )
        self.assertEqual(conn.cursor_instance.parameters[23], "message-id")

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
                    None,
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
                ),
                (
                    2,
                    None,
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
                ),
            ],
        )

        digests = list_ready_assignee_digests(
            conn=conn,
            data_pull_date=date(2026, 8, 26),
        )

        self.assertEqual(len(digests), 1)
        self.assertEqual(digests[0].email, "analyst@example.gov")
        self.assertEqual(len(digests[0].rows), 2)
        self.assertEqual(conn.cursor_instance.parameters, (date(2026, 8, 26),))

    def test_list_ready_report_candidates_finds_unsent_finished_rows(self) -> None:
        """Find recent tracker rows without sent reports or existing claims."""
        conn = FakeConnection(
            fetchall_rows=[
                (7, "TAG1", date(2026, 9, 1), 12345, 3, None, None, None),
            ]
        )

        candidates = list_ready_report_candidates(
            conn=conn,
            stakeholder_tag="TAG1",
            limit=5,
        )

        self.assertEqual(candidates[0].id, 7)
        self.assertEqual(candidates[0].tag, "TAG1")
        self.assertIn("tracker.report_sent_date IS NULL", conn.cursor_instance.query)
        self.assertIn("runs.source_tracker_id", conn.cursor_instance.query)
        self.assertIn(
            "stakeholders.manual_report IS NOT TRUE", conn.cursor_instance.query
        )
        self.assertEqual(conn.cursor_instance.parameters, ("TAG1", 5))

    def test_mark_tracker_report_manual_updates_unsent_row(self) -> None:
        """Send generation failures to the assigned analyst for manual handling."""
        conn = FakeConnection()

        mark_tracker_report_manual(tracker_id=7, conn=conn)

        self.assertTrue(conn.committed)
        self.assertIn("report_scan_notes = 'MANUAL'", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, (7,))

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
                    8,
                    "failed",
                    "pending",
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
        self.assertIn("runs.status = 'failed'", conn.cursor_instance.query)
        self.assertIn("stakeholders.manual_report IS TRUE", conn.cursor_instance.query)
        self.assertNotIn(
            "stakeholders.manual_report IS NOT TRUE",
            conn.cursor_instance.query,
        )
        self.assertEqual(conn.cursor_instance.parameters, ("TAG1", 1))

    def test_mark_assignee_digest_emailed_updates_matching_rows(self) -> None:
        """Mark unsent rows for one assignee and pull date."""
        conn = FakeConnection()

        mark_assignee_digest_emailed(
            conn=conn,
            assignee_id=3,
            data_pull_date=date(2026, 8, 26),
            message_id="message-id",
        )

        self.assertTrue(conn.committed)
        self.assertIn("assignee_emailed_at = NOW()", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("message-id", 3, date(2026, 8, 26)),
        )

    def test_list_tracker_rows_for_export_filters_rows(self) -> None:
        """Return tracker rows for CSV export."""
        conn = FakeConnection(
            fetchall_rows=[
                (
                    None,
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
        self.assertIn("data_pull_date >= CURRENT_DATE - %s", conn.cursor_instance.query)
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


if __name__ == "__main__":
    unittest.main()
