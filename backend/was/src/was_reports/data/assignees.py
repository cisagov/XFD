"""Data access helpers for WAS assignees."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection


@dataclass(frozen=True)
class Assignee:
    """Database representation of a WAS report assignee."""

    id: int
    name: str
    email: Optional[str] = None
    active: bool = True
    email_enabled: bool = True


def normalize_assignee_name(name: str) -> str:
    """Normalize an assignee name from the legacy tracker."""
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Assignee name must not be empty.")
    return normalized_name


def get_assignee_by_name(name: str, conn: connection) -> Optional[Assignee]:
    """Return an assignee by name."""
    normalized_name = normalize_assignee_name(name)
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name, email, active, email_enabled
            FROM was_assignees
            WHERE name = %s
            """,
            (normalized_name,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    return Assignee(
        id=row[0],
        name=row[1],
        email=row[2],
        active=bool(row[3]),
        email_enabled=bool(row[4]),
    )


def list_active_assignee_names(conn: connection) -> list[str]:
    """Return active WAS assignee names in stable database order."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT name
            FROM was_assignees
            WHERE active IS TRUE
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()

    return [row[0] for row in rows]


def upsert_assignee(
    name: str,
    conn: connection,
    email: Optional[str] = None,
) -> Assignee:
    """Insert or return an existing WAS assignee."""
    normalized_name = normalize_assignee_name(name)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO was_assignees (name, email)
                VALUES (%s, %s)
                ON CONFLICT (name)
                DO UPDATE SET
                    email = COALESCE(EXCLUDED.email, was_assignees.email),
                    updated_at = NOW()
                RETURNING id, name, email, active, email_enabled
                """,
                (normalized_name, email),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    return Assignee(
        id=row[0],
        name=row[1],
        email=row[2],
        active=bool(row[3]),
        email_enabled=bool(row[4]),
    )


def upsert_assignee_in_db(name: str, email: Optional[str] = None) -> Assignee:
    """Insert or return an assignee using a managed database connection."""
    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        return upsert_assignee(name=name, conn=conn, email=email)
    finally:
        close(conn)
