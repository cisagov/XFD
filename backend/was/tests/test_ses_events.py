"""Verify SES notification sanitization and SNS trust checks."""

# Standard Python Libraries
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.delivery import ses_events

TOPIC_ARN = "arn:aws:sns:us-east-1:123456789012:was-ses-events"
SNS_MESSAGE_ID = "76d9b097-bc2a-409a-9c88-294788248e17"


def sns_record(notification: dict, topic_arn: str = TOPIC_ARN) -> dict:
    """Build an SNS Lambda record containing one SES notification."""
    return {
        "EventSource": "aws:sns",
        "Sns": {
            "TopicArn": topic_arn,
            "MessageId": SNS_MESSAGE_ID,
            "Message": json.dumps(notification),
        },
    }


def bounce_notification() -> dict:
    """Return a representative multi-recipient SES bounce notification."""
    return {
        "eventType": "Bounce",
        "mail": {
            "messageId": "ses-message-123",
            "timestamp": "2026-11-18T14:00:00.000Z",
            "destination": ["first@example.gov", "second@example.gov"],
        },
        "bounce": {
            "timestamp": "2026-11-18T14:01:00.000Z",
            "bounceType": "Permanent",
            "bounceSubType": "General",
            "bouncedRecipients": [
                {
                    "emailAddress": "first@example.gov",
                    "status": "5.1.1",
                    "diagnosticCode": "smtp; 550 address first@example.gov failed",
                }
            ],
        },
    }


class SesEventTests(unittest.TestCase):
    """Require trusted, recipient-specific, sanitized SES event evidence."""

    def test_bounce_retains_only_affected_recipient_and_safe_code(self) -> None:
        """Do not treat every original destination as a bounced recipient."""
        parsed = ses_events.parse_sns_record(
            sns_record(bounce_notification()), TOPIC_ARN
        )

        self.assertEqual(parsed.delivery_status, "confirmed_failure")
        self.assertEqual(parsed.affected_recipients, ("first@example.gov",))
        self.assertEqual(parsed.smtp_status_code, "5.1.1")
        self.assertEqual(parsed.bounce_type, "Permanent")
        self.assertEqual(
            parsed.occurred_at,
            datetime(2026, 11, 18, 14, 1, tzinfo=timezone.utc),
        )
        self.assertNotIn("diagnostic", repr(parsed).lower())

    def test_wrong_topic_and_source_are_rejected(self) -> None:
        """Reject forged envelopes before parsing or persisting their contents."""
        record = sns_record(
            bounce_notification(),
            topic_arn="arn:aws:sns:us-east-1:123456789012:other",
        )
        with self.assertRaises(ValueError):
            ses_events.parse_sns_record(record, TOPIC_ARN)

        record = sns_record(bounce_notification())
        record["EventSource"] = "aws:sqs"
        with self.assertRaises(ValueError):
            ses_events.parse_sns_record(record, TOPIC_ARN)

    def test_missing_affected_recipient_is_held(self) -> None:
        """Prevent an ambiguous bounce from authorizing any recipient retry."""
        notification = bounce_notification()
        notification["bounce"]["bouncedRecipients"] = []
        parsed = ses_events.parse_sns_record(sns_record(notification), TOPIC_ARN)

        self.assertEqual(parsed.delivery_status, "held")
        self.assertEqual(parsed.affected_recipients, ())

    def test_transient_bounce_does_not_confirm_nondelivery(self) -> None:
        """Keep soft bounces in manual review when inbox delivery is uncertain."""
        notification = bounce_notification()
        notification["bounce"]["bounceType"] = "Transient"
        parsed = ses_events.parse_sns_record(sns_record(notification), TOPIC_ARN)

        self.assertEqual(parsed.delivery_status, "held")
        self.assertEqual(parsed.affected_recipients, ("first@example.gov",))

    def test_delivery_uses_delivery_recipients(self) -> None:
        """Distinguish delivered destinations from the mail's entire address list."""
        notification = bounce_notification()
        notification["eventType"] = "Delivery"
        notification.pop("bounce")
        notification["delivery"] = {
            "timestamp": "2026-11-18T14:02:00.000Z",
            "recipients": ["second@example.gov"],
        }
        parsed = ses_events.parse_sns_record(sns_record(notification), TOPIC_ARN)

        self.assertEqual(parsed.delivery_status, "delivered")
        self.assertEqual(parsed.affected_recipients, ("second@example.gov",))

    def test_unrelated_event_is_ignored_without_retrying_sns_batch(self) -> None:
        """Skip open tracking events that carry no delivery outcome."""
        notification = bounce_notification()
        notification["eventType"] = "Open"
        notification.pop("bounce")
        notification["open"] = {"timestamp": "2026-11-18T14:03:00.000Z"}
        persist_event = Mock()

        count = ses_events.ingest_sns_event(
            {"Records": [sns_record(notification)]}, TOPIC_ARN, persist_event
        )

        self.assertEqual(count, 0)
        persist_event.assert_not_called()

    def test_invalid_address_is_rejected_without_echo(self) -> None:
        """Never persist or expose malformed SES recipient data."""
        notification = bounce_notification()
        notification["bounce"]["bouncedRecipients"][0][
            "emailAddress"
        ] = "victim@example.gov\r\nBCC: attacker@example.gov"
        with self.assertRaises(ValueError) as error_context:
            ses_events.parse_sns_record(sns_record(notification), TOPIC_ARN)
        self.assertIn("SES event recipient is invalid", str(error_context.exception))
        self.assertNotIn("victim", str(error_context.exception))

    def test_ingestion_persists_sanitized_record_once_per_input(self) -> None:
        """Hand only validated event objects to the idempotent repository API."""
        persist_event = Mock(return_value=True)
        result = ses_events.ingest_sns_event(
            {"Records": [sns_record(bounce_notification())]},
            TOPIC_ARN,
            persist_event,
        )

        self.assertEqual(result, 1)
        persisted = persist_event.call_args.args[0]
        self.assertEqual(persisted.sns_message_id, SNS_MESSAGE_ID)
        self.assertEqual(persisted.ses_message_id, "ses-message-123")
        self.assertEqual(persisted.affected_recipients, ("first@example.gov",))

    def test_handler_requires_exact_topic_configuration(self) -> None:
        """Fail closed when the expected SNS topic is not configured."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                ses_events.handler(
                    {"Records": [sns_record(bounce_notification())]}, None
                )

    def test_bad_timestamp_is_rejected(self) -> None:
        """Never create false event chronology from a timestamp without a zone."""
        notification = bounce_notification()
        notification["bounce"]["timestamp"] = "2026-11-18T14:01:00"
        with self.assertRaises(ValueError):
            ses_events.parse_sns_record(sns_record(notification), TOPIC_ARN)


if __name__ == "__main__":
    unittest.main()
