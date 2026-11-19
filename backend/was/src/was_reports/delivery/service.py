"""Authorized, audit-ready WAS delivery review and archived-report retry."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from email.headerregistry import Address
import hashlib
import os
from pathlib import PurePosixPath
from typing import Mapping

from botocore.exceptions import BotoCoreError, ClientError
from s3transfer.exceptions import RetriesExceededError

from was_mailer.email_reports import send_message
from was_mailer.message import build_report_email
from was_mailer.ses_client import create_ses_client
from was_reports.data import delivery_attempts
from was_reports.storage.s3_reports import (
    materialize_report,
    parse_s3_uri,
    validate_archived_pdf,
)
from was_reports.utils.env import require_env


def authenticate_operator() -> str:
    """Use the host UID passed to the CLI container without adding a login.

    Stakeholder grants are still checked by the data layer on every operation.
    A shared host UID has shared audit attribution and is not proof of an
    individual analyst's identity.
    """
    operator_uid = os.getuid()
    if operator_uid < 1:
        raise PermissionError("A non-root host account is required.")
    return "os-uid:{}".format(operator_uid)


def _validated_address(value: str) -> str:
    """Require one bounded customer mailbox rather than a recipient list."""
    if not isinstance(value, str):
        raise ValueError("One recipient address is required.")
    address_value = value.strip()
    if (
        not address_value
        or len(address_value) > 254
        or any(
            character.isspace() or ord(character) < 33
            for character in address_value
        )
        or "," in address_value
        or ";" in address_value
    ):
        raise ValueError("One valid recipient address is required.")
    try:
        address = Address(addr_spec=address_value)
    except ValueError as error:
        raise ValueError("One valid recipient address is required.") from error
    if (
        not address.username
        or not address.domain
        or "." not in address.domain
        or address.addr_spec != address_value
    ):
        raise ValueError("One valid recipient address is required.")
    return address_value


def _data_filters(filters: Mapping[str, object]) -> dict[str, object]:
    """Translate bounded CLI filters into the data layer's exact fields."""
    supported = {
        "stakeholder_tag",
        "recipient",
        "date",
        "date_from",
        "date_to",
        "bounce_type",
        "delivery_status",
        "report_id",
    }
    if set(filters) - supported:
        raise ValueError("Unsupported delivery failure filter.")
    converted = {
        field_name: filters[field_name]
        for field_name in (
            "stakeholder_tag",
            "recipient",
            "bounce_type",
            "delivery_status",
            "report_id",
        )
        if filters.get(field_name) not in (None, "")
    }
    if "recipient" in converted:
        converted["recipient"] = _validated_address(str(converted["recipient"]))
    if filters.get("date") and (filters.get("date_from") or filters.get("date_to")):
        raise ValueError("Use one date or a date range.")
    first_day = filters.get("date") or filters.get("date_from")
    last_day = filters.get("date") or filters.get("date_to")
    try:
        if first_day:
            converted["from_date"] = (
                first_day
                if isinstance(first_day, date)
                else date.fromisoformat(str(first_day))
            )
        if last_day:
            parsed_last_day = (
                last_day
                if isinstance(last_day, date)
                else date.fromisoformat(str(last_day))
            )
            converted["to_date"] = parsed_last_day + timedelta(days=1)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Dates must use YYYY-MM-DD format.") from error
    if (
        "from_date" in converted
        and "to_date" in converted
        and converted["from_date"] >= converted["to_date"]
    ):
        raise ValueError("The date range is reversed.")
    return converted


def list_failures(filters: Mapping[str, object], actor_id: str) -> list[dict]:
    """List only failures within an actor's grants and audit the sensitive read."""
    delivery_attempts.recover_stale_delivery_attempts(actor_id)
    failures = delivery_attempts.list_failures(_data_filters(filters), actor_id)
    delivery_attempts.record_access(actor_id, None, "list")
    return failures


def get_failure(attempt_id: int, actor_id: str) -> dict | None:
    """Return authorized failure history without an S3 location or password."""
    delivery_attempts.recover_stale_delivery_attempts(actor_id)
    failure = delivery_attempts.get_failure(attempt_id, actor_id)
    if failure is None:
        return None
    delivery_attempts.record_access(actor_id, attempt_id, "detail")
    visible = dict(failure)
    visible.pop("archived_report_s3_uri", None)
    return visible


def _report_scan_epoch(scan_started_at: datetime | None) -> int | None:
    """Translate the persisted scan timestamp for the existing mail template."""
    if scan_started_at is None:
        return None
    if scan_started_at.tzinfo is None:
        scan_started_at = scan_started_at.replace(tzinfo=timezone.utc)
    return int(scan_started_at.timestamp())


