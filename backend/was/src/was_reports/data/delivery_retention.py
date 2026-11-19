"""Expire WAS delivery-review recipient copies and retry detail after 14 days."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from was_reports.data.delivery_attempts import DELIVERY_RETENTION_DAYS
from was_reports.utils.database import close, connect


BATCH_SIZE = 500


def retention_counts(cutoff: datetime) -> dict[str, int]:
    """Count eligible rows without reading or returning customer information."""
    database_connection = connect()
    try:
        with database_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM was_delivery_attempts
                     WHERE original_failed_attempt_id IS NOT NULL
                       AND created_at <= %s
                       AND (status NOT IN ('pending', 'sending')
                            OR updated_at <= NOW() - INTERVAL '1 hour'))
                         AS retries,
                    (SELECT COUNT(*) FROM was_delivery_attempts
                     WHERE original_failed_attempt_id IS NULL
                       AND created_at <= %s
                       AND recipient_redacted_at IS NULL) AS recipients,
                    (SELECT COUNT(*) FROM was_ses_delivery_events
                     WHERE received_at <= %s
                       AND cardinality(affected_recipients) > 0) AS events
                """,
                (cutoff, cutoff, cutoff),
            )
            retry_count, recipient_count, event_count = cursor.fetchone()
            return {
                "expired_retries": retry_count,
                "recipient_copies": recipient_count,
                "event_recipient_copies": event_count,
            }
    finally:
        close(database_connection)


def apply_retention(cutoff: datetime) -> dict[str, int]:
    """Delete expired retry detail and redact older recipient copies.

    Original attempt and SES classification metadata remain for audit. Retry
    audit rows retain their historical attempt IDs without recipient details.
    Each bounded batch commits independently so locks are short lived.
    """
    totals = {
        "expired_retries": 0,
        "recipient_copies": 0,
        "event_recipient_copies": 0,
    }
    database_connection = connect()
    try:
        while True:
            try:
                with database_connection.cursor() as cursor:
                    cursor.execute("SET LOCAL lock_timeout = '5s'")
                    cursor.execute(
                        """
                        SELECT id FROM was_delivery_attempts
                        WHERE original_failed_attempt_id IS NOT NULL
                          AND created_at <= %s
                          AND (status NOT IN ('pending', 'sending')
                               OR updated_at <= NOW() - INTERVAL '1 hour')
                        ORDER BY created_at, id
                        LIMIT %s FOR UPDATE SKIP LOCKED
                        """,
                        (cutoff, BATCH_SIZE),
                    )
                    attempt_ids = [row[0] for row in cursor.fetchall()]
                    if not attempt_ids:
                        database_connection.commit()
                        break
                    cursor.execute(
                        """
                        DELETE FROM was_delivery_attempts
                        WHERE id = ANY(%s::bigint[])
                        """,
                        (attempt_ids,),
                    )
                    totals["expired_retries"] += cursor.rowcount
                database_connection.commit()
            except Exception:
                database_connection.rollback()
                raise
        for table_name, count_name, condition, assignment in (
            (
                "was_delivery_attempts", "recipient_copies",
                "original_failed_attempt_id IS NULL AND created_at <= %s "
                "AND recipient_redacted_at IS NULL",
                "recipient_addresses = ARRAY[]::text[], "
                "recipient_redacted_at = NOW()",
            ),
            (
                "was_ses_delivery_events", "event_recipient_copies",
                "received_at <= %s AND cardinality(affected_recipients) > 0",
                "affected_recipients = ARRAY[]::text[]",
            ),
        ):
            while True:
                try:
                    with database_connection.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '5s'")
                        cursor.execute(
                            """
                            WITH expired AS (
                                SELECT id FROM {table_name}
                                WHERE {condition}
                                ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED
                            )
                            UPDATE {table_name} AS records
                            SET {assignment}
                            FROM expired WHERE records.id = expired.id
                            """.format(
                                table_name=table_name,
                                condition=condition,
                                assignment=assignment,
                            ),
                            (cutoff, BATCH_SIZE),
                        )
                        changed_count = cursor.rowcount
                        totals[count_name] += changed_count
                    database_connection.commit()
                    if changed_count == 0:
                        break
                except Exception:
                    database_connection.rollback()
                    raise
        return totals
    finally:
        close(database_connection)


def retention_cutoff() -> datetime:
    """Return the UTC cutoff for the approved delivery-review retention rule."""
    return datetime.now(timezone.utc) - timedelta(days=DELIVERY_RETENTION_DAYS)
