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


@dataclass(frozen=True)
class StakeholderDetails:
    """Stakeholder fields required by the WAS daily tracker."""

    tag: str
    was_report_poc: Optional[str] = None
    tech_poc_email: Optional[str] = None
    distro_email: Optional[str] = None
    comments: Optional[str] = None
    report_password: Optional[str] = None
    manual_report: bool = False
    fceb: bool = False


STAKEHOLDER_EXPORT_COLUMNS = (
    "tag",
    "customer_name",
    "comments",
    "location_notes",
    "ci_type",
    "testing_sector",
    "subtype",
    "distro_email",
    "tech_poc_email",
    "was_report_poc",
    "frequency",
    "num_web_apps",
    "web_apps_last_updated",
    "last_scanned",
    "next_scheduled",
    "onboarding_date",
    "parent_tag",
    "ticket",
    "elections",
    "fceb",
    "manual_report",
    "retired",
    "state",
    "created_at",
    "updated_at",
)
STAKEHOLDER_CONTACT_COLUMNS = frozenset(
    {"was_report_poc", "tech_poc_email", "distro_email"}
)


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


def get_stakeholder_details(
    tag: str,
    conn: connection,
) -> Optional[StakeholderDetails]:
    """Return stakeholder fields required by the daily tracker."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tag,
                was_report_poc,
                tech_poc_email,
                distro_email,
                comments,
                report_password,
                manual_report,
                fceb
            FROM was_stakeholders
            WHERE tag = %s
            """,
            (tag,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return StakeholderDetails(
        tag=row[0],
        was_report_poc=row[1],
        tech_poc_email=row[2],
        distro_email=row[3],
        comments=row[4],
        report_password=row[5],
        manual_report=bool(row[6]),
        fceb=bool(row[7]),
    )


def get_stakeholder_details_by_tag(tag: str) -> Optional[StakeholderDetails]:
    """Return stakeholder tracker details using a managed connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return get_stakeholder_details(tag=tag, conn=conn)
    finally:
        close(conn)


def update_stakeholder_contacts(
    tag: str,
    updates: dict[str, str | None],
    conn: connection,
) -> None:
    """Update selected stakeholder POC and email fields."""
    normalized_tag = tag.strip()
    if not normalized_tag:
        raise ValueError("Stakeholder tag must not be empty.")
    if not updates:
        raise ValueError("At least one stakeholder contact field is required.")
    invalid_columns = set(updates).difference(STAKEHOLDER_CONTACT_COLUMNS)
    if invalid_columns:
        raise ValueError("Unsupported stakeholder contact field.")

    assignments = []
    parameters: list[object] = []
    for column_name in sorted(updates):
        assignments.append("{} = %s".format(column_name))
        parameters.append(updates[column_name])
    assignments.append("updated_at = NOW()")
    parameters.append(normalized_tag)

    query = "UPDATE was_stakeholders SET {} WHERE tag = %s RETURNING tag".format(
        ", ".join(assignments)
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    if row is None:
        raise KeyError("Stakeholder tag {} was not found.".format(normalized_tag))


def update_stakeholder_contacts_for_tag(
    tag: str,
    updates: dict[str, str | None],
) -> None:
    """Update stakeholder contact fields using a managed connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        update_stakeholder_contacts(tag=tag, updates=updates, conn=conn)
    finally:
        close(conn)


def list_stakeholders_for_export(
    conn: connection,
    include_report_passwords: bool = False,
) -> tuple[list[str], list[tuple[object, ...]]]:
    """Return stakeholder export columns and rows in stable tag order."""
    columns = list(STAKEHOLDER_EXPORT_COLUMNS)
    if include_report_passwords:
        columns.insert(-2, "report_password")
    query = "SELECT {} FROM was_stakeholders ORDER BY tag ASC".format(
        ", ".join(columns)
    )
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    return columns, rows


def list_stakeholders_for_export_from_db(
    include_report_passwords: bool = False,
) -> tuple[list[str], list[tuple[object, ...]]]:
    """Return stakeholder export data using a managed connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return list_stakeholders_for_export(
            conn=conn,
            include_report_passwords=include_report_passwords,
        )
    finally:
        close(conn)


def update_scan_metadata(
    tag: str,
    last_scanned: int,
    next_scheduled: int,
    num_web_apps: int,
    web_apps_last_updated: int,
    conn: connection,
) -> None:
    """Update scan dates and web app counts for a stakeholder."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_stakeholders
                SET last_scanned = %s,
                    next_scheduled = %s,
                    num_web_apps = %s,
                    web_apps_last_updated = %s,
                    updated_at = NOW()
                WHERE tag = %s
                """,
                (
                    last_scanned,
                    next_scheduled,
                    num_web_apps,
                    web_apps_last_updated,
                    tag,
                ),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        raise


def update_scan_metadata_for_tag(
    tag: str,
    last_scanned: int,
    next_scheduled: int,
    num_web_apps: int,
    web_apps_last_updated: int,
) -> None:
    """Update scan metadata using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        update_scan_metadata(
            tag=tag,
            last_scanned=last_scanned,
            next_scheduled=next_scheduled,
            num_web_apps=num_web_apps,
            web_apps_last_updated=web_apps_last_updated,
            conn=conn,
        )
    finally:
        close(conn)


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
