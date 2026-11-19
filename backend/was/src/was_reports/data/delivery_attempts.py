"""Persist scoped WAS delivery attempts, SES outcomes, and minimal audit events."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from email.headerregistry import Address
from typing import Iterator, Mapping, Protocol

from psycopg2.extras import RealDictCursor

from was_reports.utils.database import close, connect
from was_reports.utils.logging_config import positive_integer


FAILURE_STATUSES = frozenset({"confirmed_failure", "held", "failed_pre_send"})
EVENT_STATUSES = frozenset({"accepted", "delivered", "confirmed_failure", "held"})
MAX_FILTER_RESULTS = 100
DELIVERY_RETENTION_DAYS = 14


class SesEvent(Protocol):
    """Fields supplied by the sanitized SES notification parser."""

    sns_message_id: str
    ses_message_id: str
    event_type: str
    delivery_status: str
    occurred_at: datetime
    affected_recipients: tuple[str, ...]
    bounce_type: str | None
    bounce_subtype: str | None
    smtp_status_code: str | None


@contextmanager
def _database_connection() -> Iterator:
    """Own a short lived WAS database connection for one operation."""
    database_connection = connect()
    try:
        yield database_connection
    finally:
        close(database_connection)


def _validated_principal_key(actor_id: str) -> str:
    """Require the bounded host UID principal issued by the CLI boundary."""
    if not isinstance(actor_id, str) or len(actor_id) > 128:
        raise ValueError("A verified actor principal is required.")
    if actor_id.startswith("os-uid:"):
        numeric_user_id = actor_id[7:]
        if (
            not numeric_user_id
            or not numeric_user_id.isascii()
            or not numeric_user_id.isdigit()
            or numeric_user_id != str(int(numeric_user_id))
        ):
            raise ValueError("A verified actor principal is required.")
        return actor_id
    raise ValueError("A verified actor principal is required.")


def _validated_recipient(recipient: str) -> str:
    """Reject empty or control-bearing addresses before database persistence."""
    normalized = recipient.strip()
    if not normalized or len(normalized) > 254:
        raise ValueError(
            "A recipient address is required and must be at most 254 characters."
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError("Recipient address contains a control character.")
    if any(character.isspace() for character in normalized):
        raise ValueError("Recipient address is invalid.")
    if "," in normalized or ";" in normalized:
        raise ValueError("Recipient address is invalid.")
    try:
        parsed_address = Address(addr_spec=normalized)
    except ValueError as error:
        raise ValueError("Recipient address is invalid.") from error
    if (
        not parsed_address.username
        or not parsed_address.domain
        or "." not in parsed_address.domain
        or parsed_address.addr_spec != normalized
    ):
        raise ValueError("Recipient address is invalid.")
    return normalized.lower()


def _row_dictionary(row: Mapping | None) -> dict | None:
    """Return an ordinary dictionary without leaking cursor internals."""
    return None if row is None else dict(row)


def list_failures(
    filters: Mapping[str, object],
    actor_id: str,
    *,
    limit: int = MAX_FILTER_RESULTS,
    offset: int = 0,
) -> list[dict]:
    """List only failure attempts for stakeholder tags granted to the actor."""
    if limit < 1 or limit > MAX_FILTER_RESULTS or offset < 0:
        raise ValueError("Invalid delivery failure pagination.")
    conditions = [
        "attempts.status IN ('confirmed_failure', 'held', 'failed_pre_send')",
        "(attempts.original_failed_attempt_id IS NULL OR "
        "attempts.created_at > NOW() - INTERVAL '14 days')",
    ]
    parameters: list[object] = [_validated_principal_key(actor_id)]
    filter_columns = {
        "stakeholder_tag": "runs.stakeholder_tag = %s",
        "recipient": (
            "attempts.created_at > NOW() - INTERVAL '14 days' "
            "AND %s = ANY(attempts.recipient_addresses) AND ("
            "attempts.status = 'failed_pre_send' OR "
            "NOT EXISTS (SELECT 1 FROM was_ses_delivery_events AS outcome "
            "WHERE outcome.delivery_attempt_id = attempts.id "
            "AND outcome.delivery_status IN ('confirmed_failure', 'held')) OR "
            "EXISTS (SELECT 1 FROM was_ses_delivery_events AS outcome "
            "WHERE outcome.delivery_attempt_id = attempts.id "
            "AND outcome.delivery_status IN ('confirmed_failure', 'held') "
            "AND %s = ANY(outcome.affected_recipients)))"
        ),
        "delivery_status": "attempts.status = %s",
        "report_id": "attempts.report_run_id = %s",
        "from_date": (
            "COALESCE(attempts.confirmed_failed_at, attempts.updated_at) >= %s"
        ),
        "to_date": "COALESCE(attempts.confirmed_failed_at, attempts.updated_at) < %s",
    }
    for filter_name, condition in filter_columns.items():
        filter_value = filters.get(filter_name)
        if filter_value is None or filter_value == "":
            continue
        if filter_name == "delivery_status" and filter_value not in FAILURE_STATUSES:
            raise ValueError("Unknown delivery failure status.")
        if filter_name == "recipient":
            filter_value = _validated_recipient(str(filter_value))
            conditions.append(condition)
            parameters.extend((filter_value, filter_value))
            continue
        if filter_name == "report_id":
            filter_value = int(filter_value)
            if filter_value < 1:
                raise ValueError("Report identifier must be positive.")
        if filter_name in {"from_date", "to_date"} and not isinstance(
            filter_value, (date, datetime)
        ):
            raise ValueError("Date filters require date values.")
        conditions.append(condition)
        parameters.append(filter_value)
    bounce_type = filters.get("bounce_type")
    if bounce_type:
        if not isinstance(bounce_type, str) or len(bounce_type) > 64:
            raise ValueError("Invalid bounce type.")
        conditions.append(
            "EXISTS (SELECT 1 FROM was_ses_delivery_events AS events "
            "WHERE events.delivery_attempt_id = attempts.id "
            "AND events.bounce_type = %s)"
        )
        parameters.append(bounce_type)
    unsupported = set(filters) - set(filter_columns) - {"bounce_type"}
    if unsupported:
        raise ValueError("Unsupported delivery failure filter.")
    query = """
        SELECT attempts.id, attempts.report_run_id, runs.stakeholder_tag,
               CASE WHEN attempts.created_at > NOW() - INTERVAL '14 days'
                    THEN attempts.recipient_addresses ELSE ARRAY[]::text[]
               END AS recipient_addresses, attempts.status,
               attempts.failure_classification, attempts.created_at,
               COALESCE(attempts.confirmed_failed_at, attempts.updated_at)
                 AS failure_occurred_at,
               attempts.confirmed_failed_at, attempts.ses_message_id,
               (
                   SELECT events.bounce_type
                   FROM was_ses_delivery_events AS events
                   WHERE events.delivery_attempt_id = attempts.id
                     AND events.bounce_type IS NOT NULL
                   ORDER BY events.occurred_at DESC, events.id DESC
                   LIMIT 1
               ) AS bounce_type
        FROM was_delivery_attempts AS attempts
        JOIN was_report_runs AS runs ON runs.id = attempts.report_run_id
        JOIN was_delivery_stakeholder_grants AS grants
          ON grants.stakeholder_tag = runs.stakeholder_tag
         AND grants.principal_key = %s
        WHERE {}
        ORDER BY attempts.created_at DESC, attempts.id DESC
        LIMIT %s OFFSET %s
    """.format(" AND ".join(conditions))
    parameters.extend([limit, offset])
    with _database_connection() as database_connection:
        with database_connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, tuple(parameters))
            return [dict(row) for row in cursor.fetchall()]


def get_failure(attempt_id: int, actor_id: str) -> dict | None:
    """Return a scoped failure with report, recipient, event, and retry history."""
    with _database_connection() as database_connection:
        with database_connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT attempts.id, attempts.report_run_id, runs.stakeholder_tag,
                       runs.status AS report_generation_status,
                       runs.delivery_purpose,
                       attempts.original_failed_attempt_id,
                       attempts.failed_recipient,
                       CASE WHEN attempts.created_at > NOW() - INTERVAL '14 days'
                            THEN attempts.recipient_addresses ELSE ARRAY[]::text[]
                       END AS recipient_addresses,
                       attempts.archived_report_s3_uri, attempts.status,
                       attempts.ses_message_id, attempts.failure_classification,
                       attempts.sanitized_diagnostic, attempts.created_at,
                       attempts.confirmed_failed_at,
                       (attempts.created_at > NOW() - INTERVAL '14 days')
                           AS retry_window_open
                FROM was_delivery_attempts AS attempts
                JOIN was_report_runs AS runs ON runs.id = attempts.report_run_id
                JOIN was_delivery_stakeholder_grants AS grants
                  ON grants.stakeholder_tag = runs.stakeholder_tag
                 AND grants.principal_key = %s
                WHERE attempts.id = %s
                  AND attempts.status IN (
                      'confirmed_failure', 'held', 'failed_pre_send'
                  )
                  AND (attempts.original_failed_attempt_id IS NULL OR
                       attempts.created_at > NOW() - INTERVAL '14 days')
                """,
                (_validated_principal_key(actor_id), attempt_id),
            )
            failure = _row_dictionary(cursor.fetchone())
            if failure is None:
                return None
            cursor.execute(
                """
                SELECT id, original_failed_attempt_id, failed_recipient,
                       CASE WHEN created_at > NOW() - INTERVAL '14 days'
                            THEN recipient_addresses ELSE ARRAY[]::text[]
                       END AS recipient_addresses, requested_by_principal_key,
                       status, ses_message_id, failure_classification,
                       sanitized_diagnostic, created_at, sent_at
                FROM was_delivery_attempts
                WHERE report_run_id = %s
                  AND (original_failed_attempt_id IS NULL OR
                       created_at > NOW() - INTERVAL '14 days')
                ORDER BY created_at, id
                """,
                (failure["report_run_id"],),
            )
            failure["attempt_history"] = [dict(row) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT id, delivery_attempt_id, event_type, delivery_status,
                       CASE WHEN received_at > NOW() - INTERVAL '14 days'
                            THEN affected_recipients ELSE ARRAY[]::text[]
                       END AS affected_recipients,
                       bounce_type, bounce_subtype,
                       smtp_status_code, occurred_at
                FROM was_ses_delivery_events
                WHERE delivery_attempt_id IN (
                    SELECT id FROM was_delivery_attempts
                    WHERE report_run_id = %s
                      AND (original_failed_attempt_id IS NULL OR
                           created_at > NOW() - INTERVAL '14 days')
                )
                ORDER BY occurred_at, id
                """,
                (failure["report_run_id"],),
            )
            failure["ses_events"] = [dict(row) for row in cursor.fetchall()]
            return failure


def get_retry_context(attempt_id: int, actor_id: str) -> dict | None:
    """Read a scoped completed report and failed attempt independent of emailed_at."""
    with _database_connection() as database_connection:
        with database_connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT attempts.id, attempts.report_run_id, attempts.status,
                       attempts.recipient_addresses, attempts.archived_report_s3_uri,
                       attempts.archive_sha256,
                       runs.stakeholder_tag, runs.status AS report_generation_status,
                       runs.delivery_purpose, runs.artifact_type,
                       runs.output_path, runs.source_tracker_id,
                       stakeholders.was_report_poc, stakeholders.next_scheduled,
                       stakeholders.report_password,
                       assignees.name AS assignee_name,
                       tracker.template, tracker.recent_nws, tracker.nws,
                       tracker.remove_nws, tracker.qualys_error,
                       tracker.scan_started_at,
                       attempts.failed_recipient
                FROM was_delivery_attempts AS attempts
                JOIN was_report_runs AS runs ON runs.id = attempts.report_run_id
                JOIN was_delivery_stakeholder_grants AS grants
                  ON grants.stakeholder_tag = runs.stakeholder_tag
                 AND grants.principal_key = %s
                LEFT JOIN was_stakeholders AS stakeholders
                  ON stakeholders.tag = runs.stakeholder_tag
                LEFT JOIN was_daily_report_tracker AS tracker
                  ON tracker.id = runs.source_tracker_id
                LEFT JOIN was_assignees AS assignees
                  ON assignees.id = tracker.assignee_id
                WHERE attempts.id = %s
                  AND attempts.created_at > NOW() - INTERVAL '14 days'
                """,
                (_validated_principal_key(actor_id), attempt_id),
            )
            context = _row_dictionary(cursor.fetchone())
            if context is None:
                return None
            return context


