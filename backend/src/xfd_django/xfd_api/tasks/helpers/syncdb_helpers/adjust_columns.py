"""Adjust column types based on model.py vs. RDS."""
# Standard Python Libraries
import logging
import re
import traceback

# Third-Party Libraries
from django.db import connections
from xfd_api.tasks.syncdb_task import get_ordered_models

LOGGER = logging.getLogger(__name__)


def normalize_pg_type(column_name: str, table_name: str, database: str) -> str:
    """Normalize postgres type."""
    with connections[database].cursor() as cursor:
        cursor.execute(
            """
            SELECT data_type, udt_name
              FROM information_schema.columns
             WHERE table_name   = %s
               AND column_name  = %s
               AND table_schema = 'public';
            """,
            [table_name, column_name],
        )
        row = cursor.fetchone()
        if not row:
            return ""
        data_type, udt_name = row[0].lower(), row[1].lower()

    if data_type == "array":
        # …array‐normalization logic as before…
        if udt_name.startswith("_"):
            base = udt_name[1:]
            if base == "int4":
                return "integer[]"
            elif base == "int8":
                return "bigint[]"
            elif base == "varchar":
                return "varchar[]"
            elif base == "text":
                return "text[]"
            elif base == "bool":
                return "boolean[]"
            elif base == "jsonb":
                return "jsonb[]"
            elif base == "timestamptz":
                return "timestamp with time zone[]"
            elif base == "timestamp":
                return "timestamp without time zone[]"
            else:
                return f"{base}[]"
        if udt_name.endswith("[]"):
            return udt_name
        return "array"

    if "character varying" in data_type:
        return "varchar"

    return data_type  # e.g. "integer", "numeric", "boolean", etc.


def adjust_column_types(target_app_label: str, using: str = "mini_data_lake"):
    """
    For each model in target_app_label, compare Django’s db_type() vs. the actual Postgres type.

    Skip:
      • any "numeric" → "numeric(p,s)" mismatch,
      • any "varchar" → "varchar(…)" mismatch,
      • any array→scalar mismatch.
    Otherwise, drop dependent views and ALTER as needed.
    """
    db_mapping = {"xfd_mini_dl": "mini_data_lake", "xfd_api": "default"}
    database = db_mapping[target_app_label]
    if using:
        database = using

    (
        f"Phase 2: Adjusting column types for '{target_app_label}' on DB alias '{database}'…"
    )

    ordered = get_ordered_models(target_app_label)

    for model in ordered:
        table_name = model._meta.db_table

        for field in model._meta.fields:
            col = field.column

            # 1) Figure out the “actual” type in Postgres:
            actual = normalize_pg_type(col, table_name, database)
            if not actual:
                continue  # column doesn’t exist yet (e.g. deferred FK)

            # 2) Figure out the “desired” type from Django’s field.db_type():
            desired_raw = field.db_type(connection=connections[database]) or ""
            desired_lower = desired_raw.lower().strip()

            # 3) Extract base + optional (precision) + optional []:
            m = re.match(r"^([a-z ]+)(?:\(\d+(?:,\s*\d+)?\))?(\[\])?$", desired_lower)
            if m:
                base_type = m.group(1).strip()
                array_part = m.group(2) or ""
                desired_pref = f"{base_type}{array_part}"
            else:
                desired_pref = desired_lower

            # 4a) If already identical, skip:
            if actual == desired_pref:
                continue

            # 4b) If actual is plain numeric and desired is numeric(p,s), skip:
            if actual == "numeric" and desired_pref.startswith("numeric("):
                continue

            # 4c) If actual is plain varchar and desired is varchar(length), skip:
            #     i.e. treat varchar == varchar(...) as “close enough”:
            if actual == "varchar" and desired_pref.startswith("varchar("):
                continue

            # 4d) If actual is an array but model expects a scalar, warn + skip:
            if actual.endswith("[]") and not desired_pref.endswith("[]"):
                LOGGER.warning(
                    "⚠️ Skipping ALTER on %s.%s: "
                    "actual is '%s', but model expects '%s'. Cannot cast array→scalar.",
                    table_name,
                    col,
                    actual,
                    desired_pref,
                )
                continue

            # 5) Otherwise, we truly need an ALTER:
            LOGGER.info(
                "Column type mismatch on %s.%s: actual='%s' vs desired='%s'",
                table_name,
                col,
                actual,
                desired_pref,
            )

            # 5a) Drop any dependent views (via pg_depend):
            with connections[database].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c_view.relname
                      FROM pg_class   AS c_tab
                      JOIN pg_depend  AS dep
                        ON dep.refobjid = c_tab.oid
                      JOIN pg_class   AS c_view
                        ON c_view.oid = dep.objid
                     WHERE c_tab.relname = %s
                       AND c_tab.relkind = 'r'
                       AND c_view.relkind = 'v'
                       AND dep.deptype   = 'n';
                    """,
                    [table_name],
                )
                dependents = [r[0] for r in cursor.fetchall()]

            for vname in dependents:
                LOGGER.warning(
                    "Dropping dependent view '%s' to allow ALTER on %s.%s",
                    vname,
                    table_name,
                    col,
                )
                try:
                    with connections[database].cursor() as c2:
                        c2.execute(
                            f"DROP VIEW IF EXISTS {connections[database].ops.quote_name(vname)} CASCADE;"
                        )
                    LOGGER.info("‣ Dropped view '%s'", vname)
                except Exception as e:
                    LOGGER.error("⚠️ Could not drop view '%s': %s", vname, e)

            # 5b) Finally attempt the ALTER:
            try:
                alter_sql = (
                    f"ALTER TABLE {connections[database].ops.quote_name(table_name)} "
                    f"ALTER COLUMN {connections[database].ops.quote_name(col)} "
                    f"TYPE {desired_pref} USING {connections[database].ops.quote_name(col)}::{desired_pref};"
                )
                with connections[database].cursor() as cursor:
                    cursor.execute(alter_sql)
                LOGGER.info("✅ Altered %s.%s to type %s", table_name, col, desired_pref)
            except Exception as e:
                LOGGER.error(
                    "❌ Failed to ALTER %s.%s → %s: %s", table_name, col, desired_pref, e
                )
                traceback.print_exc()

    LOGGER.info("Column‐type adjustments complete.")
