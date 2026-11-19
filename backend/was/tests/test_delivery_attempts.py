"""Behavioral tests for scoped WAS delivery-attempt persistence."""

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from was_reports.data import delivery_attempts


ACTOR_ID = "os-uid:1001"


@contextmanager
def fake_connection_context(database_connection):
    """Provide the same context boundary as a managed database connection."""
    yield database_connection


class DeliveryAttemptTests(unittest.TestCase):
    """Exercise authorization and duplicate prevention without a live database."""

    def setUp(self) -> None:
        """Provide a database cursor that can return controlled query results."""
        self.database_connection = MagicMock()
        cursor_context = self.database_connection.cursor.return_value
        self.cursor = cursor_context.__enter__.return_value
        connection_patch = patch.object(
            delivery_attempts,
            "_database_connection",
            return_value=fake_connection_context(self.database_connection),
        )
        connection_patch.start()
        self.addCleanup(connection_patch.stop)

    def test_list_filters_stay_bound_and_scoped_to_user(self) -> None:
        """Keep recipient input out of SQL and join the actor's stakeholder grants."""
        self.cursor.fetchall.return_value = []
        delivery_attempts.list_failures(
            {"recipient": "person@example.gov", "report_id": 321}, ACTOR_ID
        )
        query, parameters = self.cursor.execute.call_args.args
        self.assertIn("was_delivery_stakeholder_grants", query)
        self.assertIn("grants.principal_key = %s", query)
        self.assertIn("outcome.affected_recipients", query)
        self.assertNotIn("person@example.gov", query)
        self.assertEqual(parameters[0], ACTOR_ID)
        self.assertEqual(parameters.count("person@example.gov"), 2)

    def test_detail_of_unknown_or_ungranted_attempt_stops_before_history(self) -> None:
        """Return the same absence for unknown and unauthorized records."""
        self.cursor.fetchone.return_value = None
        result = delivery_attempts.get_failure(900, ACTOR_ID)
        self.assertIsNone(result)
        self.assertEqual(self.cursor.execute.call_count, 1)
        query = self.cursor.execute.call_args.args[0]
        self.assertIn("was_delivery_stakeholder_grants", query)

    def test_unverified_actor_name_is_rejected_before_database_read(self) -> None:
        """Only caller-bound host UID principals can enter scoped queries."""
        with self.assertRaises(ValueError):
            delivery_attempts.get_failure(900, "analyst")
        self.cursor.execute.assert_not_called()

    def test_duplicate_retry_returns_existing_attempt_without_insert(self) -> None:
        """A repeated request reuses its child and never creates another send."""
        self.cursor.fetchone.side_effect = [
            {"id": 900},
            {
                "id": 901,
                "failed_recipient": "old@example.gov",
                "recipient_addresses": ["new@example.gov"],
                "status": "accepted",
                "requested_by_principal_key": ACTOR_ID,
            },
        ]
        result = delivery_attempts.claim_retry(
            900, ACTOR_ID, "old@example.gov", "new@example.gov", "same-request"
        )
        self.assertEqual(result["id"], 901)
        self.assertEqual(self.cursor.execute.call_count, 2)
        self.database_connection.commit.assert_called_once()

    def test_expired_failure_cannot_be_claimed_again(self) -> None:
        """Close retry eligibility before expired child rows are removed."""
        self.cursor.fetchone.return_value = None

        with self.assertRaises(LookupError):
            delivery_attempts.claim_retry(
                900, ACTOR_ID, "old@example.gov", "old@example.gov", "late-key"
            )

        query, parameters = self.cursor.execute.call_args.args
        self.assertIn("attempts.created_at > NOW()", query)
        self.assertEqual(parameters[-1], 14)
        self.assertEqual(self.cursor.execute.call_count, 1)

    def test_sending_transition_checks_retention_age(self) -> None:
        """An old pending attempt cannot begin a new SES request."""
        self.cursor.fetchone.return_value = None

        with self.assertRaises(ValueError):
            delivery_attempts.mark_sending(901)

        query, parameters = self.cursor.execute.call_args.args
        self.assertIn("created_at > NOW()", query)
        self.assertEqual(parameters[-1], 14)
        self.database_connection.rollback.assert_called_once()

    def test_new_request_cannot_duplicate_an_active_retry(self) -> None:
        """A new key cannot resend while an earlier attempt may have sent."""
        self.cursor.fetchone.side_effect = [{"id": 900}, None, {"id": 901}]
        with self.assertRaises(ValueError) as duplicate_request:
            delivery_attempts.claim_retry(
                900, ACTOR_ID, "old@example.gov", "new@example.gov", "new-request"
            )
        self.assertIn("active retry", str(duplicate_request.exception))
        self.database_connection.rollback.assert_called_once()

    def test_uncertain_outcome_does_not_create_retry(self) -> None:
        """Keep held SES outcomes out of the automatic retry path."""
        self.cursor.fetchone.side_effect = [
            {
                "id": 900,
                "status": "held",
                "report_generation_status": "completed",
                "delivery_purpose": "customer",
                "artifact_type": "pdf",
            },
            None,
            None,
        ]
        with self.assertRaises(ValueError) as held_delivery:
            delivery_attempts.claim_retry(
                900, ACTOR_ID, "old@example.gov", "new@example.gov", "request-key"
            )
        self.assertIn("not eligible", str(held_delivery.exception))
        self.assertEqual(self.cursor.execute.call_count, 3)

    def test_conflicting_recipient_event_blocks_retry(self) -> None:
        """Do not resend when the same recipient has a held or delivered event."""
        self.cursor.fetchone.side_effect = [
            self._eligible_parent(),
            None,
            None,
            {"confirmed_failure_at": datetime(2026, 11, 18, tzinfo=timezone.utc)},
            (1,),
        ]
        with self.assertRaises(ValueError) as conflict:
            delivery_attempts.claim_retry(
                900, ACTOR_ID, "old@example.gov", "new@example.gov", "request-key"
            )
        self.assertIn("manual review", str(conflict.exception))
        self.assertEqual(self.cursor.execute.call_count, 5)

    @staticmethod
    def _eligible_parent() -> dict:
        """Provide one granted customer report with a validated archive."""
        return {
            "id": 900,
            "report_run_id": 321,
            "recipient_addresses": ["old@example.gov"],
            "archived_report_s3_uri": "s3://reports/was_reports/321.pdf",
            "archive_sha256": "a" * 64,
            "status": "confirmed_failure",
            "output_path": "s3://reports/was_reports/321.pdf",
            "report_generation_status": "completed",
            "delivery_purpose": "customer",
            "artifact_type": "pdf",
        }

    def test_later_confirmed_bounce_allows_retry_after_earlier_delay(self) -> None:
        """Claim a retry when no held event follows the confirmed failure."""
        confirmed_at = datetime(2026, 11, 18, tzinfo=timezone.utc)
        self.cursor.fetchone.side_effect = [
            self._eligible_parent(),
            None,
            None,
            {"confirmed_failure_at": confirmed_at},
            None,
            {
                "id": 901,
                "status": "pending",
                "recipient_addresses": ["new@example.gov"],
            },
        ]
        claimed = delivery_attempts.claim_retry(
            900, ACTOR_ID, "old@example.gov", "new@example.gov", "request-key"
        )
        self.assertEqual(claimed["id"], 901)
        conflict_query = self.cursor.execute.call_args_list[4]
        self.assertIn("occurred_at >= %s", conflict_query.args[0])
        self.assertEqual(conflict_query.args[1][-1], confirmed_at)
        insert_query = self.cursor.execute.call_args_list[5]
        self.assertIn("archive_sha256", insert_query.args[0])
        self.assertIn("a" * 64, insert_query.args[1])
        correction_audit = self.cursor.execute.call_args_list[6]
        retry_audit = self.cursor.execute.call_args_list[7]
        self.assertIn("'correction'", correction_audit.args[0])
        self.assertIn("'retry_requested'", retry_audit.args[0])
        self.database_connection.commit.assert_called_once()

    def test_same_address_retry_does_not_record_a_correction(self) -> None:
        """Audit the resend while preserving the original recipient unchanged."""
        self.cursor.fetchone.side_effect = [
            self._eligible_parent(),
            None,
            None,
            {"confirmed_failure_at": datetime(2026, 11, 18, tzinfo=timezone.utc)},
            None,
            {
                "id": 902,
                "status": "pending",
                "recipient_addresses": ["old@example.gov"],
            },
        ]

        claimed = delivery_attempts.claim_retry(
            900, ACTOR_ID, "old@example.gov", "old@example.gov", "same-address"
        )

        self.assertEqual(claimed["recipient_addresses"], ["old@example.gov"])
        executed_queries = [
            call.args[0] for call in self.cursor.execute.call_args_list
        ]
        self.assertEqual(len(executed_queries), 7)
        self.assertFalse(any("'correction'" in query for query in executed_queries))
        self.assertIn("'retry_requested'", executed_queries[-1])
        self.database_connection.commit.assert_called_once()

    def test_invalid_correction_is_rejected_before_database_write(self) -> None:
        """Refuse a malformed corrected address at the persistence boundary."""
        with self.assertRaises(ValueError):
            delivery_attempts.claim_retry(
                900, ACTOR_ID, "old@example.gov", "not-an-email", "request-key"
            )
        self.cursor.execute.assert_not_called()

    def test_stale_retry_recovery_is_scoped_and_audited(self) -> None:
        """Expire only granted pending or sending retry children without resending."""
        self.cursor.rowcount = 2
        recovered = delivery_attempts.recover_stale_delivery_attempts(ACTOR_ID)
        query, parameters = self.cursor.execute.call_args.args
        self.assertEqual(recovered, 2)
        self.assertIn("was_delivery_stakeholder_grants", query)
        self.assertIn("'failed_pre_send' ELSE 'held'", query)
        self.assertIn("'retry_result'", query)
        self.assertEqual(parameters[0], ACTOR_ID)
        self.database_connection.commit.assert_called_once()

    def test_ses_event_dedupes_by_notification_message_id(self) -> None:
        """A repeated SNS notification cannot create duplicate event history."""
        self.cursor.fetchone.return_value = None
        event = SimpleNamespace(
            sns_message_id="sns-id",
            ses_message_id="ses-id",
            event_type="Bounce",
            delivery_status="confirmed_failure",
            affected_recipients=("old@example.gov",),
            occurred_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
            bounce_type="Permanent",
            bounce_subtype="General",
            smtp_status_code="5.1.1",
        )
        self.assertFalse(delivery_attempts.record_ses_event(event))
        self.assertEqual(self.cursor.execute.call_count, 2)
        query = self.cursor.execute.call_args.args[0]
        self.assertIn("ON CONFLICT (sns_message_id) DO NOTHING", query)

    def test_old_ses_notification_does_not_restore_expired_address(self) -> None:
        """Redact late notification addresses before database insertion."""
        self.cursor.fetchone.return_value = (100, None)
        event = SimpleNamespace(
            sns_message_id="late-sns-id",
            ses_message_id="old-ses-id",
            event_type="Bounce",
            delivery_status="confirmed_failure",
            affected_recipients=("old@example.gov",),
            occurred_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            bounce_type="Permanent",
            bounce_subtype="General",
            smtp_status_code="5.1.1",
        )

        self.assertTrue(delivery_attempts.record_ses_event(event))

        insert_call = self.cursor.execute.call_args_list[1]
        self.assertEqual(insert_call.args[1][4], [])
        self.assertNotIn("old@example.gov", insert_call.args[1])

    def test_accepted_send_attaches_earlier_recipient_scoped_event(self) -> None:
        """Correlate an event that arrived before the SES message ID was stored."""
        self.cursor.fetchone.return_value = (900,)
        delivery_attempts.mark_accepted(900, "ses-id")
        executed_queries = [
            call.args[0] for call in self.cursor.execute.call_args_list
        ]
        self.assertEqual(len(executed_queries), 4)
        self.assertIn(
            "cardinality(events.affected_recipients) = 0",
            executed_queries[2],
        )
        self.assertIn("was_ses_delivery_events", executed_queries[3])
        self.database_connection.commit.assert_called_once()

    def test_recipient_free_send_event_links_by_ses_message_id(self) -> None:
        """Keep a Send event with no recipient list in its attempt history."""
        self.cursor.fetchone.return_value = (100, 900)
        event = SimpleNamespace(
            sns_message_id="sns-send-id",
            ses_message_id="ses-id",
            event_type="Send",
            delivery_status="accepted",
            affected_recipients=(),
            occurred_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
            bounce_type=None,
            bounce_subtype=None,
            smtp_status_code=None,
        )

        self.assertTrue(delivery_attempts.record_ses_event(event))
        self.assertEqual(self.cursor.execute.call_count, 2)
        insert_query, parameters = self.cursor.execute.call_args.args
        self.assertIn("%s = 'accepted' AND cardinality(%s::text[]) = 0", insert_query)
        self.assertIn("accepted", parameters)
        self.assertEqual(parameters[-3:], ([], [], []))
        self.database_connection.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