def record_access(actor_id: str, attempt_id: int | None, action: str) -> None:
    """Audit an authorized list or detail read without copying sensitive data."""
    if action not in {"list", "detail"}:
        raise ValueError("Unknown delivery access action.")
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO was_delivery_audit_events "
                    "(actor_principal_key, action, delivery_attempt_id) "
                    "VALUES (%s, %s, %s)",
                    (_validated_principal_key(actor_id), action, attempt_id),
                )
            database_connection.commit()
        except Exception:
            database_connection.rollback()
            raise


def recover_stale_delivery_attempts(actor_id: str) -> int:
    """Classify stale scoped retries without ever sending another email.

    A pending child has not reached SES and can be replaced by a new request.
    A sending child may have reached SES and must remain held for manual review.
    """
    actor_principal = _validated_principal_key(actor_id)
    timeout_seconds = positive_integer("WAS_EMAIL_CLAIM_STALE_SECONDS", 300)
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH stale_attempts AS (
                        UPDATE was_delivery_attempts AS attempts
                        SET status = CASE WHEN attempts.status = 'pending'
                                THEN 'failed_pre_send' ELSE 'held' END,
                            sanitized_diagnostic = CASE
                                WHEN attempts.status = 'pending'
                                THEN 'stale_pre_send'
                                ELSE 'stale_ses_outcome_uncertain' END,
                            updated_at = NOW()
                        FROM was_report_runs AS runs
                        JOIN was_delivery_stakeholder_grants AS grants
                          ON grants.stakeholder_tag = runs.stakeholder_tag
                         AND grants.principal_key = %s
                        WHERE attempts.report_run_id = runs.id
                          AND attempts.original_failed_attempt_id IS NOT NULL
                          AND attempts.status IN ('pending', 'sending')
                          AND attempts.updated_at <
                              NOW() - (%s * INTERVAL '1 second')
                        RETURNING attempts.id
                    )
                    INSERT INTO was_delivery_audit_events
                        (actor_principal_key, action, delivery_attempt_id)
                    SELECT %s, 'retry_result', id FROM stale_attempts
                    """,
                    (actor_principal, timeout_seconds, actor_principal),
                )
                recovered_count = cursor.rowcount
            database_connection.commit()
            return recovered_count
        except Exception:
            database_connection.rollback()
            raise


def create_initial_attempt(
    report_run_id: int, recipients: list[str], artifact_s3_uri: str | None,
    claim_token: str,
) -> int:
    """Record one initial send exactly once for a report-run email claim."""
    validated_recipients = [_validated_recipient(value) for value in recipients]
    if not validated_recipients or not claim_token:
        raise ValueError("Recipients and a claim token are required.")
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO was_delivery_attempts
                        (report_run_id, recipient_addresses,
                         archived_report_s3_uri, claim_token)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (report_run_id, claim_token)
                      WHERE original_failed_attempt_id IS NULL
                        AND claim_token IS NOT NULL
                    DO UPDATE SET updated_at = was_delivery_attempts.updated_at
                    RETURNING id
                    """,
                    (report_run_id, validated_recipients, artifact_s3_uri, claim_token),
                )
                attempt_id = int(cursor.fetchone()[0])
            database_connection.commit()
            return attempt_id
        except Exception:
            database_connection.rollback()
            raise


