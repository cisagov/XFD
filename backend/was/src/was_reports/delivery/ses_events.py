"""Accept sanitized SES notifications from an exact SNS subscription."""

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime, timezone
from email.headerregistry import Address
import json
import os
from typing import Callable, Mapping
from uuid import UUID


EVENT_STATUSES = {
    "Send": "accepted",
    "Delivery": "delivered",
    "Bounce": "confirmed_failure",
    "Reject": "confirmed_failure",
    "Rendering Failure": "confirmed_failure",
    "DeliveryDelay": "held",
    "Complaint": "held",
}
IGNORED_EVENT_TYPES = frozenset({"Open", "Click", "Subscription"})
BOUNCE_TYPES = frozenset({"Permanent", "Transient", "Undetermined"})
BOUNCE_SUBTYPES = frozenset(
    {
        "General",
        "NoEmail",
        "Suppressed",
        "OnAccountSuppressionList",
        "Undetermined",
        "MailboxFull",
        "MessageTooLarge",
        "ContentRejected",
        "AttachmentRejected",
    }
)
MAX_SNS_MESSAGE_BYTES = 262144
MAX_SNS_RECORDS = 1000
MAX_EVENT_RECIPIENTS = 100


@dataclass(frozen=True)
class SanitizedSesEvent:
    """Keep only non-sensitive fields needed to classify and match an SES event."""

    sns_message_id: str
    ses_message_id: str
    event_type: str
    delivery_status: str
    occurred_at: datetime
    bounce_type: str | None = None
    bounce_subtype: str | None = None
    smtp_status_code: str | None = None
    affected_recipients: tuple[str, ...] = ()


def _required_mapping(value: object) -> Mapping[str, object]:
    """Return one JSON object or reject an unexpected event structure."""
    if not isinstance(value, dict):
        raise ValueError("SES notification must contain JSON objects.")
    return value


def _message_identifier(value: object, label: str) -> str:
    """Validate an opaque message identifier without exposing its raw value."""
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise ValueError("{} is missing or invalid.".format(label))
    if not all(33 <= ord(character) <= 126 for character in value):
        raise ValueError("{} is missing or invalid.".format(label))
    return value


def _sns_message_identifier(value: object) -> str:
    """Require the UUID that SNS assigns to a published notification."""
    message_identifier = _message_identifier(value, "SNS message ID")
    try:
        parsed_identifier = UUID(message_identifier)
    except ValueError as error:
        raise ValueError("SNS message ID is invalid.") from error
    if str(parsed_identifier) != message_identifier.lower():
        raise ValueError("SNS message ID is invalid.")
    return message_identifier


def _event_timestamp(value: object) -> datetime:
    """Parse an aware SES timestamp and normalize it to UTC."""
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("SES event timestamp is missing or invalid.")
    try:
        parsed_timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("SES event timestamp is invalid.") from error
    if parsed_timestamp.tzinfo is None:
        raise ValueError("SES event timestamp must include a time zone.")
    return parsed_timestamp.astimezone(timezone.utc)


def _smtp_status_code(bounce: Mapping[str, object]) -> str | None:
    """Retain only a common enhanced SMTP status, never recipient diagnostics."""
    bounced_recipients = bounce.get("bouncedRecipients")
    if not isinstance(bounced_recipients, list) or not bounced_recipients:
        return None
    status_codes: set[str] = set()
    for recipient in bounced_recipients:
        if not isinstance(recipient, dict):
            return None
        status_code = recipient.get("status")
        if not isinstance(status_code, str):
            return None
        components = status_code.split(".")
        if (
            len(components) != 3
            or len(components[0]) != 1
            or not 1 <= len(components[1]) <= 3
            or not 1 <= len(components[2]) <= 3
            or not all(
                component.isascii() and component.isdecimal()
                for component in components
            )
        ):
            return None
        status_codes.add(status_code)
    return next(iter(status_codes)) if len(status_codes) == 1 else None


def _recipient_address(value: object) -> str:
    """Validate one SES-reported destination before storing a recipient link."""
    if not isinstance(value, str) or not 3 <= len(value) <= 254:
        raise ValueError("SES event recipient is invalid.")
    if value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("SES event recipient is invalid.")
    try:
        parsed_address = Address(addr_spec=value)
    except (TypeError, ValueError) as error:
        raise ValueError("SES event recipient is invalid.") from error
    if not parsed_address.username or not parsed_address.domain:
        raise ValueError("SES event recipient is invalid.")
    return value.lower()


def _recipient_list(
    value: object, *, address_key: str | None = None
) -> tuple[str, ...]:
    """Return a bounded, deduplicated set of actual event destinations."""
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > MAX_EVENT_RECIPIENTS:
        raise ValueError("SES event recipients are missing or too numerous.")
    recipients: set[str] = set()
    for entry in value:
        address = _required_mapping(entry).get(address_key) if address_key else entry
        recipients.add(_recipient_address(address))
    return tuple(sorted(recipients))


