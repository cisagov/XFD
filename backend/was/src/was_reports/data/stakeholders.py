"""Stakeholder data access for WAS report generation."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from was_reports.utils.passwords import (
    generate_report_password,
    validate_report_password,
)

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection


@dataclass(frozen=True)
class Stakeholder:
    """Stakeholder fields required by WAS report generation."""

    tag: str
    report_password: Optional[str]
    next_scheduled: Optional[int] = None
    manual_report: bool = False
    retired: bool = False


def get_stakeholder(tag: str, conn: connection) -> Optional[Stakeholder]:
    """Return a stakeholder record by tag."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT tag, report_password
            FROM was_stakeholders
            WHERE tag = %s
            """,
            (tag,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return Stakeholder(tag=row[0], report_password=row[1])


def list_due_stakeholders(
    conn: connection,
    current_epoch: int,
    include_manual: bool = False,
    include_retired: bool = False,
    limit: Optional[int] = None,
) -> List[Stakeholder]:
    """Return stakeholders whose scheduled report date is due."""
    query = """
        SELECT tag, report_password, next_scheduled, manual_report, retired
        FROM was_stakeholders
        WHERE next_scheduled IS NOT NULL
          AND next_scheduled <= %s
    """
    parameters = [current_epoch]

    if not include_manual:
        query += " AND manual_report IS NOT TRUE"

    if not include_retired:
        query += " AND retired IS NOT TRUE"

    query += " ORDER BY next_scheduled ASC, tag ASC"

    if limit is not None:
        query += " LIMIT %s"
        parameters.append(limit)

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    stakeholders = []
    for row in rows:
        stakeholders.append(
            Stakeholder(
                tag=row[0],
                report_password=row[1],
                next_scheduled=row[2],
                manual_report=bool(row[3]),
                retired=bool(row[4]),
            )
        )

    return stakeholders


def list_due_stakeholders_for_report(
    current_epoch: int,
    include_manual: bool = False,
    include_retired: bool = False,
    limit: Optional[int] = None,
) -> List[Stakeholder]:
    """Return due stakeholders using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_due_stakeholders(
            conn=conn,
            current_epoch=current_epoch,
            include_manual=include_manual,
            include_retired=include_retired,
            limit=limit,
        )
    finally:
        close(conn)


def get_report_password(tag: str) -> Optional[str]:
    """Return the WAS report password for a stakeholder tag."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        stakeholder = get_stakeholder(tag, conn)
    finally:
        close(conn)

    if stakeholder is None:
        return None

    return stakeholder.report_password


def create_report_password(tag: str, conn: connection) -> str:
    """Create and save a report password for a stakeholder when one is absent."""
    generated_password = generate_report_password()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_stakeholders
                SET report_password = %s,
                    updated_at = NOW()
                WHERE tag = %s
                  AND (report_password IS NULL OR report_password = '')
                RETURNING report_password
                """,
                (generated_password, tag),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is not None:
        return row[0]

    existing_password = get_stakeholder(tag, conn)
    if existing_password is None:
        raise KeyError("Stakeholder tag {} was not found.".format(tag))

    if not existing_password.report_password:
        raise RuntimeError(
            "Unable to create report password for stakeholder tag {}.".format(tag)
        )

    return existing_password.report_password


def create_report_password_for_tag(tag: str) -> str:
    """Create and save a report password using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return create_report_password(tag, conn)
    finally:
        close(conn)


def update_report_password(tag: str, report_password: str, conn: connection) -> str:
    """Update and return the report password for a stakeholder."""
    validate_report_password(report_password)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_stakeholders
                SET report_password = %s,
                    updated_at = NOW()
                WHERE tag = %s
                RETURNING report_password
                """,
                (report_password, tag),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        raise KeyError("Stakeholder tag {} was not found.".format(tag))

    return row[0]


def update_report_password_for_tag(tag: str, report_password: str) -> str:
    """Update a stakeholder report password using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return update_report_password(tag, report_password, conn)
    finally:
        close(conn)


def rotate_report_password(tag: str, conn: connection) -> str:
    """Generate, update, and return a new stakeholder report password."""
    generated_password = generate_report_password()
    return update_report_password(tag, generated_password, conn)


def rotate_report_password_for_tag(tag: str) -> str:
    """Rotate a stakeholder report password using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return rotate_report_password(tag, conn)
    finally:
        close(conn)
