"""Tests for WAS report run data access."""

# Standard Python Libraries
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Event, Lock
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.data import report_runs


class FakeCursor:
    """Small cursor test double for report run tests."""

    def __init__(self, row=None):
        """Initialize the fake cursor."""
        self.row = row
        self.query = None
        self.parameters = None

    def __enter__(self):
        """Return this cursor for context manager usage."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""

    def execute(self, query, parameters):
        """Capture the executed query and parameters."""
        if str(query).count("%s") != len(parameters):
            raise AssertionError("SQL placeholders must match bound parameters.")
        self.query = query
        self.parameters = parameters

    def fetchone(self):
        """Return the configured row."""
        return self.row

    def fetchall(self):
        """Return configured rows for list queries."""
        return self.row


class FakeConnection:
    """Small connection test double for report run tests."""

    def __init__(self, row=None):
        """Initialize the fake connection."""
        self.cursor_instance = FakeCursor(row=row)
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


class ReportRunTests(unittest.TestCase):
    """Validate report run persistence helpers."""

    @patch("was_reports.utils.database.close")
    @patch("was_reports.utils.database.connect")
    @patch("was_reports.data.report_runs.create_report_run")
    @patch("was_reports.data.daily_report_tracker.list_ready_report_candidates")
    def test_automated_claim_rechecks_current_candidate(
        self, candidates, create_run, connect, close
    ) -> None:
        """Reject a stale row when a newer row or safety hold replaces it."""
        conn = connect.return_value
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("TAG", 42, date(2026, 9, 21))
        candidates.return_value = [SimpleNamespace(id=102)]
        result = report_runs.create_report_run_for_tracker(
            "TAG", 101, enforce_automated_eligibility=True, days_back=7
        )
        self.assertIsNone(result)
        candidates.assert_called_once_with(conn, stakeholder_tag="TAG", days_back=7)
        create_run.assert_not_called()
        conn.rollback.assert_called_once_with()
        close.assert_called_once_with(conn)
        conn.set_session.assert_called_once_with(
            isolation_level="READ COMMITTED", autocommit=False
        )
        queries = [str(call.args[0]) for call in cursor.execute.call_args_list]
        self.assertIn("pg_advisory_xact_lock", queries[0])
        self.assertEqual(
            cursor.execute.call_args_list[0].args[1], ("was-tracker-tag:TAG",)
        )
        self.assertIn("FOR UPDATE", queries[1])

    @patch("was_reports.utils.database.close")
    @patch("was_reports.utils.database.connect")
    @patch("was_reports.data.report_runs.create_report_run")
    @patch("was_reports.data.daily_report_tracker.list_ready_report_candidates")
    def test_automated_claim_rejects_changed_identity(
        self, candidates, create_run, connect, close
    ) -> None:
        """Do not claim a row whose execution changed while acquiring its lock."""
        conn = connect.return_value
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("OTHER", 43, date(2026, 9, 21))
        self.assertIsNone(
            report_runs.create_report_run_for_tracker(
                "TAG", 101, enforce_automated_eligibility=True
            )
        )
        candidates.assert_not_called()
        create_run.assert_not_called()
        conn.rollback.assert_called_once_with()

    @patch("was_reports.utils.database.close")
    @patch("was_reports.utils.database.connect")
    @patch("was_reports.data.report_runs.create_report_run")
    def test_automated_claim_releases_transaction_on_recheck_error(
        self, create_run, connect, close
    ) -> None:
        """A failed eligibility read must not leave an execution lock open."""
        with patch(
            "was_reports.data.report_runs._lock_eligible_automated_tracker",
            side_effect=RuntimeError("read failed"),
        ):
            with self.assertRaises(RuntimeError):
                report_runs.create_report_run_for_tracker(
                    "TAG", 101, enforce_automated_eligibility=True
                )
        create_run.assert_not_called()
        connect.return_value.rollback.assert_called_once_with()
        close.assert_called_once_with(connect.return_value)

    @patch("was_reports.utils.database.close")
    @patch("was_reports.utils.database.connect")
    @patch("was_reports.data.report_runs.create_report_run")
    def test_manual_tracker_claim_keeps_existing_behavior(
        self, create_run, connect, close
    ) -> None:
        """Default/manual claims do not apply automated eligibility restrictions."""
        result = report_runs.create_report_run_for_tracker("TAG", 101)
        self.assertIs(result, create_run.return_value)
        connect.return_value.cursor.assert_not_called()
        connect.return_value.set_session.assert_not_called()
        create_run.assert_called_once_with(
            stakeholder_tag="TAG",
            scheduled_epoch=None,
            source_tracker_id=101,
            conn=connect.return_value,
        )

    @patch("was_reports.utils.database.close")
    @patch("was_reports.utils.database.connect")
    @patch("was_reports.data.report_runs.create_report_run")
    @patch("was_reports.data.daily_report_tracker.list_ready_report_candidates")
    def test_sibling_claims_serialize_before_rechecking(
        self, candidates, create_run, connect, close
    ) -> None:
        """Model tag serialization for two IDs from different executions."""
        execution_lock = Lock()
        first_check = Event()
        second_lock_attempt = Event()
        claimed_ids: list[int] = []
        lock_keys: list[str] = []
        connection_ids: dict[int, int] = {}

        def connection_for(row_id: int, tag: str):
            """Build a connection whose advisory transaction lock blocks peers."""
            conn = MagicMock()
            connection_ids[id(conn)] = row_id
            cursor = conn.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = (tag, row_id, date(2026, 9, 21))

            def execute(query, parameters):
                """Use a local mutex to model PostgreSQL's transaction lock."""
                if "pg_advisory_xact_lock" in str(query):
                    lock_keys.append(parameters[0])
                    if row_id == 102:
                        second_lock_attempt.set()
                    if not execution_lock.acquire(timeout=5):
                        raise AssertionError("Execution lock was not released")

            cursor.execute.side_effect = execute
            conn.commit.side_effect = execution_lock.release
            conn.rollback.side_effect = execution_lock.release
            return conn

        first_conn = connection_for(101, "TAG")
        second_conn = connection_for(102, "TAG")
        connect.side_effect = [first_conn, second_conn]

        def eligible(conn, **kwargs):
            """Read sibling claims only after the execution lock is acquired."""
            if conn is first_conn:
                first_check.set()
                if not second_lock_attempt.wait(timeout=5):
                    raise AssertionError("Second claim did not reach lock")
            return [] if claimed_ids else [SimpleNamespace(id=connection_ids[id(conn)])]

        def insert_run(**kwargs):
            """Persist a simulated claim and release the transaction lock."""
            claimed_ids.append(kwargs["source_tracker_id"])
            kwargs["conn"].commit()
            return SimpleNamespace(id=1)

        candidates.side_effect = eligible
        create_run.side_effect = insert_run
        with ThreadPoolExecutor(max_workers=2) as workers:
            first = workers.submit(
                report_runs.create_report_run_for_tracker, "TAG", 101, True, 7
            )
            self.assertTrue(first_check.wait(timeout=5))
            second = workers.submit(
                report_runs.create_report_run_for_tracker, "TAG", 102, True, 7
            )
            self.assertIsNotNone(first.result(timeout=5))
            self.assertIsNone(second.result(timeout=5))
        self.assertEqual(claimed_ids, [101])
        self.assertEqual(lock_keys, ["was-tracker-tag:TAG"] * 2)
        self.assertEqual(candidates.call_count, 2)

    def test_creation_intent_commits_before_authorizing_post(self) -> None:
        """Authorize one create only when the token-fenced intent commits."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (7,)
        self.assertIs(
            report_runs.claim_qualys_report_creation(
                7, "xml", conn, generation_token="owner"
            ),
            True,
        )
        query, parameters = cursor.execute.call_args.args
        self.assertIn("CREATE_REQUESTED", str(query))
        self.assertIn("generation_token = %s", str(query))
        self.assertIn("IS NULL", str(query))
        self.assertEqual(parameters, (7, "running", "owner"))
        conn.commit.assert_called_once_with()

    def test_existing_intent_reconciles_without_reauthorizing_create(
        self,
    ) -> None:
        """Distinguish an owned existing intent from a lost lease."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [None, (7,)]
        self.assertIs(
            report_runs.claim_qualys_report_creation(
                7, "detail", conn, generation_token="owner"
            ),
            False,
        )
        self.assertEqual(cursor.execute.call_count, 2)
        conn.commit.assert_called_once_with()

    def test_creation_intent_does_not_authorize_on_lost_or_uncertain_commit(
        self,
    ) -> None:
        """Neither a lost lease nor a lost commit response may permit POST."""
        for lost_lease in (True, False):
            with self.subTest(lost_lease=lost_lease):
                conn = MagicMock()
                cursor = conn.cursor.return_value.__enter__.return_value
                if lost_lease:
                    cursor.fetchone.return_value = None
                    expected = report_runs.ActiveReportOperationError
                else:
                    cursor.fetchone.return_value = (7,)
                    conn.commit.side_effect = OSError("commit uncertain")
                    expected = OSError
                with self.assertRaises(expected):
                    report_runs.claim_qualys_report_creation(
                        7, "xml", conn, generation_token="owner"
                    )
                conn.rollback.assert_called_once_with()

    def test_record_id_preserves_creation_marker(self) -> None:
        """Recording the recovered ID must not reset creation intent to NULL."""
        conn = FakeConnection(row=(7,))
        report_runs.record_qualys_report_id(
            7, "xml", "saved", conn, generation_token="owner"
        )
        self.assertNotIn("qualys_xml_report_status", str(conn.cursor_instance.query))

    def test_customer_failures_requeue_digest_in_same_transaction(
        self,
    ) -> None:
        """Increment failure revisions only for customer-linked failed runs."""
        for purpose in ("customer", "analyst"):
            for email in (True, False):
                with self.subTest(purpose=purpose, email=email):
                    conn = MagicMock()
                    cursor = conn.cursor.return_value.__enter__.return_value
                    cursor.fetchone.return_value = (7, 42, purpose)
                    if email:
                        report_runs.mark_report_run_email_failed(
                            7, "failed", conn, email_claim_token="owner"
                        )
                    else:
                        report_runs.fail_report_run(
                            7, "failed", conn, generation_token="owner"
                        )
                    self.assertEqual(
                        cursor.execute.call_count,
                        2 if purpose == "customer" else 1,
                    )
                    if purpose == "customer":
                        self.assertIn(
                            "digest_revision = digest_revision + 1",
                            cursor.execute.call_args.args[0],
                        )
                        self.assertIn(
                            "position(%s in COALESCE(report_scan_notes",
                            cursor.execute.call_args.args[0],
                        )
                        self.assertIn("concat_ws", cursor.execute.call_args.args[0])
                        self.assertEqual(cursor.execute.call_args.args[1][-1], 42)
                        self.assertIn("MANUAL: ", cursor.execute.call_args.args[1][0])
                        self.assertIn("failed", cursor.execute.call_args.args[1][0])
                    conn.commit.assert_called_once_with()

    def test_digest_requeue_error_rolls_back_report_failure(self) -> None:
        """Do not commit failure without its new digest revision."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (7, 42, "customer")
        cursor.execute.side_effect = [None, OSError("digest unavailable")]
        with self.assertRaises(OSError):
            report_runs.fail_report_run(7, "failed", conn, generation_token="owner")
        conn.commit.assert_not_called()
        conn.rollback.assert_called_once_with()

    def test_stale_recovery_requeues_only_customer_failure_revisions(
        self,
    ) -> None:
        """Publish all recovered customer failures in the recovery transaction."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1, [42])
        cursor.fetchall.return_value = [
            (7, 43, "customer"),
            (8, 99, "analyst"),
        ]
        self.assertEqual(report_runs.recover_stale_report_operations(conn), (1, 2))
        self.assertEqual(cursor.execute.call_count, 4)
        self.assertEqual(cursor.execute.call_args_list[2].args[1][-1], 42)
        self.assertEqual(cursor.execute.call_args_list[3].args[1][-1], 43)
        self.assertIn(
            "Report generation lease expired",
            cursor.execute.call_args_list[2].args[1][0],
        )
        self.assertIn(
            "Email delivery lease expired", cursor.execute.call_args_list[3].args[1][0]
        )
        conn.commit.assert_called_once_with()

    def test_generation_mutations_reject_stale_tokens(self) -> None:
        """Fence every generation mutation even when the run ID is reused."""
        operations = [
            (report_runs.complete_report_run, {"report_run_id": 7}),
            (
                report_runs.fail_report_run,
                {"report_run_id": 7, "error_message": "failed"},
            ),
            (
                report_runs.record_qualys_report_id,
                {
                    "report_run_id": 7,
                    "artifact_label": "xml",
                    "report_id": "xml-1",
                },
            ),
            (
                report_runs.clear_qualys_report_id,
                {
                    "report_run_id": 7,
                    "artifact_label": "xml",
                    "report_id": "xml-1",
                },
            ),
            (
                report_runs.record_qualys_report_status,
                {
                    "report_run_id": 7,
                    "artifact_label": "xml",
                    "status": "COMPLETE",
                },
            ),
        ]
        for operation, arguments in operations:
            with self.subTest(operation=operation.__name__):
                conn = FakeConnection(row=None)
                with self.assertRaises(report_runs.ActiveReportOperationError):
                    operation(conn=conn, generation_token="stale-token", **arguments)
                self.assertIn("generation_token = %s", str(conn.cursor_instance.query))
                self.assertIn("stale-token", conn.cursor_instance.parameters)
                self.assertTrue(conn.rolled_back)
                self.assertFalse(conn.committed)

    def test_email_mutations_reject_stale_tokens(self) -> None:
        """Prevent an old sender from stamping or failing a reclaimed email."""
        for operation, arguments in [
            (report_runs.mark_report_run_emailed, {"message_id": "ses-id"}),
            (
                report_runs.mark_report_run_email_failed,
                {"error_message": "failed"},
            ),
        ]:
            with self.subTest(operation=operation.__name__):
                conn = FakeConnection(row=None)
                with self.assertRaises(report_runs.ActiveReportOperationError):
                    operation(
                        7, conn=conn, email_claim_token="stale-token", **arguments
                    )
                self.assertIn("email_claim_token = %s", conn.cursor_instance.query)
                self.assertEqual(conn.cursor_instance.parameters[-1], "stale-token")
                self.assertTrue(conn.rolled_back)
                self.assertFalse(conn.committed)

    def test_confirm_held_email_delivered_updates_run_and_tracker_atomically(
        self,
    ) -> None:
        """Record confirmed delivery without invoking or claiming the mailer."""
        conn = FakeConnection(row=(7,))

        report_runs.confirm_held_report_email_delivered(
            7,
            "SES event 2026-09-29T17:00:00Z",
            conn,
        )

        query = conn.cursor_instance.query
        self.assertIn("FOR UPDATE OF runs, tracker", query)
        self.assertIn("UPDATE was_daily_report_tracker", query)
        self.assertIn("report_sent_date = CURRENT_DATE", query)
        self.assertIn("runs.delivery_purpose = 'customer'", query)
        self.assertIn("runs.email_claimed_at IS NULL", query)
        self.assertIn("email_claim_token = NULL", query)
        self.assertIn("UPDATE was_batch_report_attempts", query)
        self.assertIn("attempts.report_run_id = reconciled_run.id", query)
        self.assertIn("SET sent = TRUE", query)
        self.assertNotIn("SET email_message_id", query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                7,
                report_runs.COMPLETED,
                report_runs.EMAIL_HELD,
                report_runs.EMAIL_SENT,
                "Manual email reconciliation: delivery confirmed: "
                "SES event 2026-09-29T17:00:00Z",
            ),
        )
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)

    def test_inspect_held_email_reconciliation_reports_eligibility(self) -> None:
        """Preview reconciliation without changing transaction state."""
        conn = FakeConnection(
            row=(
                7,
                "TAG1",
                report_runs.COMPLETED,
                report_runs.EMAIL_HELD,
                "customer",
                None,
                None,
                42,
                42,
                None,
                False,
            )
        )

        preview = report_runs.inspect_held_report_email_reconciliation(7, conn)

        self.assertTrue(preview.eligible)
        self.assertIsNone(preview.ineligible_reason)
        self.assertEqual(preview.source_tracker_id, 42)
        self.assertEqual(conn.cursor_instance.parameters, (7,))
        self.assertFalse(conn.committed)
        self.assertFalse(conn.rolled_back)

    def test_inspect_held_email_reconciliation_explains_active_claim(self) -> None:
        """Explain why an active sender prevents operator reconciliation."""
        claimed_at = datetime(2026, 9, 29, tzinfo=timezone.utc)
        conn = FakeConnection(
            row=(
                7,
                "TAG1",
                report_runs.COMPLETED,
                report_runs.EMAIL_HELD,
                "customer",
                None,
                claimed_at,
                42,
                42,
                None,
                False,
            )
        )

        preview = report_runs.inspect_held_report_email_reconciliation(7, conn)

        self.assertFalse(preview.eligible)
        self.assertEqual(
            preview.ineligible_reason,
            "An email delivery claim is active.",
        )

    @patch.object(report_runs, "uuid4", return_value="authorization-token")
    def test_confirm_held_email_not_delivered_releases_retry_safely(
        self,
        uuid,
    ) -> None:
        """Authorize an explicit retry while retaining the held safety state."""
        conn = FakeConnection(row=("authorization-token",))

        token = report_runs.confirm_held_report_email_not_delivered(
            7,
            "  SES event history confirms   rejection  ",
            "stored-customer",
            conn,
        )

        self.assertEqual(token, "authorization-token")
        uuid.assert_called_once_with()
        query = conn.cursor_instance.query
        self.assertNotIn("SET email_status", query)
        self.assertIn("NULLIF(runs.email_error, '')", query)
        self.assertIn("runs.email_claimed_at IS NULL", query)
        self.assertIn("email_claim_token = %s", query)
        self.assertIn("tracker.report_sent_date IS NULL", query)
        self.assertIn("FOR UPDATE OF runs, tracker", query)
        self.assertNotIn("SET report_sent_date", query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                7,
                report_runs.COMPLETED,
                report_runs.EMAIL_HELD,
                "Manual email reconciliation: non-delivery confirmed: "
                "SES event history confirms rejection",
                "Manual email reconciliation: retry authorized: "
                "token=authorization-token; scope=stored-customer",
                "authorization-token",
            ),
        )
        self.assertTrue(conn.committed)
        self.assertFalse(conn.rolled_back)

    def test_held_email_reconciliation_rejects_changed_state(self) -> None:
        """Roll back when the run, claim, delivery, or tracker state changed."""
        operations = [
            (
                report_runs.confirm_held_report_email_delivered,
                (
                    7,
                    "delivery evidence",
                ),
            ),
            (
                report_runs.confirm_held_report_email_not_delivered,
                (7, "non-delivery evidence", "stored-customer"),
            ),
        ]
        for operation, arguments in operations:
            with self.subTest(operation=operation.__name__):
                conn = FakeConnection(row=None)
                with self.assertRaises(report_runs.ActiveReportOperationError):
                    operation(*arguments, conn)
                self.assertIn("runs.email_status = %s", conn.cursor_instance.query)
                self.assertIn(
                    "runs.email_claimed_at IS NULL",
                    conn.cursor_instance.query,
                )
                self.assertIn(
                    "tracker.report_sent_date IS NULL",
                    conn.cursor_instance.query,
                )
                self.assertTrue(conn.rolled_back)
                self.assertFalse(conn.committed)

    def test_held_email_reconciliation_requires_audit_evidence(self) -> None:
        """Reject blank evidence before beginning a database transaction."""
        conn = FakeConnection(row=(7,))

        with self.assertRaises(ValueError):
            report_runs.confirm_held_report_email_delivered(7, " \n ", conn)

        self.assertIsNone(conn.cursor_instance.query)
        self.assertFalse(conn.committed)
        self.assertFalse(conn.rolled_back)

    def test_held_email_reconciliation_limits_audit_evidence(self) -> None:
        """Reject an oversized operator reference before opening a transaction."""
        conn = FakeConnection(row=(7,))

        with self.assertRaises(ValueError):
            report_runs.confirm_held_report_email_delivered(
                7,
                "x" * (report_runs.MAX_EMAIL_RECONCILIATION_EVIDENCE_LENGTH + 1),
                conn,
            )

        self.assertIsNone(conn.cursor_instance.query)

    def test_heartbeats_cannot_refresh_reclaimed_runs(self) -> None:
        """Require the owner token for generation and email heartbeats."""
        for operation, token_name in [
            (report_runs.touch_report_run, "generation_token"),
            (report_runs.touch_report_email_claim, "email_claim_token"),
        ]:
            with self.subTest(operation=operation.__name__):
                conn = FakeConnection(row=None)
                self.assertFalse(operation(7, conn, **{token_name: "old-token"}))
                self.assertIn("{} = %s".format(token_name), conn.cursor_instance.query)
                self.assertEqual(conn.cursor_instance.parameters[-1], "old-token")

    def test_retry_rotates_generation_token(self) -> None:
        """Keep the report ID but issue an independent token for each retry."""
        conn = FakeConnection(row=(7, "TAG1", report_runs.RUNNING))
        original = report_runs.create_report_run("TAG1", None, conn)
        retried = report_runs.retry_failed_report_run_for_tracker(42, conn)
        self.assertEqual(original.id, retried.id)
        self.assertTrue(original.generation_token)
        self.assertNotEqual(original.generation_token, retried.generation_token)
        self.assertIn(retried.generation_token, conn.cursor_instance.parameters)

    def test_failure_tracker_update_is_part_of_fenced_statement(self) -> None:
        """Update tracker notes only from the token-matched failed run."""
        conn = FakeConnection(row=(7, None, "customer"))
        report_runs.fail_report_run(7, "failed", conn, generation_token="owner")
        self.assertIn("FROM changed_run", conn.cursor_instance.query)
        self.assertIn(
            "SELECT id, source_tracker_id, delivery_purpose FROM changed_run",
            conn.cursor_instance.query,
        )

    def test_analyst_delivery_never_stamps_customer_tracker(self) -> None:
        """Limit customer report-sent stamps to customer-purpose deliveries."""
        conn = FakeConnection(row=(7, None, "customer"))
        report_runs.mark_report_run_emailed(
            7, "ses-id", conn, email_claim_token="owner"
        )
        self.assertIn(
            "emailed_run.delivery_purpose = 'customer'",
            conn.cursor_instance.query,
        )

    def test_invalid_delivery_purpose_fails_before_database_use(self) -> None:
        """Reject unsupported delivery purposes at the data boundary."""
        conn = FakeConnection()
        with self.assertRaises(ValueError):
            report_runs.create_report_run("TAG1", None, conn, delivery_purpose="other")
        self.assertIsNone(conn.cursor_instance.query)

    def test_get_qualys_report_polling_state_returns_saved_ids(self) -> None:
        """Load report IDs used to resume Qualys polling after a restart."""
        conn = FakeConnection(row=("detail-123", "xml-456"))

        state = report_runs.get_qualys_report_polling_state(7, conn)

        self.assertEqual(state.detail_report_id, "detail-123")
        self.assertEqual(state.xml_report_id, "xml-456")
        self.assertEqual(conn.cursor_instance.parameters, (7,))

    def test_record_qualys_report_id_requires_active_lease(self) -> None:
        """Persist a created Qualys report ID only for the active worker."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.record_qualys_report_id(
            7, "xml", "xml-456", conn, generation_token="token"
        )

        self.assertTrue(conn.committed)
        self.assertIn("qualys_xml_report_id", str(conn.cursor_instance.query))
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("xml-456", 7, report_runs.RUNNING, "token"),
        )

    def test_record_qualys_report_status_rejects_expired_lease(self) -> None:
        """Prevent a stale poller from updating a reclaimed report run."""
        conn = FakeConnection(row=None)

        with self.assertRaises(report_runs.ActiveReportOperationError):
            report_runs.record_qualys_report_status(
                7,
                "detail",
                "RUNNING",
                conn,
                generation_token="token",
            )

        self.assertTrue(conn.rolled_back)

    def test_clear_qualys_report_id_requires_matching_active_report(
        self,
    ) -> None:
        """Clear only the temporary report owned by the active run lease."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.clear_qualys_report_id(
            7, "xml", "xml-456", conn, generation_token="token"
        )

        self.assertTrue(conn.committed)
        self.assertIn(
            "qualys_xml_report_id",
            str(conn.cursor_instance.query),
        )
        self.assertEqual(
            conn.cursor_instance.parameters,
            (7, report_runs.RUNNING, "token", "xml-456"),
        )

    def test_create_report_run_inserts_running_record(self) -> None:
        """Create a running report execution record."""
        conn = FakeConnection(row=(7, "TAG1", report_runs.RUNNING))

        report_run = report_runs.create_report_run(
            stakeholder_tag="TAG1",
            scheduled_epoch=1720000001,
            conn=conn,
        )

        self.assertEqual(report_run.id, 7)
        self.assertEqual(report_run.status, report_runs.RUNNING)
        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                "TAG1",
                report_runs.RUNNING,
                1720000001,
                None,
                report_runs.EMAIL_PENDING,
                report_run.generation_token,
                "customer",
                "TAG1",
                report_runs.RUNNING,
            ),
        )
        self.assertIn("ON CONFLICT", conn.cursor_instance.query)
        self.assertIn("active_run.status = %s", conn.cursor_instance.query)

    def test_create_report_run_skips_an_active_schedule_claim(self) -> None:
        """Return no run when another worker already claimed the schedule."""
        conn = FakeConnection(row=None)

        report_run = report_runs.create_report_run(
            stakeholder_tag="TAG1",
            scheduled_epoch=1720000001,
            conn=conn,
        )

        self.assertIsNone(report_run)
        self.assertTrue(conn.committed)

    def test_create_report_run_claims_source_tracker_row(self) -> None:
        """Claim one tracker row using its unique report-run link."""
        conn = FakeConnection(row=(8, "TAG2", report_runs.RUNNING))

        report_run = report_runs.create_report_run(
            stakeholder_tag="TAG2",
            scheduled_epoch=None,
            source_tracker_id=42,
            conn=conn,
        )

        self.assertEqual(report_run.id, 8)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                "TAG2",
                report_runs.RUNNING,
                None,
                42,
                report_runs.EMAIL_PENDING,
                report_run.generation_token,
                "customer",
                "TAG2",
                report_runs.RUNNING,
            ),
        )

    @patch("was_reports.utils.database.close")
    @patch("was_reports.utils.database.connect")
    @patch("was_reports.data.report_runs.create_report_run")
    @patch("was_reports.data.report_runs.lock_tracker_tag")
    @patch("was_reports.data.report_runs.recover_stale_report_operations")
    def test_on_demand_claim_locks_tag_before_mutable_rows(
        self,
        recover_stale,
        lock_tag,
        create_run,
        connect,
        close,
    ) -> None:
        """Keep on-demand creation in the shared advisory-first lock order."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(False,), None]
        connect.return_value = connection
        create_run.return_value = SimpleNamespace(id=17)
        sequence = MagicMock()
        sequence.attach_mock(recover_stale, "recover")
        sequence.attach_mock(lock_tag, "lock_tag")
        sequence.attach_mock(cursor.execute, "execute")
        sequence.attach_mock(create_run, "create_run")

        result = report_runs.create_on_demand_report_run("TAG1")

        self.assertEqual(result.id, 17)
        self.assertEqual(sequence.mock_calls[0], call.recover(connection))
        self.assertEqual(
            sequence.mock_calls[1],
            call.lock_tag(connection, "TAG1"),
        )
        stakeholder_query = str(sequence.mock_calls[2].args[0])
        active_query = str(sequence.mock_calls[3].args[0])
        self.assertIn("was_stakeholders", stakeholder_query)
        self.assertIn("status = 'running'", active_query)
        self.assertEqual(sequence.mock_calls[4][0], "create_run")
        close.assert_called_once_with(connection)

    def test_complete_report_run_sets_completed_status(self) -> None:
        """Mark an existing report execution as completed."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.complete_report_run(
            report_run_id=7, conn=conn, generation_token="token"
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                None,
                None,
                None,
                7,
                report_runs.RUNNING,
                "token",
            ),
        )

    def test_retry_failed_tracker_run_reclaims_existing_record(self) -> None:
        """Reuse a failed tracker run without violating its unique link."""
        conn = FakeConnection(row=(7, "TAG1", report_runs.RUNNING))

        report_run = report_runs.retry_failed_report_run_for_tracker(
            source_tracker_id=42,
            conn=conn,
        )

        self.assertEqual(report_run.id, 7)
        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.RUNNING,
                report_run.generation_token,
                report_runs.EMAIL_PENDING,
                42,
                report_runs.FAILED,
                report_runs.RUNNING,
                False,
            ),
        )
        self.assertIn("error_message = NULL", conn.cursor_instance.query)
        self.assertIn("active_run.status = %s", conn.cursor_instance.query)

    def test_retry_failed_tracker_run_locks_tag_before_reclaim(self) -> None:
        """Serialize failed-run retries with every same-tag generation claim."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (7, "TAG1", report_runs.RUNNING)

        report_runs.retry_failed_report_run_for_tracker(42, connection)

        lock_query = str(cursor.execute.call_args_list[0].args[0])
        update_query = str(cursor.execute.call_args_list[1].args[0])
        self.assertIn("pg_advisory_xact_lock", lock_query)
        self.assertEqual(
            cursor.execute.call_args_list[0].args[1],
            (42, report_runs.FAILED),
        )
        self.assertIn("NOT EXISTS", update_query)
        self.assertIn("active_run.status = %s", update_query)

    def test_complete_report_run_can_store_output_metadata(self) -> None:
        """Mark a report complete with artifact details."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.complete_report_run(
            report_run_id=7,
            output_path="/WAS_REPORT_GENERATION/docs/TAG1_report_2026-08-25.pdf",
            artifact_type="pdf",
            conn=conn,
            generation_token="token",
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                None,
                "/WAS_REPORT_GENERATION/docs/TAG1_report_2026-08-25.pdf",
                "pdf",
                7,
                report_runs.RUNNING,
                "token",
            ),
        )

    def test_fail_report_run_sets_failed_status(self) -> None:
        """Mark an existing report execution as failed."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.fail_report_run(
            report_run_id=7,
            error_message="Report generation failed.",
            conn=conn,
            generation_token="token",
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.FAILED,
                "Report generation failed.",
                None,
                None,
                7,
                report_runs.RUNNING,
                "token",
            ),
        )

    def test_complete_report_run_rejects_an_expired_lease(self) -> None:
        """Prevent an expired worker from resurrecting a recovered run."""
        conn = FakeConnection(row=None)

        with self.assertRaises(report_runs.ActiveReportOperationError):
            report_runs.complete_report_run(
                report_run_id=7, conn=conn, generation_token="token"
            )

        self.assertTrue(conn.rolled_back)

    def test_mark_report_run_emailed_records_message_id(self) -> None:
        """Record successful email delivery metadata."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.mark_report_run_emailed(
            report_run_id=7,
            message_id="message-id",
            conn=conn,
            email_claim_token="token",
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                "message-id",
                report_runs.EMAIL_RECONCILIATION_PREFIX,
                report_runs.EMAIL_SENT,
                7,
                report_runs.EMAIL_SENDING,
                "token",
            ),
        )
        self.assertIn("report_sent_date = CURRENT_DATE", conn.cursor_instance.query)
        self.assertIn(
            "UPDATE was_batch_report_attempts",
            conn.cursor_instance.query,
        )
        self.assertIn(
            "attempts.report_run_id = emailed_run.id",
            conn.cursor_instance.query,
        )

    def test_mark_report_run_email_failed_records_error(self) -> None:
        """Record email delivery failure metadata."""
        conn = FakeConnection(row=(7, None, "customer"))

        report_runs.mark_report_run_email_failed(
            report_run_id=7,
            error_message="delivery failed",
            conn=conn,
            email_claim_token="token",
        )

        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.EMAIL_RECONCILIATION_PREFIX,
                "delivery failed",
                "delivery failed",
                report_runs.EMAIL_FAILED,
                7,
                report_runs.EMAIL_SENDING,
                "token",
            ),
        )

    def test_get_report_email_only_uses_active_signature_assignee(self) -> None:
        """Never fall back to an inactive or unvalidated historical signature name."""
        conn = FakeConnection(
            row=(
                7,
                "TAG1",
                "report.pdf",
                None,
                "recipient@example.gov",
                None,
                "Customer",
                42,
                "pdf",
                "Results",
                None,
                "",
                "",
                "",
                "",
                None,
                None,
                "token",
                "customer",
            )
        )
        email = report_runs.get_report_run_email(7, conn)
        self.assertIsNone(email.assignee_name)
        self.assertIn(
            "CASE WHEN assignees.active IS TRUE THEN assignees.name ELSE NULL END",
            conn.cursor_instance.query,
        )
        self.assertNotIn(
            "COALESCE(assignees.name, tracker.assignee)", conn.cursor_instance.query
        )
        self.assertIn(
            "COALESCE(replay.template_override, tracker.template)",
            conn.cursor_instance.query,
        )

    def test_report_email_start_belongs_to_source_execution(self) -> None:
        """A later stakeholder update cannot change the selected report's start."""
        conn = FakeConnection(
            row=(
                7,
                "TAG1",
                "report.pdf",
                None,
                "recipient@example.gov",
                None,
                "Customer",
                42,
                "pdf",
                "Results",
                None,
                "",
                "",
                "",
                "",
                int(datetime(2026, 9, 1, 12, tzinfo=timezone.utc).timestamp()),
                None,
                "token",
                "customer",
            )
        )
        email = report_runs.get_report_run_email(7, conn)
        self.assertEqual(
            email.last_scanned,
            int(datetime(2026, 9, 1, 12, tzinfo=timezone.utc).timestamp()),
        )
        self.assertIn(
            "EXTRACT(EPOCH FROM tracker.scan_started_at)::bigint",
            conn.cursor_instance.query,
        )
        self.assertNotIn("stakeholders.last_scanned", conn.cursor_instance.query)

    def test_list_report_runs_ready_for_email_excludes_failures(self) -> None:
        """Return completed report runs that are ready to email."""
        conn = FakeConnection(
            row=[
                (
                    7,
                    "TAG1",
                    "/WAS_REPORT_GENERATION/docs/report.pdf",
                    "password",
                    "distro@example.gov",
                    "tech@example.gov",
                    "poc@example.gov",
                    None,
                    "pdf",
                    "Results",
                    "Analyst",
                    "",
                    "",
                    "",
                    "",
                    1788307200,
                    1790985600,
                    "token",
                    "customer",
                )
            ]
        )

        report_run_emails = report_runs.list_report_runs_ready_for_email(
            conn=conn,
            limit=5,
            stakeholder_tag="TAG1",
            days_back=30,
        )

        self.assertEqual(report_run_emails[0].id, 7)
        self.assertIn(
            "EXTRACT(EPOCH FROM tracker.scan_started_at)::bigint",
            conn.cursor_instance.query,
        )
        self.assertNotIn("stakeholders.last_scanned", conn.cursor_instance.query)
        self.assertIn(
            "CASE WHEN assignees.active IS TRUE THEN assignees.name ELSE NULL END",
            conn.cursor_instance.query,
        )
        self.assertNotIn(
            "COALESCE(assignees.name, tracker.assignee)", conn.cursor_instance.query
        )
        self.assertIn("COALESCE(runs.email_status", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING],
                "TAG1",
                30,
                5,
            ),
        )
        self.assertIn("runs.stakeholder_tag = %s", conn.cursor_instance.query)
        self.assertIn(
            "tracker.data_pull_date >= CURRENT_DATE - (%s - 1)",
            conn.cursor_instance.query,
        )

    def test_list_report_runs_ready_for_email_can_retry_failures(self) -> None:
        """Allow failed email runs to be selected for retry."""
        conn = FakeConnection(row=[])

        report_runs.list_report_runs_ready_for_email(
            conn=conn,
            include_previous_failures=True,
        )

        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING, report_runs.EMAIL_FAILED],
            ),
        )

    def test_claim_report_run_email_updates_pending_row_atomically(
        self,
    ) -> None:
        """Claim one pending email before an external delivery side effect."""
        conn = FakeConnection(
            row=(
                7,
                "TAG1",
                "s3://reports/was_reports/report.pdf",
                42,
                "pdf",
                "password",
                "distro@example.gov",
                "tech@example.gov",
                "poc@example.gov",
                "Results",
                "Analyst",
                "",
                "",
                "",
                "",
                1788307200,
                1790985600,
                "token",
                "customer",
            )
        )

        claimed = report_runs.claim_report_run_email(
            report_run_id=7,
            conn=conn,
        )

        self.assertEqual(claimed.id, 7)
        self.assertIn(
            "EXTRACT(EPOCH FROM tracker.scan_started_at)::bigint",
            conn.cursor_instance.query,
        )
        self.assertNotIn("stakeholders.last_scanned", conn.cursor_instance.query)
        self.assertIn(
            "CASE WHEN assignees.active IS TRUE THEN assignees.name ELSE NULL END",
            conn.cursor_instance.query,
        )
        self.assertNotIn(
            "COALESCE(assignees.name, tracker.assignee)", conn.cursor_instance.query
        )
        self.assertIn(
            "COALESCE(replay.template_override, tracker.template)",
            conn.cursor_instance.query,
        )
        self.assertEqual(claimed.source_tracker_id, 42)
        self.assertTrue(conn.committed)
        self.assertIn("UPDATE was_report_runs", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.EMAIL_SENDING,
                conn.cursor_instance.parameters[1],
                7,
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING],
                report_runs.EMAIL_PENDING,
                report_runs.EMAIL_HELD,
                False,
                "customer",
            ),
        )

    @patch.object(report_runs, "uuid4", return_value="send-claim-token")
    def test_reconciled_held_claim_requires_one_time_scoped_token(
        self,
        uuid,
    ) -> None:
        """Only an exact one-time token and recipient scope can claim a hold."""
        blocked_connection = FakeConnection(row=None)

        report_runs.claim_report_run_email(
            report_run_id=7,
            conn=blocked_connection,
            allow_held=False,
        )

        blocked_parameters = blocked_connection.cursor_instance.parameters
        self.assertFalse(blocked_parameters[8])
        self.assertNotIn(report_runs.EMAIL_HELD, blocked_parameters[5])

        authorized_connection = FakeConnection(row=None)
        report_runs.claim_report_run_email(
            report_run_id=7,
            conn=authorized_connection,
            held_reconciliation_token="authorization-token",
            held_reconciliation_scope="stored-customer",
        )
        authorized_parameters = authorized_connection.cursor_instance.parameters
        self.assertEqual(authorized_parameters[3], "authorization-token")
        self.assertEqual(
            authorized_parameters[4],
            "Manual email reconciliation: retry authorized: "
            "token=authorization-token; scope=stored-customer",
        )
        self.assertEqual(authorized_parameters[6], "send-claim-token")
        uuid.assert_called()
        self.assertIn(
            "delivery_purpose = 'customer'",
            authorized_connection.cursor_instance.query,
        )
        self.assertIn(
            "runs.email_claim_token = %s",
            authorized_connection.cursor_instance.query,
        )
        self.assertIn(
            "tracker.report_sent_date IS NULL",
            authorized_connection.cursor_instance.query,
        )
        self.assertIn(
            "FOR UPDATE OF runs, tracker",
            authorized_connection.cursor_instance.query,
        )

    def test_initial_held_claim_rejects_rows_with_a_previous_error(self) -> None:
        """Initial analyst delivery cannot retry an uncertain held send."""
        conn = FakeConnection(row=None)

        report_runs.claim_report_run_email(
            report_run_id=7,
            conn=conn,
            allow_held=True,
            delivery_purpose="analyst",
        )

        self.assertIn(
            "NULLIF(BTRIM(email_error), '') IS NULL",
            conn.cursor_instance.query,
        )
        self.assertIn("delivery_purpose = 'analyst'", conn.cursor_instance.query)
        self.assertTrue(conn.cursor_instance.parameters[8])

    def test_reconciled_held_claim_requires_complete_valid_authority(self) -> None:
        """Reject missing or malformed one-time retry authority."""
        invalid_arguments = [
            {"held_reconciliation_token": "token"},
            {"held_reconciliation_scope": "stored-customer"},
            {
                "held_reconciliation_token": "token",
                "held_reconciliation_scope": "test-sha256:not-a-digest",
            },
        ]
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                conn = FakeConnection(row=None)
                with self.assertRaises(ValueError):
                    report_runs.claim_report_run_email(
                        report_run_id=7,
                        conn=conn,
                        **arguments,
                    )
                self.assertIsNone(conn.cursor_instance.query)

    def test_claim_report_run_email_rejects_existing_claim(self) -> None:
        """Return no email when another mailer already owns the run."""
        conn = FakeConnection(row=None)

        claimed = report_runs.claim_report_run_email(
            report_run_id=7,
            conn=conn,
        )

        self.assertIsNone(claimed)
        self.assertTrue(conn.committed)

    def test_list_report_run_errors_filters_recent_tag(self) -> None:
        """Return persisted report and delivery failures for operators."""
        timestamp = datetime(2026, 9, 1, tzinfo=timezone.utc)
        conn = FakeConnection(
            row=[
                (
                    7,
                    "TAG1",
                    report_runs.FAILED,
                    report_runs.EMAIL_PENDING,
                    timestamp,
                    timestamp,
                    "Report generation failed.",
                    None,
                )
            ]
        )

        errors = report_runs.list_report_run_errors(
            conn=conn,
            days_back=14,
            stakeholder_tag=" TAG1 ",
            limit=25,
        )

        self.assertEqual(errors[0].id, 7)
        self.assertEqual(errors[0].error_message, "Report generation failed.")
        self.assertEqual(conn.cursor_instance.parameters, (14, "TAG1", 25))
        self.assertIn("email_error", conn.cursor_instance.query)


if __name__ == "__main__":
    unittest.main()