def record_archive_sha256(attempt_id: int, archive_sha256: str) -> None:
    """Persist the validated initial S3 PDF digest before an SES send."""
    if (
        not isinstance(archive_sha256, str)
        or len(archive_sha256) != 64
        or any(character not in "0123456789abcdef" for character in archive_sha256)
    ):
        raise ValueError("A SHA-256 archive digest is required.")
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE was_delivery_attempts
                    SET archive_sha256 = %s, updated_at = NOW()
                    WHERE id = %s AND original_failed_attempt_id IS NULL
                      AND archived_report_s3_uri IS NOT NULL
                      AND status = 'pending'
                    RETURNING id
                    """,
                    (archive_sha256, attempt_id),
                )
                if cursor.fetchone() is None:
                    raise ValueError("Initial delivery archive state changed.")
            database_connection.commit()
        except Exception:
            database_connection.rollback()
            raise


def claim_retry(
    attempt_id: int, actor_id: str, failed_recipient: str,
    corrected_recipient: str, idempotency_key: str,
) -> dict:
    """Atomically claim an audited same-address or corrected retry request."""
    original = _validated_recipient(failed_recipient)
    corrected = _validated_recipient(corrected_recipient)
    actor_principal = _validated_principal_key(actor_id)
    if (
        not isinstance(idempotency_key, str)
        or not idempotency_key
        or len(idempotency_key) > 128
        or any(ord(character) < 33 or ord(character) > 126
               for character in idempotency_key)
    ):
        raise ValueError("A bounded retry idempotency key is required.")
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT attempts.id, attempts.report_run_id,
                           attempts.recipient_addresses,
                           attempts.archived_report_s3_uri,
                           attempts.archive_sha256, attempts.status,
                           runs.output_path, runs.status AS report_generation_status,
                           runs.delivery_purpose, runs.artifact_type
                    FROM was_delivery_attempts AS attempts
                    JOIN was_report_runs AS runs ON runs.id = attempts.report_run_id
                    JOIN was_delivery_stakeholder_grants AS grants
                      ON grants.stakeholder_tag = runs.stakeholder_tag
                     AND grants.principal_key = %s
                    WHERE attempts.id = %s
                      AND attempts.created_at > NOW() - (%s * INTERVAL '1 day')
                    FOR UPDATE OF attempts
                    """,
                    (actor_principal, attempt_id, DELIVERY_RETENTION_DAYS),
                )
                parent = _row_dictionary(cursor.fetchone())
                if parent is None:
                    raise LookupError("Delivery failure was not found.")
                cursor.execute(
                    """
                    SELECT id, failed_recipient, recipient_addresses, status,
                           requested_by_principal_key
                    FROM was_delivery_attempts
                    WHERE original_failed_attempt_id = %s
                      AND idempotency_key = %s
                    """,
                    (attempt_id, idempotency_key),
                )
                existing = _row_dictionary(cursor.fetchone())
                if existing is not None:
                    if (
                        existing["failed_recipient"] != original
                        or existing["recipient_addresses"] != [corrected]
                        or existing["requested_by_principal_key"] != actor_principal
                    ):
                        raise ValueError("This retry request has different details.")
                    database_connection.commit()
                    return existing
                cursor.execute(
                    """
                    SELECT id FROM was_delivery_attempts
                    WHERE original_failed_attempt_id = %s
                      AND failed_recipient = %s
                      AND status <> 'failed_pre_send'
                    LIMIT 1
                    """,
                    (attempt_id, original),
                )
                if cursor.fetchone() is not None:
                    raise ValueError("This failure already has an active retry.")
                if (
                    parent["status"] != "confirmed_failure"
                    or parent["report_generation_status"] != "completed"
                    or parent["delivery_purpose"] != "customer"
                    or parent["artifact_type"] != "pdf"
                    or not parent["output_path"]
                    or not str(parent["output_path"]).startswith("s3://")
                    or parent["archived_report_s3_uri"] != parent["output_path"]
                    or original not in parent["recipient_addresses"]
                ):
                    raise ValueError("Delivery failure is not eligible for retry.")
                cursor.execute(
                    """
                    SELECT MAX(occurred_at) AS confirmed_failure_at
                    FROM was_ses_delivery_events
                    WHERE delivery_attempt_id = %s
                      AND delivery_status = 'confirmed_failure'
                      AND %s = ANY(affected_recipients)
                    """,
                    (attempt_id, original),
                )
                confirmed_failure_at = cursor.fetchone()["confirmed_failure_at"]
                if confirmed_failure_at is None:
                    raise ValueError("Recipient failure is not confirmed by SES.")
                cursor.execute(
                    """
                    SELECT 1 FROM was_ses_delivery_events
                    WHERE delivery_attempt_id = %s
                      AND delivery_status IN ('delivered', 'held')
                      AND %s = ANY(affected_recipients)
                      AND (
                          delivery_status = 'delivered'
                          OR event_type = 'Complaint'
                          OR occurred_at >= %s
                      )
                    LIMIT 1
                    """,
                    (attempt_id, original, confirmed_failure_at),
                )
                if cursor.fetchone() is not None:
                    raise ValueError(
                        "Recipient delivery outcome requires manual review."
                    )
                cursor.execute(
                    """
                    INSERT INTO was_delivery_attempts
                        (report_run_id, original_failed_attempt_id,
                         failed_recipient,
                         recipient_addresses, archived_report_s3_uri,
                         archive_sha256,
                         requested_by_principal_key, idempotency_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, status, recipient_addresses
                    """,
                    (
                        parent["report_run_id"], attempt_id, original, [corrected],
                        parent["output_path"], parent["archive_sha256"],
                        actor_principal, idempotency_key,
                    ),
                )
                created = dict(cursor.fetchone())
                if original != corrected:
                    cursor.execute(
                        """
                        INSERT INTO was_delivery_audit_events
                            (actor_principal_key, action, delivery_attempt_id)
                        VALUES (%s, 'correction', %s)
                        """,
                        (actor_principal, created["id"]),
                    )
                cursor.execute(
                    """
                    INSERT INTO was_delivery_audit_events
                        (actor_principal_key, action, delivery_attempt_id)
                    VALUES (%s, 'retry_requested', %s)
                    """,
                    (actor_principal, created["id"]),
                )
            database_connection.commit()
            return created
        except Exception:
            database_connection.rollback()
            raise


