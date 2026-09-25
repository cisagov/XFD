"""Isolated, idempotent analyst-only replay records and read-only previews."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from was_reports.data.report_runs import ReportRun
from was_reports.utils.database import close, connect


@dataclass(frozen=True)
class ReplayCandidate:
    """One customer execution eligible for explicit analyst-only replay."""

    tracker_id: int
    tag: str
    action: str
    original_run_id: int | None
    output_path: str | None
    tag_id: int | None
    organization_name: str | None
    scan_start_date: date | None


def list_replay_candidates(
    days_back: int = 7, manual_tracker_ids: tuple[int, ...] = (),
    include_all_manual: bool = False,
    targets_removed_tracker_ids: tuple[int, ...] = (),
) -> list[ReplayCandidate]:
    """Preview completed PDFs and explicitly selected unsent manual failures."""
    if days_back < 1:
        raise ValueError("days_back must be positive.")
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT tracker.id, tracker.tag,
                       CASE WHEN tracker.id = ANY(%s) THEN 'targets_removed'
                            WHEN runs.status = 'completed' THEN 'resend'
                            ELSE 'manual' END,
                       runs.id, runs.output_path,
                       COALESCE(tracker.tag_id, stakeholders.qualys_tag_id),
                       stakeholders.customer_name, tracker.scan_start_date
                FROM was_daily_report_tracker AS tracker
                JOIN was_stakeholders AS stakeholders ON stakeholders.tag = tracker.tag
                LEFT JOIN was_report_runs AS runs ON runs.source_tracker_id = tracker.id
                WHERE COALESCE(tracker.scan_start_date, tracker.data_pull_date)
                      BETWEEN (NOW() AT TIME ZONE 'America/New_York')::date - (%s - 1)
                          AND (NOW() AT TIME ZONE 'America/New_York')::date
                  AND stakeholders.retired IS NOT TRUE
                  AND COALESCE(tracker.template, '') <> 'Deactivated'
                  AND (runs.id IS NULL OR runs.delivery_purpose = 'customer')
                  AND (
                    (NOT (tracker.id = ANY(%s))
                     AND runs.status = 'completed' AND runs.artifact_type = 'pdf'
                     AND NULLIF(BTRIM(runs.output_path), '') IS NOT NULL)
                    OR
                    ((%s OR tracker.id = ANY(%s)) AND tracker.report_sent_date IS NULL
                     AND (runs.id IS NULL OR (runs.status = 'failed'
                          AND runs.email_status NOT IN ('held', 'sending', 'sent')
                          AND COALESCE(runs.qualys_detail_report_status, '') <> 'CREATE_REQUESTED'
                          AND COALESCE(runs.qualys_xml_report_status, '') <> 'CREATE_REQUESTED'
                          AND COALESCE(runs.error_message, '')
                              NOT LIKE '%%QualysReportCreationUncertainError%%'))
                     AND COALESCE(tracker.report_scan_notes, '') ILIKE 'MANUAL:%%')
                    OR
                    (tracker.id = ANY(%s)
                     AND tracker.status = 'Finished'
                     AND tracker.report_sent_date IS NULL
                     AND BTRIM(COALESCE(tracker.report_scan_notes, ''))
                         = 'QUALYS DELETION REQUIRED'
                     AND tracker.template = 'Action Required'
                     AND NULLIF(BTRIM(COALESCE(tracker.remove_nws, '')), '')
                         IS NOT NULL
                     AND COALESCE(tracker.tag_id, stakeholders.qualys_tag_id)
                         IS NOT NULL
                     AND (runs.id IS NULL OR (runs.status = 'failed'
                          AND runs.email_status NOT IN ('held', 'sending', 'sent')
                          AND COALESCE(runs.qualys_detail_report_status, '')
                              <> 'CREATE_REQUESTED'
                          AND COALESCE(runs.qualys_xml_report_status, '')
                              <> 'CREATE_REQUESTED'
                          AND COALESCE(runs.error_message, '')
                              NOT LIKE '%%QualysReportCreationUncertainError%%')))
                  )
                ORDER BY tracker.id
                """,
                (
                    list(targets_removed_tracker_ids),
                    days_back,
                    list(targets_removed_tracker_ids),
                    include_all_manual,
                    list(manual_tracker_ids),
                    list(targets_removed_tracker_ids),
                ),
            )
            return [ReplayCandidate(*row) for row in cursor.fetchall()]
    finally:
        close(conn)


