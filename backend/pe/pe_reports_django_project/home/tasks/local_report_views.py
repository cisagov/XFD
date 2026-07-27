"""Production-equivalent report SQL views for local ``pesyncdb``.

Production PE databases define ``vw_*`` / ``mat_vw_*`` objects via migrations and
scheduled refreshes. Local ``pesyncdb`` only creates base tables, so this module
applies bundled view DDL (``sql/local_report_views.sql``) so report generation
exercises real joins and aggregations.

Not used in deployed/staging environments.
"""
# Standard Python Libraries
import logging
from pathlib import Path
import re

# Third-Party Libraries
from django.db import connections
from psycopg2 import sql

DATABASE = "default"
SQL_DIR = Path(__file__).resolve().parent / "sql"
VIEWS_SQL_PATH = SQL_DIR / "local_report_views.sql"
VIEW_ORDER_PATH = SQL_DIR / "local_report_view_order.txt"

CREATE_VIEW_RE = re.compile(
    r"^CREATE (?:OR REPLACE )?(MATERIALIZED )?VIEW (\w+) AS\b",
    re.IGNORECASE | re.MULTILINE,
)

LOGGER = logging.getLogger(__name__)


def _emit(message, stdout):
    if stdout is not None:
        stdout.write(message)
    else:
        LOGGER.info("%s", message)


def _load_view_order():
    if not VIEW_ORDER_PATH.exists():
        raise FileNotFoundError(f"Missing view order file: {VIEW_ORDER_PATH}")
    return [
        line.strip()
        for line in VIEW_ORDER_PATH.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _load_view_statements():
    if not VIEWS_SQL_PATH.exists():
        raise FileNotFoundError(f"Missing view SQL file: {VIEWS_SQL_PATH}")
    sql_text = VIEWS_SQL_PATH.read_text()
    statements = {}
    matches = list(CREATE_VIEW_RE.finditer(sql_text))
    for index, match in enumerate(matches):
        view_name = match.group(2)
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(sql_text)
        statements[view_name] = sql_text[start:end].strip().rstrip(";") + ";"
    return statements


def build_local_report_views():
    """Return ordered (view_name, create_sql) pairs for local report views."""
    order = _load_view_order()
    statements = _load_view_statements()
    missing = [name for name in order if name not in statements]
    if missing:
        raise KeyError(f"Missing SQL for local report views: {', '.join(missing)}")
    return [(name, statements[name]) for name in order]


def _materialized_view_exists(cursor, view_name):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_matviews
            WHERE schemaname = 'public'
              AND matviewname = %s
        )
        """,
        [view_name],
    )
    return cursor.fetchone()[0]


def _sql_view_exists(cursor, view_name):
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name = %s
        )
        """,
        [view_name],
    )
    return cursor.fetchone()[0]


def _view_exists(cursor, view_name, create_sql):
    if create_sql.upper().startswith("CREATE MATERIALIZED VIEW"):
        return _materialized_view_exists(cursor, view_name)
    return _sql_view_exists(cursor, view_name)


def _is_stub_definition(definition: str) -> bool:
    lowered = definition.lower()
    if "where false" in lowered:
        return True
    if "null::" in lowered and " from " not in lowered and " join " not in lowered:
        return True
    return False


def _fetch_view_definition(cursor, view_name, materialized: bool) -> str | None:
    if materialized:
        cursor.execute(
            "SELECT pg_get_viewdef(%s::regclass, true)",
            [view_name],
        )
    else:
        cursor.execute(
            "SELECT pg_get_viewdef(%s::regclass, true)",
            [view_name],
        )
    row = cursor.fetchone()
    return row[0] if row else None


def _drop_view(cursor, view_name, materialized: bool) -> None:
    kind = "MATERIALIZED VIEW" if materialized else "VIEW"
    cursor.execute(
        sql.SQL("DROP {} IF EXISTS {}").format(
            sql.SQL(kind),
            sql.Identifier(view_name),
        )
    )


def ensure_local_report_views(database=DATABASE, stdout=None):
    """Create local report views when missing (``pesyncdb`` only)."""
    view_definitions = build_local_report_views()

    with connections[database].cursor() as cursor:
        for view_name, create_sql in view_definitions:
            materialized = create_sql.upper().startswith("CREATE MATERIALIZED VIEW")
            exists = _view_exists(cursor, view_name, create_sql)
            if exists:
                definition = _fetch_view_definition(cursor, view_name, materialized)
                if definition and _is_stub_definition(definition):
                    _emit(f"Replacing local report view stub {view_name}...", stdout)
                    _drop_view(cursor, view_name, materialized)
                    exists = False
            if exists:
                continue
            _emit(f"Creating local report view {view_name}...", stdout)
            cursor.execute(create_sql)
