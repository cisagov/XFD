"""Data access helpers for WAS special cases."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    # Third-Party Libraries
    from psycopg2.extensions import connection


@dataclass(frozen=True)
class SpecialCase:
    """Database representation of one WAS special case."""

    id: int
    value: str
    active: bool = True


def normalize_special_case_value(value: str) -> str:
    """Normalize a WAS special case value."""
    normalized_value = value.strip().upper()
    if not normalized_value:
        raise ValueError("Special case value must not be empty.")
    return normalized_value


def list_active_special_case_names(conn: connection) -> List[str]:
    """Return active special case values."""
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT value
            FROM was_special_cases
            WHERE active IS TRUE
            ORDER BY value ASC
            """
        )
        rows = cursor.fetchall()

    return [row[0] for row in rows]


def list_special_cases(
    conn: connection,
    include_inactive: bool = False,
) -> List[SpecialCase]:
    """Return special cases."""
    query = """
        SELECT id, value, active
        FROM was_special_cases
        WHERE 1 = 1
    """
    parameters = []

    if not include_inactive:
        query += " AND active IS TRUE"

    query += " ORDER BY value ASC"

    with conn.cursor() as cursor:
        cursor.execute(query, tuple(parameters))
        rows = cursor.fetchall()

    return [
        SpecialCase(
            id=row[0],
            value=row[1],
            active=bool(row[2]),
        )
        for row in rows
    ]


def upsert_special_case(
    value: str,
    conn: connection,
) -> SpecialCase:
    """Insert or reactivate a WAS special case."""
    normalized_value = normalize_special_case_value(value)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO was_special_cases (value)
                VALUES (%s)
                ON CONFLICT (value)
                DO UPDATE SET
                    active = TRUE,
                    updated_at = NOW()
                RETURNING id, value, active
                """,
                (normalized_value,),
            )
            row = cursor.fetchone()
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    return SpecialCase(
        id=row[0],
        value=row[1],
        active=bool(row[2]),
    )


def deactivate_special_case(
    value: str,
    conn: connection,
) -> bool:
    """Deactivate a WAS special case and return whether a row changed."""
    normalized_value = normalize_special_case_value(value)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE was_special_cases
                SET active = FALSE,
                    updated_at = NOW()
                WHERE value = %s
                  AND active IS TRUE
                """,
                (normalized_value,),
            )
            changed = cursor.rowcount > 0
            conn.commit()
    except Exception:
        conn.rollback()
        raise

    return changed