def parse_sns_record(
    record: Mapping[str, object], expected_topic_arn: str
) -> SanitizedSesEvent | None:
    """Validate an SNS envelope and reduce its SES payload to safe fields.

    The Lambda subscription and resource policy must also restrict invocation to
    the same topic. This check rejects events routed from any other SNS topic.
    """
    if not expected_topic_arn or not expected_topic_arn.startswith("arn:"):
        raise ValueError("An exact SES SNS topic ARN is required.")
    if record.get("EventSource") != "aws:sns":
        raise ValueError("SES event did not originate from SNS.")
    sns_envelope = _required_mapping(record.get("Sns"))
    if sns_envelope.get("TopicArn") != expected_topic_arn:
        raise ValueError("SES event arrived from an unexpected SNS topic.")
    sns_message_id = _sns_message_identifier(sns_envelope.get("MessageId"))
    raw_message = sns_envelope.get("Message")
    if (
        not isinstance(raw_message, str)
        or len(raw_message.encode("utf-8")) > MAX_SNS_MESSAGE_BYTES
    ):
        raise ValueError("SES notification is missing or too large.")
    try:
        notification = _required_mapping(json.loads(raw_message))
    except json.JSONDecodeError as error:
        raise ValueError("SES notification is not valid JSON.") from error

    event_type = notification.get("eventType", notification.get("notificationType"))
    if not isinstance(event_type, str):
        raise ValueError("SES notification has an unsupported event type.")
    if event_type in IGNORED_EVENT_TYPES:
        return None
    if event_type not in EVENT_STATUSES:
        raise ValueError("SES notification has an unsupported event type.")
    mail = _required_mapping(notification.get("mail"))
    ses_message_id = _message_identifier(mail.get("messageId"), "SES message ID")
    event_details_key = {
        "Send": "send",
        "Delivery": "delivery",
        "Bounce": "bounce",
        "Reject": "reject",
        "Rendering Failure": "failure",
        "DeliveryDelay": "deliveryDelay",
        "Complaint": "complaint",
    }[event_type]
    event_details = notification.get(event_details_key)
    if event_type == "Bounce" and not isinstance(event_details, dict):
        raise ValueError("SES bounce notification is incomplete.")
    if event_details is not None:
        event_details = _required_mapping(event_details)
    timestamp_value = (
        event_details.get("timestamp") if event_details is not None else None
    ) or mail.get("timestamp")
    occurred_at = _event_timestamp(timestamp_value)

    bounce_type = None
    bounce_subtype = None
    smtp_status_code = None
    affected_recipients: tuple[str, ...] = ()
    if event_type == "Bounce":
        bounce = _required_mapping(event_details)
        candidate_type = bounce.get("bounceType")
        if not isinstance(candidate_type, str) or candidate_type not in BOUNCE_TYPES:
            raise ValueError("SES bounce type is invalid.")
        bounce_type = candidate_type
        candidate_subtype = bounce.get("bounceSubType")
        if isinstance(candidate_subtype, str) and candidate_subtype in BOUNCE_SUBTYPES:
            bounce_subtype = candidate_subtype
        smtp_status_code = _smtp_status_code(bounce)
        affected_recipients = _recipient_list(
            bounce.get("bouncedRecipients"), address_key="emailAddress"
        )
    elif event_type == "Delivery":
        delivery = _required_mapping(event_details)
        affected_recipients = _recipient_list(delivery.get("recipients"))
    elif event_type == "DeliveryDelay":
        delay = _required_mapping(event_details)
        affected_recipients = _recipient_list(
            delay.get("delayedRecipients"), address_key="emailAddress"
        )
    elif event_type == "Complaint":
        complaint = _required_mapping(event_details)
        affected_recipients = _recipient_list(
            complaint.get("complainedRecipients"), address_key="emailAddress"
        )
    else:
        affected_recipients = _recipient_list(mail.get("destination"))

    delivery_status = EVENT_STATUSES[event_type]
    if event_type == "Bounce" and bounce_type != "Permanent":
        delivery_status = "held"
    if not affected_recipients and delivery_status != "accepted":
        delivery_status = "held"

    return SanitizedSesEvent(
        sns_message_id=sns_message_id,
        ses_message_id=ses_message_id,
        event_type=event_type,
        delivery_status=delivery_status,
        occurred_at=occurred_at,
        bounce_type=bounce_type,
        bounce_subtype=bounce_subtype,
        smtp_status_code=smtp_status_code,
        affected_recipients=affected_recipients,
    )


def ingest_sns_event(
    lambda_event: Mapping[str, object],
    expected_topic_arn: str,
    persist_event: Callable[[SanitizedSesEvent], bool],
) -> int:
    """Persist each sanitized SNS record, allowing redelivery after a failure."""
    records = lambda_event.get("Records")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_SNS_RECORDS:
        raise ValueError("SNS event must contain a bounded list of records.")
    recorded_count = 0
    for record in records:
        parsed_event = parse_sns_record(_required_mapping(record), expected_topic_arn)
        if parsed_event is not None and persist_event(parsed_event):
            recorded_count += 1
    return recorded_count


def handler(lambda_event: Mapping[str, object], context: object) -> dict[str, int]:
    """Handle AWS SNS delivery using the configured exact topic and DB role."""
    del context
    expected_topic_arn = os.environ.get("WAS_SES_EVENTS_TOPIC_ARN", "")
    if not expected_topic_arn:
        raise ValueError("WAS_SES_EVENTS_TOPIC_ARN is required.")
    from was_reports.data.delivery_attempts import record_ses_event

    recorded_count = ingest_sns_event(
        lambda_event=lambda_event,
        expected_topic_arn=expected_topic_arn,
        persist_event=record_ses_event,
    )
    return {"recorded_events": recorded_count}
