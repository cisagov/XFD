"""Opt-in real PostgreSQL tests for tracker uniqueness and operation ownership."""

# Standard Python Libraries
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import os
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

# Third-Party Libraries
import psycopg2
from psycopg2 import sql
from was_reports.data import daily_report_tracker as tracker
from was_reports.data import report_runs
from was_reports.tracker import update_service
from was_reports.tracker.models import TrackerItem


@unittest.skipUnless(
    os.environ.get("WAS_TEST_DATABASE_DSN"), "Requires isolated PostgreSQL"
)
class PostgresIntegrationTests(unittest.TestCase):
    """Exercise actual SQL in a disposable schema, never application tables."""

    def setUp(self) -> None:
        """Create a unique test schema using an explicitly supplied test database."""
        self.schema = "was_test_{}".format(uuid4().hex)
        self.connection = psycopg2.connect(os.environ["WAS_TEST_DATABASE_DSN"])
        if not self.connection.info.dbname.startswith("was_test_"):
            self.connection.close()
            self.fail("Use a disposable database with a was_test_ name.")
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
            )
            cursor.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
            )
            schema_path = (
                Path(__file__).parents[1] / "schema/stakeholders_table_creation.sql"
            )
            cursor.execute(schema_path.read_text())
            cursor.execute("INSERT INTO was_stakeholders (tag) VALUES ('TEST')")
        self.connection.commit()

    def tearDown(self) -> None:
        """Remove only this test's uniquely named schema."""
        self.connection.rollback()
        with self.connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema))
            )
        self.connection.commit()
        self.connection.close()

    def connect(self):
        """Create an independent connection scoped to the private test schema."""
        connection = psycopg2.connect(os.environ["WAS_TEST_DATABASE_DSN"])
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
            )
        connection.commit()
        return connection

    def tracker_row(self, execution: str = "first") -> int:
        """Insert one stable execution fixture."""
        return tracker.insert_daily_report_tracker_row(
            conn=self.connection,
            row=tracker.DailyReportTrackerRow(
                tag="TEST", data_pull_date=date.today(), scan_execution_key=execution
            ),
        )

    def test_concurrent_execution_insert_preserves_single_row(self) -> None:
        """Two refreshes cannot create two rows for the same scan execution."""
        barrier = Barrier(2)

        def insert() -> int:
            """Race independent database transactions on the execution constraint."""
            connection = self.connect()
            try:
                barrier.wait(timeout=5)
                return tracker.insert_daily_report_tracker_row(
                    conn=connection,
                    row=tracker.DailyReportTrackerRow(
                        tag="TEST", scan_execution_key="same"
                    ),
                )
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda unused: insert(), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertNotEqual(results[0], self.tracker_row("next"))

    def test_reclaimed_run_rejects_previous_generation_token(self) -> None:
        """A stale worker cannot complete or heartbeat a newly reclaimed run."""
        tracker_id = self.tracker_row()
        original = report_runs.create_report_run(
            "TEST", None, self.connection, source_tracker_id=tracker_id
        )
        report_runs.fail_report_run(
            original.id,
            "test failure",
            self.connection,
            generation_token=original.generation_token,
        )
        replacement = report_runs.retry_failed_report_run_for_tracker(
            tracker_id, self.connection
        )
        self.assertNotEqual(original.generation_token, replacement.generation_token)
        self.assertFalse(
            report_runs.touch_report_run(
                original.id, self.connection, generation_token=original.generation_token
            )
        )
        with self.assertRaises(report_runs.ActiveReportOperationError):
            report_runs.complete_report_run(
                original.id, self.connection, generation_token=original.generation_token
            )
        report_runs.complete_report_run(
            replacement.id,
            self.connection,
            output_path="s3://test/report.pdf",
            generation_token=replacement.generation_token,
        )

    def test_analyst_run_is_not_claimed_for_customer_delivery(self) -> None:
        """Persisted purpose is enforced by the SQL claim, not only the menu."""
        run = report_runs.create_report_run(
            "TEST", None, self.connection, delivery_purpose="analyst"
        )
        report_runs.complete_report_run(
            run.id,
            self.connection,
            output_path="s3://test/report.pdf",
            generation_token=run.generation_token,
        )
        self.assertIsNone(report_runs.claim_report_run_email(run.id, self.connection))
        claimed = report_runs.claim_report_run_email(
            run.id, self.connection, delivery_purpose="analyst"
        )
        self.assertEqual(claimed.delivery_purpose, "analyst")
        self.assertFalse(
            report_runs.touch_report_email_claim(
                run.id, self.connection, email_claim_token="wrong-token"
            )
        )

    def test_recovered_email_rejects_old_sender_completion(self) -> None:
        """Only a replacement claim can record delivery after explicit recovery."""
        run = report_runs.create_report_run("TEST", None, self.connection)
        report_runs.complete_report_run(
            run.id,
            self.connection,
            output_path="s3://test/report.pdf",
            generation_token=run.generation_token,
        )
        original = report_runs.claim_report_run_email(run.id, self.connection)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE was_report_runs SET email_claimed_at = NOW() - INTERVAL '1 day' "
                "WHERE id = %s",
                (run.id,),
            )
        self.connection.commit()
        self.assertEqual(
            report_runs.recover_stale_report_operations(self.connection), (0, 1)
        )
        replacement = report_runs.claim_report_run_email(
            run.id, self.connection, allow_held=True
        )
        with self.assertRaises(report_runs.ActiveReportOperationError):
            report_runs.mark_report_run_emailed(
                run.id,
                "old",
                self.connection,
                email_claim_token=original.email_claim_token,
            )
        report_runs.mark_report_run_emailed(
            run.id,
            "new",
            self.connection,
            email_claim_token=replacement.email_claim_token,
        )

    def test_digest_claim_race_and_exact_row_completion(self) -> None:
        """Only one sender claims a snapshot; later rows remain unsent."""
        row_ids = [self.tracker_row("one"), self.tracker_row("two")]
        barrier = Barrier(2)

        def claim(token: str) -> tuple[str, bool]:
            """Race digest claims on the same rows."""
            barrier.wait(timeout=5)
            return token, tracker.claim_assignee_digest_rows(row_ids, token)

        with patch("was_reports.utils.database.connect", side_effect=self.connect):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(claim, ["first", "second"]))
            winners = [token for token, claimed in results if claimed]
            self.assertEqual(len(winners), 1)
            later_id = self.tracker_row("later")
            with self.assertRaises(RuntimeError):
                tracker.finish_assignee_digest_rows(row_ids, "wrong", message_id="test")
            tracker.finish_assignee_digest_rows(row_ids, winners[0], message_id="test")
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT assignee_email_status FROM was_daily_report_tracker WHERE id = %s",
                (later_id,),
            )
            self.assertEqual(cursor.fetchone()[0], "pending")

    def test_schema_upgrade_preserves_history_and_can_repeat(self) -> None:
        """Apply update 010 twice to a pre-hardening schema with history."""
        tracker_id = self.tracker_row()
        report_runs.create_report_run("TEST", None, self.connection)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "UPDATE was_daily_report_tracker SET assignee_emailed_at = NOW() "
                "WHERE id = %s",
                (tracker_id,),
            )
            cursor.execute(
                "ALTER TABLE was_report_runs DROP COLUMN generation_token, "
                "DROP COLUMN email_claim_token, DROP COLUMN delivery_purpose"
            )
            cursor.execute(
                "ALTER TABLE was_daily_report_tracker DROP COLUMN scan_execution_key, "
                "DROP COLUMN assignee_email_status, DROP COLUMN assignee_email_claim_token, "
                "DROP COLUMN assignee_email_claimed_at, DROP COLUMN digest_revision, "
                "DROP COLUMN digest_claimed_revision"
            )
        self.connection.commit()
        update_path = (
            Path(__file__).parents[1]
            / "schema/updates/010_harden_report_delivery_and_tracker.sql"
        )
        upgrade = update_path.read_text()
        with self.connection.cursor() as cursor:
            cursor.execute(upgrade)
            cursor.execute(upgrade)
            cursor.execute(
                "SELECT assignee_email_status FROM was_daily_report_tracker WHERE id = %s",
                (tracker_id,),
            )
            self.assertEqual(cursor.fetchone()[0], "sent")
            cursor.execute("SELECT qualys_xml_report_status FROM was_report_runs")
            self.assertEqual(cursor.fetchone()[0], "CREATE_REQUESTED")

    def test_failure_during_digest_send_remains_pending(self) -> None:
        """Acknowledging an older snapshot must not swallow a new failure."""
        tracker_id = self.tracker_row()
        with patch("was_reports.utils.database.connect", side_effect=self.connect):
            self.assertTrue(
                tracker.claim_assignee_digest_rows(
                    [tracker_id], "owned", expected_revisions={tracker_id: 0}
                )
            )
            tracker.record_tracker_digest_failure(tracker_id, self.connection)
            self.connection.commit()
            tracker.finish_assignee_digest_rows(
                [tracker_id], "owned", message_id="test"
            )
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT assignee_email_status, digest_revision, assignee_emailed_at "
                "FROM was_daily_report_tracker WHERE id = %s",
                (tracker_id,),
            )
            self.assertEqual(cursor.fetchone(), ("pending", 1, None))

    def test_creation_intent_survives_generation_reclaim(self) -> None:
        """A retry must reconcile an uncertain create rather than authorizing another."""
        tracker_id = self.tracker_row()
        run = report_runs.create_report_run(
            "TEST", None, self.connection, source_tracker_id=tracker_id
        )
        self.assertTrue(
            report_runs.claim_qualys_report_creation(
                run.id, "xml", self.connection, generation_token=run.generation_token
            )
        )
        report_runs.fail_report_run(
            run.id, "timeout", self.connection, generation_token=run.generation_token
        )
        replacement = report_runs.retry_failed_report_run_for_tracker(
            tracker_id, self.connection
        )
        self.assertFalse(
            report_runs.claim_qualys_report_creation(
                run.id,
                "xml",
                self.connection,
                generation_token=replacement.generation_token,
            )
        )

    def test_deletion_is_recorded_before_external_call_and_not_repeated(self) -> None:
        """Persist an opt-in deletion claim before the external boundary executes."""
        item = TrackerItem(
            tag="TEST",
            scan_name="TEST Scan",
            status="Finished",
            result="Successful",
            launched_date="2026-09-01T12:00:00Z",
            next_scan_date="2026-10-01T12:00:00Z",
            nws=True,
            recent_nws="",
            removed_nws="<br>https://example.test",
            manual="",
            fceb=False,
            schedule_id=1,
            qualys_errors="",
            scan_execution_key="delete-test",
        )
        row = tracker.DailyReportTrackerRow(
            tag="TEST",
            status="Finished",
            result="Successful",
            report_scan_notes="DEACTIVATE",
            template="Deactivated",
            data_pull_date=date.today(),
        )

        def verify_pending(*arguments) -> None:
            """Read the committed claim through a separate connection before deleting."""
            connection = self.connect()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT report_scan_notes FROM was_daily_report_tracker WHERE scan_execution_key = 'delete-test'"
                    )
                    self.assertEqual(
                        cursor.fetchone()[0], "MANUAL QUALYS DELETION PENDING"
                    )
            finally:
                connection.close()

        with patch.object(
            update_service, "build_tracker_row", return_value=row
        ), patch.object(
            update_service, "delete_webapp", side_effect=verify_pending
        ) as delete:
            self.assertEqual(
                update_service.update_execution(
                    None,
                    item,
                    True,
                    date.today(),
                    "Analyst",
                    self.connection,
                    "delete-test",
                ),
                1,
            )
            self.assertEqual(
                update_service.update_execution(
                    None,
                    item,
                    True,
                    date.today(),
                    "Analyst",
                    self.connection,
                    "delete-test",
                ),
                0,
            )
            delete.assert_called_once()
