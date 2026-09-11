"""Tests for WAS report run data access."""

# Standard Python Libraries
from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock

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
            ),
        )
        self.assertIn("ON CONFLICT", conn.cursor_instance.query)

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
            ),
        )

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
            ),
        )
        self.assertIn("error_message = NULL", conn.cursor_instance.query)

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
                report_runs.EMAIL_SENT,
                7,
                report_runs.EMAIL_SENDING,
                "token",
            ),
        )
        self.assertIn("report_sent_date = CURRENT_DATE", conn.cursor_instance.query)

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
                "delivery failed",
                report_runs.EMAIL_FAILED,
                7,
                report_runs.EMAIL_SENDING,
                "token",
            ),
        )

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
        )

        self.assertEqual(report_run_emails[0].id, 7)
        self.assertIn("COALESCE(runs.email_status", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                report_runs.COMPLETED,
                report_runs.EMAIL_PENDING,
                [report_runs.EMAIL_PENDING],
                "TAG1",
                5,
            ),
        )
        self.assertIn("runs.stakeholder_tag = %s", conn.cursor_instance.query)

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
                "customer",
            ),
        )

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