def reserve_replay_run(
    replay_id: str, recipient: str, candidate: ReplayCandidate
) -> tuple[ReportRun, bool]:
    """Atomically reserve an analyst child without changing customer history."""
    replay_id = str(UUID(replay_id))
    recipient = recipient.strip().lower()
    if not recipient or candidate.action not in {
        "resend", "manual", "targets_removed",
    }:
        raise ValueError("A recipient and valid replay action are required.")
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO was_test_replay_batches (replay_id, recipient) "
                "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (replay_id, recipient),
            )
            cursor.execute(
                "SELECT recipient FROM was_test_replay_batches "
                "WHERE replay_id = %s FOR UPDATE", (replay_id,),
            )
            if cursor.fetchone()[0] != recipient:
                raise ValueError("Replay ID is already bound to a different recipient.")
            cursor.execute(
                """
                SELECT runs.id, runs.stakeholder_tag, runs.status, runs.output_path,
                       runs.artifact_type, runs.generation_token,
                       items.action, items.original_run_id, items.template_override
                FROM was_test_replay_items AS items
                JOIN was_report_runs AS runs ON runs.id = items.report_run_id
                WHERE items.replay_id = %s AND items.tracker_id = %s
                """, (replay_id, candidate.tracker_id),
            )
            existing = cursor.fetchone()
            if existing is not None:
                expected_override = (
                    "Targets Removed"
                    if candidate.action == "targets_removed"
                    else None
                )
                if existing[6:] != (
                    candidate.action,
                    candidate.original_run_id,
                    expected_override,
                ):
                    raise ValueError("Replay source/action differs from the original reservation.")
                conn.commit()
                return ReportRun(*existing[:6]), False
            cursor.execute(
                "SELECT tag FROM was_stakeholders WHERE tag = %s FOR UPDATE",
                (candidate.tag,),
            )
            if cursor.fetchone() is None:
                raise ValueError("Replay stakeholder no longer exists.")
            if candidate.action in {"manual", "targets_removed"}:
                cursor.execute(
                    "SELECT id FROM was_report_runs WHERE stakeholder_tag = %s "
                    "AND (status = 'running' OR email_status = 'sending') LIMIT 1",
                    (candidate.tag,),
                )
                if cursor.fetchone() is not None:
                    raise ValueError("Another report operation is active for this tag.")
            cursor.execute(
                """
                SELECT tracker.tag
                FROM was_daily_report_tracker AS tracker
                JOIN was_stakeholders AS stakeholders ON stakeholders.tag = tracker.tag
                WHERE tracker.id = %s AND tracker.tag = %s
                  AND stakeholders.retired IS NOT TRUE
                  AND COALESCE(tracker.template, '') <> 'Deactivated'
                  AND (
                    (%s = 'resend' AND EXISTS (
                        SELECT 1 FROM was_report_runs AS original
                        WHERE original.id = %s AND original.source_tracker_id = tracker.id
                          AND original.delivery_purpose = 'customer'
                          AND original.status = 'completed'
                          AND original.artifact_type = 'pdf'
                          AND original.output_path = %s
                    ))
                    OR (%s IN ('manual', 'targets_removed')
                        AND tracker.report_sent_date IS NULL
                        AND NOT EXISTS (
                            SELECT 1 FROM was_report_runs AS original
                            WHERE original.source_tracker_id = tracker.id
                              AND (original.delivery_purpose <> 'customer'
                                   OR original.status <> 'failed'
                                   OR original.email_status IN ('held', 'sending', 'sent')
                                   OR original.qualys_detail_report_status = 'CREATE_REQUESTED'
                                   OR original.qualys_xml_report_status = 'CREATE_REQUESTED'
                                   OR original.error_message
                                       LIKE '%%QualysReportCreationUncertainError%%')
                        )
                        AND (
                            (%s = 'manual'
                             AND COALESCE(tracker.report_scan_notes, '')
                                 ILIKE 'MANUAL:%%')
                            OR
                            (%s = 'targets_removed'
                             AND tracker.status = 'Finished'
                             AND BTRIM(COALESCE(tracker.report_scan_notes, ''))
                                 = 'QUALYS DELETION REQUIRED'
                             AND tracker.template = 'Action Required'
                             AND NULLIF(BTRIM(COALESCE(tracker.remove_nws, '')), '')
                                 IS NOT NULL
                             AND COALESCE(
                                 tracker.tag_id, stakeholders.qualys_tag_id
                             ) IS NOT NULL)
                        ))
                  )
                FOR SHARE OF tracker, stakeholders
                """,
                (
                    candidate.tracker_id,
                    candidate.tag,
                    candidate.action,
                    candidate.original_run_id,
                    candidate.output_path,
                    candidate.action,
                    candidate.action,
                    candidate.action,
                ),
            )
            if cursor.fetchone() is None:
                raise ValueError("Replay source is no longer eligible. Preview again.")
            generation_token = str(uuid4())
            status = "completed" if candidate.action == "resend" else "running"
            output_path = candidate.output_path if candidate.action == "resend" else None
            artifact_type = "pdf" if candidate.action == "resend" else None
            cursor.execute(
                """
                INSERT INTO was_report_runs
                    (stakeholder_tag, status, delivery_purpose, generation_token,
                     output_path, artifact_type, completed_at)
                VALUES (%s, %s, 'analyst', %s, %s, %s,
                        CASE WHEN %s = 'completed' THEN NOW() ELSE NULL END)
                RETURNING id
                """,
                (candidate.tag, status, generation_token, output_path, artifact_type, status),
            )
            report_run_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO was_test_replay_items
                    (replay_id, tracker_id, original_run_id, report_run_id,
                     action, template_override)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    replay_id,
                    candidate.tracker_id,
                    candidate.original_run_id,
                    report_run_id,
                    candidate.action,
                    (
                        "Targets Removed"
                        if candidate.action == "targets_removed"
                        else None
                    ),
                ),
            )
        conn.commit()
        return ReportRun(report_run_id, candidate.tag, status, output_path,
                         artifact_type, generation_token), True
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)