def _verified_report_reference(context: Mapping[str, object]) -> str:
    """Require the archived S3 PDF to belong to this completed report run."""
    if (
        context["report_generation_status"] != "completed"
        or context["delivery_purpose"] != "customer"
        or context["artifact_type"] != "pdf"
    ):
        raise ValueError("Delivery failure is not eligible for report retry.")
    report_reference = context.get("archived_report_s3_uri")
    if (
        not isinstance(report_reference, str)
        or report_reference != context.get("output_path")
    ):
        raise ValueError("The archived report reference is invalid.")
    bucket, key = parse_s3_uri(report_reference)
    key_parts = PurePosixPath(key).parts
    if (
        not bucket
        or len(key_parts) < 2
        or key_parts[-2] != str(context["report_run_id"])
    ):
        raise ValueError("The archived report does not match its report run.")
    return report_reference


def retry_failure(
    attempt_id: int,
    actor_id: str,
    idempotency_key: str,
    expected_failed_recipient: str,
    expected_recipient: str,
) -> dict:
    """Send one corrected recipient the existing archived report at most once.

    The attempt claim is committed before S3 access and SES invocation. Any
    uncertainty after the SES call begins is held for manual reconciliation.
    """
    if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
        raise ValueError("A bounded retry idempotency key is required.")
    delivery_attempts.recover_stale_delivery_attempts(actor_id)
    context = delivery_attempts.get_retry_context(attempt_id, actor_id)
    if context is None:
        raise LookupError("Delivery failure was not found.")
    failed_recipient = _validated_address(expected_failed_recipient)
    corrected_recipient = _validated_address(expected_recipient)
    report_reference = _verified_report_reference(context)
    scoped_idempotency_key = hashlib.sha256(
        "{}:{}:{}".format(
            attempt_id, failed_recipient.casefold(), idempotency_key
        ).encode("utf-8")
    ).hexdigest()
    claimed = delivery_attempts.claim_retry(
        attempt_id,
        actor_id,
        failed_recipient,
        corrected_recipient,
        scoped_idempotency_key,
    )
    retry_attempt_id = int(claimed["id"])
    if claimed["status"] != "pending":
        return {"id": retry_attempt_id, "status": claimed["status"]}
    try:
        archive_sha256 = context.get("archive_sha256")
        if not isinstance(archive_sha256, str) or len(archive_sha256) != 64:
            raise ValueError("The validated archive digest is unavailable.")
        with materialize_report(report_reference) as report_path:
            validate_archived_pdf(
                report_path,
                context["report_password"],
                expected_sha256=archive_sha256,
            )
            try:
                message = build_report_email(
                    source_email=require_env("WAS_EMAIL_SOURCE"),
                    recipients=[corrected_recipient],
                    stakeholder_tag=context["stakeholder_tag"],
                    report_path=report_path,
                    poc_name=context["was_report_poc"],
                    template=context["template"],
                    assignee_name=context["assignee_name"],
                    recent_nws=context["recent_nws"],
                    nws_summary=context["nws"],
                    remove_nws=context["remove_nws"],
                    qualys_error=context["qualys_error"],
                    last_scanned=_report_scan_epoch(context["scan_started_at"]),
                    next_scheduled=context["next_scheduled"],
                )
                if not any(
                    attachment.get_content_type() == "application/pdf"
                    for attachment in message.iter_attachments()
                ):
                    raise ValueError("The archived report is absent from the email.")
            except Exception as error:
                delivery_attempts.mark_pre_send_failure(
                    retry_attempt_id, "email_preparation_failed"
                )
                raise RuntimeError(
                    "The retry email could not be prepared; no email was sent."
                ) from error
    except (
        BotoCoreError,
        ClientError,
        RetriesExceededError,
        OSError,
        ValueError,
    ) as error:
        delivery_attempts.mark_pre_send_failure(
            retry_attempt_id, "archive_unavailable"
        )
        raise FileNotFoundError(
            "The archived report is missing, inaccessible, or invalid."
        ) from error
    try:
        ses_client = create_ses_client()
    except Exception as error:
        delivery_attempts.mark_pre_send_failure(
            retry_attempt_id, "ses_client_unavailable"
        )
        raise RuntimeError(
            "SES could not be prepared; no email was sent."
        ) from error
    try:
        delivery_attempts.mark_sending(retry_attempt_id)
    except ValueError:
        return {"id": retry_attempt_id, "status": "already_requested"}
    try:
        ses_message_id = send_message(ses_client, message)
    except Exception as error:
        delivery_attempts.mark_uncertain(retry_attempt_id, "ses_outcome_uncertain")
        raise RuntimeError(
            "SES delivery outcome is uncertain; manual review is required."
        ) from error
    try:
        delivery_attempts.mark_accepted(retry_attempt_id, ses_message_id)
    except Exception as error:
        raise RuntimeError(
            "SES accepted the retry, but recording its result failed; "
            "manual review is required."
        ) from error
    return {
        "id": retry_attempt_id,
        "status": "accepted",
        "ses_message_id": ses_message_id,
    }