def _update_attempt(
    attempt_id: int, from_status: str, to_status: str,
    diagnostic: str | None = None,
) -> None:
    """Apply one compare-and-swap delivery state transition."""
    if diagnostic is not None and len(diagnostic) > 128:
        raise ValueError("Diagnostic code is too long.")
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE was_delivery_attempts
                    SET status = %s, sanitized_diagnostic = %s,
                        updated_at = NOW(),
                        confirmed_failed_at = CASE WHEN %s = 'confirmed_failure'
                            THEN NOW() ELSE confirmed_failed_at END
                    WHERE id = %s AND status = %s
                      AND (%s <> 'sending' OR
                           created_at > NOW() - (%s * INTERVAL '1 day'))
                    RETURNING id, requested_by_principal_key
                    """,
                    (
                        to_status, diagnostic, to_status, attempt_id,
                        from_status, to_status, DELIVERY_RETENTION_DAYS,
                    ),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("Delivery attempt state changed concurrently.")
                if row[1] is not None and to_status != "sending":
                    cursor.execute(
                        """
                        INSERT INTO was_delivery_audit_events
                            (actor_principal_key, action, delivery_attempt_id)
                        VALUES (%s, 'retry_result', %s)
                        """,
                        (row[1], attempt_id),
                    )
            database_connection.commit()
        except Exception:
            database_connection.rollback()
            raise


def mark_sending(attempt_id: int) -> None:
    """Record that an SES request is about to begin."""
    _update_attempt(attempt_id, "pending", "sending")


def mark_pre_send_failure(attempt_id: int, diagnostic: str) -> None:
    """Record a failed artifact or validation step before any SES request."""
    _update_attempt(attempt_id, "pending", "failed_pre_send", diagnostic)


def mark_uncertain(attempt_id: int, diagnostic: str) -> None:
    """Hold an attempt whose SES request may have succeeded."""
    _update_attempt(attempt_id, "sending", "held", diagnostic)


def mark_accepted(attempt_id: int, ses_message_id: str) -> None:
    """Store SES acceptance and correlate notifications that arrived first."""
    if not ses_message_id or len(ses_message_id) > 512:
        raise ValueError("Invalid SES message identifier.")
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (ses_message_id,),
                )
                cursor.execute(
                    """
                    UPDATE was_delivery_attempts
                    SET status = 'accepted', ses_message_id = %s,
                        sent_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND status = 'sending'
                    RETURNING id
                    """,
                    (ses_message_id, attempt_id),
                )
                if cursor.fetchone() is None:
                    raise ValueError("Delivery attempt was not sending.")
                cursor.execute(
                    """
                    UPDATE was_ses_delivery_events AS events
                    SET delivery_attempt_id = %s
                    FROM was_delivery_attempts AS attempts
                    WHERE events.delivery_attempt_id IS NULL
                      AND events.ses_message_id = %s
                      AND attempts.id = %s
                      AND (
                          (events.delivery_status = 'accepted'
                           AND cardinality(events.affected_recipients) = 0)
                          OR
                          (cardinality(events.affected_recipients) > 0
                           AND events.affected_recipients
                               <@ attempts.recipient_addresses)
                      )
                    """,
                    (attempt_id, ses_message_id, attempt_id),
                )
                cursor.execute(
                    """
                    UPDATE was_delivery_attempts AS attempts
                    SET status = events.delivery_status,
                        failure_classification = CASE
                            WHEN events.delivery_status = 'confirmed_failure'
                            THEN COALESCE(events.bounce_type, events.event_type)
                            ELSE attempts.failure_classification END,
                        sanitized_diagnostic = CASE
                            WHEN events.delivery_status IN ('confirmed_failure', 'held')
                            THEN events.smtp_status_code
                            ELSE attempts.sanitized_diagnostic END,
                        updated_at = NOW(),
                        confirmed_failed_at = CASE
                            WHEN events.delivery_status = 'confirmed_failure'
                            THEN events.occurred_at
                            ELSE attempts.confirmed_failed_at END
                    FROM (
                        SELECT delivery_status, occurred_at, bounce_type,
                               event_type, smtp_status_code
                        FROM was_ses_delivery_events
                        WHERE delivery_attempt_id = %s
                          AND delivery_status IN (
                              'delivered', 'confirmed_failure', 'held'
                          )
                        ORDER BY CASE delivery_status
                            WHEN 'confirmed_failure' THEN 3
                            WHEN 'held' THEN 2
                            ELSE 1 END DESC,
                            occurred_at DESC, id DESC LIMIT 1
                    ) AS events
                    WHERE attempts.id = %s
                    """,
                    (attempt_id, attempt_id),
                )
            database_connection.commit()
        except Exception:
            database_connection.rollback()
            raise


def record_ses_event(event: SesEvent) -> bool:
    """Dedupe a sanitized SES event and associate its message with an attempt."""
    if event.delivery_status not in EVENT_STATUSES:
        raise ValueError("Unknown SES delivery status.")
    if (
        not isinstance(event.occurred_at, datetime)
        or event.occurred_at.tzinfo is None
    ):
        raise ValueError("SES event timestamp must include a time zone.")
    recipients = [_validated_recipient(value) for value in event.affected_recipients]
    if event.occurred_at <= datetime.now(timezone.utc) - timedelta(
        days=DELIVERY_RETENTION_DAYS
    ):
        recipients = []
    with _database_connection() as database_connection:
        try:
            with database_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (event.ses_message_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO was_ses_delivery_events
                        (sns_message_id, ses_message_id, delivery_attempt_id,
                         event_type, delivery_status, affected_recipients,
                         bounce_type, bounce_subtype, smtp_status_code, occurred_at)
                    SELECT %s, %s, attempts.id, %s, %s, %s, %s, %s, %s, %s
                    FROM (SELECT 1) AS source
                    LEFT JOIN was_delivery_attempts AS attempts
                      ON attempts.ses_message_id = %s
                     AND (
                         (%s = 'accepted' AND cardinality(%s::text[]) = 0)
                         OR
                         (cardinality(%s::text[]) > 0
                          AND %s::text[] <@ attempts.recipient_addresses)
                     )
                    ON CONFLICT (sns_message_id) DO NOTHING
                    RETURNING id, delivery_attempt_id
                    """,
                    (
                        event.sns_message_id, event.ses_message_id,
                        event.event_type, event.delivery_status, recipients,
                        event.bounce_type, event.bounce_subtype,
                        event.smtp_status_code, event.occurred_at,
                        event.ses_message_id, event.delivery_status,
                        recipients, recipients, recipients,
                    ),
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    database_connection.commit()
                    return False
                matched_attempt_id = inserted[1]
                if (
                    matched_attempt_id is not None
                    and event.delivery_status != "accepted"
                ):
                    cursor.execute(
                        """
                        UPDATE was_delivery_attempts
                        SET status = CASE
                                WHEN status = 'confirmed_failure' THEN status
                                WHEN status = 'held' AND %s = 'delivered' THEN status
                                ELSE %s END,
                            failure_classification = CASE
                                WHEN %s = 'confirmed_failure'
                                THEN %s ELSE failure_classification END,
                            sanitized_diagnostic = CASE
                                WHEN %s IN ('confirmed_failure', 'held')
                                THEN %s ELSE sanitized_diagnostic END,
                            updated_at = NOW(),
                            confirmed_failed_at = CASE
                                WHEN %s = 'confirmed_failure' THEN %s
                                ELSE confirmed_failed_at END
                        WHERE id = %s
                          AND status IN (
                              'accepted', 'delivered', 'confirmed_failure', 'held'
                          )
                          AND %s <@ recipient_addresses
                        """,
                        (
                            event.delivery_status, event.delivery_status,
                            event.delivery_status,
                            event.bounce_type or event.event_type,
                            event.delivery_status,
                            event.smtp_status_code,
                            event.delivery_status,
                            event.occurred_at, matched_attempt_id, recipients,
                        ),
                    )
            database_connection.commit()
            return True
        except Exception:
            database_connection.rollback()
            raise
