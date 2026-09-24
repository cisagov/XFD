"""Explicit standalone targets; never enroll or update a stakeholder."""

from dataclasses import dataclass, field
from uuid import uuid4

from was_mailer.message import approved_analyst_recipients
from was_reports.data.report_runs import ActiveReportOperationError, ReportRun
from was_reports.utils.database import connect, close
from was_reports.utils.passwords import generate_report_password


class StandaloneTargetError(ValueError):
    """An actionable standalone validation error containing no secrets."""


@dataclass(frozen=True)
class StandaloneRequest:
    """Claimed run and private in-memory encryption material."""

    run: ReportRun
    password: str = field(repr=False)
    delivery_email: str


def normalized_recipient(value: str) -> str:
    """Validate approved recipients without accepting email header injection."""
    if "\r" in value or "\n" in value:
        raise StandaloneTargetError("Delivery email cannot contain newline characters.")
    return ",".join(approved_analyst_recipients(value)).lower()


def create_standalone_request(
    tag: str, tag_id: int, email: str | None
) -> StandaloneRequest:
    """Atomically reuse a target and claim a run; never replace saved secrets."""
    if tag_id <= 0:
        raise ValueError("Qualys tag ID must be positive.")
    recipient = normalized_recipient(email) if email is not None else None
    conn = connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"was-standalone:{tag_id}",),
            )
            cursor.execute(
                "SELECT 1 FROM was_stakeholders WHERE tag = %s OR qualys_tag_id = %s",
                (tag, tag_id),
            )
            if cursor.fetchone():
                raise StandaloneTargetError(
                    "This tag is enrolled. Use the existing stakeholder on-demand option."
                )
            cursor.execute(
                "SELECT id, tag, report_password, delivery_email FROM was_standalone_report_targets "
                "WHERE qualys_tag_id = %s FOR UPDATE",
                (tag_id,),
            )
            target = cursor.fetchone()
            if target is None:
                if recipient is None:
                    raise StandaloneTargetError(
                        "A delivery email is required for a new standalone target."
                    )
                password = generate_report_password()
                cursor.execute(
                    "INSERT INTO was_standalone_report_targets "
                    "(qualys_tag_id, tag, report_password, delivery_email) VALUES (%s,%s,%s,%s) RETURNING id",
                    (tag_id, tag, password, recipient),
                )
                target_id = cursor.fetchone()[0]
            else:
                target_id, saved_tag, password, saved_email = target
                if saved_tag != tag:
                    raise StandaloneTargetError(
                        "Qualys tag name changed; review the standalone target before retrying."
                    )
                saved_email = normalized_recipient(saved_email)
                if recipient is not None and recipient != saved_email:
                    raise StandaloneTargetError(
                        "Delivery email differs from the saved target; review it before changing recipients."
                    )
                recipient = saved_email
            cursor.execute(
                "SELECT id FROM was_report_runs WHERE standalone_target_id = %s "
                "AND (status = 'running' OR email_status IN ('sending', 'held') AND status = 'completed')",
                (target_id,),
            )
            active = cursor.fetchone()
            if active:
                raise ActiveReportOperationError(
                    "Standalone run {} is active or held; inspect it before retrying.".format(
                        active[0]
                    )
                )
            token = str(uuid4())
            cursor.execute(
                "INSERT INTO was_report_runs (standalone_target_id, status, generation_token, "
                "delivery_purpose, email_status) VALUES (%s, 'running', %s, 'standalone', 'pending') RETURNING id",
                (target_id, token),
            )
            run = ReportRun(
                cursor.fetchone()[0], tag, "running", generation_token=token
            )
        conn.commit()
        return StandaloneRequest(run, password, recipient)
    except Exception:
        conn.rollback()
        raise
    finally:
        close(conn)
