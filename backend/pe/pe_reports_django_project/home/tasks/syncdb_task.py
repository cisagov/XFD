"""Synchronize the local PE database schema from Django models."""
# Standard Python Libraries
from collections import defaultdict, deque
import logging
import os

# Third-Party Libraries
from django.apps import apps
from django.db import connections, transaction
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.utils import strip_quotes
from django.db.utils import OperationalError, ProgrammingError
from psycopg2.errors import WrongObjectType

LOGGER = logging.getLogger(__name__)

APP_LABEL = "home"
DATABASE = "default"

# Production PE exposes reporting objects as views; local sync creates base tables only.
VIEW_TABLE_PREFIXES = ("vw_", "mat_vw_")


def _is_view_model(model):
    """Return True for ORM models that map to SQL views, not physical tables."""
    return model._meta.db_table.startswith(VIEW_TABLE_PREFIXES)


def _local_sync_models(target_app_label):
    """All home app table models (managed or not), excluding SQL views."""
    return [
        model
        for model in apps.get_app_config(target_app_label).get_models()
        if not _is_view_model(model)
    ]


def table_exists_in_db(table_name, database):
    """Check whether a physical table exists (handles quoted/mixed-case names)."""
    with connections[database].cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM pg_catalog.pg_class c
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = %s
                  AND c.relkind IN ('r', 'p')
            );
            """,
            [table_name],
        )
        return cursor.fetchone()[0]


def synchronize(target_app_label=APP_LABEL, using=None):
    """Synchronize PE database schema with all home table models."""
    if target_app_label != APP_LABEL:
        raise ValueError("PE syncdb only supports the 'home' app label.")

    database = using or DATABASE
    LOGGER.info(
        "Synchronizing PE database schema for app '%s' in database '%s'...",
        target_app_label,
        database,
    )

    with connections[database].schema_editor() as schema_editor:
        ordered_models = get_ordered_models(target_app_label)
        allowed_tables = {model._meta.db_table for model in ordered_models}
        for model in ordered_models:
            LOGGER.info("Processing model: %s", model.__name__)
            process_model(schema_editor, model, database, allowed_tables)

        LOGGER.info("Processing Many-to-Many tables...")
        process_m2m_tables(schema_editor, ordered_models, database)
        cleanup_stale_tables(ordered_models, database)

    LOGGER.info("PE database synchronization complete.")


def get_ordered_models(target_app_label):
    """Return models in dependency order for foreign key constraints."""
    models = _local_sync_models(target_app_label)
    model_set = set(models)

    dependencies = defaultdict(set)
    dependents = defaultdict(set)
    for model in models:
        for field in model._meta.get_fields():
            if field.is_relation and field.related_model in model_set:
                dependencies[model].add(field.related_model)
                dependents[field.related_model].add(model)

    ordered = []
    independent_models = deque([model for model in models if not dependencies[model]])

    while independent_models:
        model = independent_models.popleft()
        ordered.append(model)
        for dependent in list(dependents[model]):
            dependencies[dependent].discard(model)
            dependents[model].discard(dependent)
            if not dependencies[dependent]:
                independent_models.append(dependent)

    remaining = [model for model in models if model not in ordered]
    if remaining:
        LOGGER.warning(
            "Circular dependencies detected among: %s",
            ", ".join(model.__name__ for model in remaining),
        )
        remaining_sorted = sorted(remaining, key=lambda model: model.__name__)
        ordered.extend(remaining_sorted)

    return ordered


def process_model(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Process a single model: create or update its table."""
    table_name = model._meta.db_table
    savepoint = transaction.savepoint(using=database)
    try:
        if table_exists_in_db(table_name, database):
            LOGGER.info("Updating table for model: %s", model.__name__)
            update_table(schema_editor, model, database, allowed_tables)
        else:
            LOGGER.info("Creating table for model: %s", model.__name__)
            try:
                schema_editor.create_model(model)
            except (ProgrammingError, OperationalError) as exc:
                if "already exists" in str(exc).lower():
                    LOGGER.info(
                        "Table %s already exists; updating schema for %s",
                        table_name,
                        model.__name__,
                    )
                    update_table(schema_editor, model, database, allowed_tables)
                else:
                    raise
        transaction.savepoint_commit(savepoint, using=database)
    except Exception as exc:
        transaction.savepoint_rollback(savepoint, using=database)
        LOGGER.error("Error processing model %s: %s", model.__name__, exc)


def process_m2m_tables(schema_editor: BaseDatabaseSchemaEditor, models, database):
    """Handle creation of Many-to-Many linking tables."""
    for model in models:
        for field in model._meta.local_many_to_many:
            m2m_table_name = field.m2m_db_table()
            savepoint = transaction.savepoint(using=database)
            try:
                if table_exists_in_db(m2m_table_name, database):
                    LOGGER.info(
                        "Many-to-Many table %s already exists. Skipping.",
                        m2m_table_name,
                    )
                else:
                    LOGGER.info("Creating Many-to-Many table: %s", m2m_table_name)
                    schema_editor.create_model(field.remote_field.through)
                transaction.savepoint_commit(savepoint, using=database)
            except Exception as exc:
                transaction.savepoint_rollback(savepoint, using=database)
                LOGGER.error(
                    "Error processing Many-to-Many table %s: %s",
                    m2m_table_name,
                    exc,
                )


def index_exists_in_db(model_index, existing_defs):
    """Return True if an index with the same name or definition already exists."""
    fields = [strip_quotes(field) for field in model_index.fields]
    condition = getattr(model_index, "condition", None)

    for name, definition in existing_defs:
        if name == model_index.name:
            return True
        if all(field in definition for field in fields):
            if condition:
                if str(condition).lower() in definition.lower():
                    return True
            else:
                return True
    return False


def update_table(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Update an existing table for the given model."""
    table_name = model._meta.db_table
    db_fields = {field.column for field in model._meta.fields}

    with connections[database].cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            [table_name],
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        missing_columns = db_fields - existing_columns
        for field in model._meta.fields:
            if field.column in missing_columns:
                if hasattr(field, "remote_field") and field.remote_field:
                    related_table = field.remote_field.model._meta.db_table
                    if related_table not in allowed_tables or not table_exists_in_db(
                        related_table, database
                    ):
                        LOGGER.warning(
                            "Skipping foreign key field '%s' on model '%s' "
                            "because referenced table '%s' does not exist yet.",
                            field.column,
                            model.__name__,
                            related_table,
                        )
                        continue
                LOGGER.info(
                    "Adding column '%s' to table '%s'", field.column, table_name
                )
                schema_editor.add_field(model, field)

        cursor.execute(
            """
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
              AND table_schema = 'public';
            """,
            [table_name],
        )
        nullability_info = {
            row[0]: (row[1].lower() == "yes") for row in cursor.fetchall()
        }

        for field in model._meta.fields:
            if field.column in existing_columns:
                actual_nullable = nullability_info.get(field.column, True)
                desired_nullable = field.null
                if actual_nullable != desired_nullable:
                    safe_table_name = connections[database].ops.quote_name(table_name)
                    safe_column_name = connections[database].ops.quote_name(
                        field.column
                    )
                    if not desired_nullable:
                        cursor.execute(
                            f"SELECT COUNT(*) FROM {safe_table_name} "
                            f"WHERE {safe_column_name} IS NULL;"  # nosec B608
                        )
                        null_count = cursor.fetchone()[0]
                        if null_count > 0:
                            LOGGER.warning(
                                "Cannot set NOT NULL on %s.%s: %s row(s) contain NULL values.",
                                table_name,
                                field.column,
                                null_count,
                            )
                            continue
                        alter_sql = (
                            f"ALTER TABLE {safe_table_name} ALTER COLUMN "
                            f"{safe_column_name} SET NOT NULL;"
                        )
                    else:
                        alter_sql = (
                            f"ALTER TABLE {safe_table_name} ALTER COLUMN "
                            f"{safe_column_name} DROP NOT NULL;"
                        )
                    try:
                        cursor.execute(alter_sql)
                    except Exception as exc:
                        LOGGER.error(
                            "Failed to update nullability of %s.%s: %s",
                            table_name,
                            field.column,
                            exc,
                        )

        extra_columns = existing_columns - db_fields
        for column in extra_columns:
            LOGGER.info(
                "Removing extra column '%s' from table '%s'", column, table_name
            )
            try:
                safe_table_name = connections[database].ops.quote_name(table_name)
                safe_column_name = connections[database].ops.quote_name(column)
                cursor.execute(
                    f"ALTER TABLE {safe_table_name} DROP COLUMN IF EXISTS {safe_column_name};"
                )
            except Exception as exc:
                LOGGER.error(
                    "Error dropping column '%s' from table '%s': %s",
                    column,
                    table_name,
                    exc,
                )

        with connections[database].cursor() as idx_cursor:
            idx_cursor.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s;
            """,
                [table_name],
            )
            existing_defs = [
                (name, definition) for name, definition in idx_cursor.fetchall()
            ]

        for model_index in model._meta.indexes:
            if not index_exists_in_db(model_index, existing_defs):
                try:
                    schema_editor.add_index(model, model_index)
                except Exception as exc:
                    LOGGER.error(
                        "Failed to add index '%s' on '%s': %s",
                        model_index.name,
                        table_name,
                        exc,
                    )


def cleanup_stale_tables(models, database):
    """Remove tables that no longer correspond to synced models."""
    LOGGER.info("Checking for stale tables...")

    with connections[database].cursor() as cursor:
        model_tables = {model._meta.db_table for model in models}
        m2m_tables = {
            field.m2m_db_table()
            for model in models
            for field in model._meta.local_many_to_many
        }
        expected_tables = model_tables.union(m2m_tables)

        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        existing_tables = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public';
        """
        )
        regular_views = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'public';
        """
        )
        materialized_views = {row[0] for row in cursor.fetchall()}

        all_views = regular_views.union(materialized_views)
        existing_tables = existing_tables - all_views
        stale_tables = existing_tables - expected_tables
        for table in stale_tables:
            LOGGER.info("Removing stale table: %s", table)
            try:
                cursor.execute(
                    "DROP TABLE {} CASCADE;".format(
                        connections[database].ops.quote_name(table)
                    )
                )
            except OperationalError as exc:
                LOGGER.error("Error dropping stale table %s: %s", table, exc)
            except WrongObjectType as exc:
                LOGGER.error("Tried to drop a non table entity %s: %s", table, exc)
            except ProgrammingError as exc:
                LOGGER.error("Issue dropping entity %s: %s", table, exc)


def drop_all_tables(app_label=APP_LABEL):
    """Drop all tables in the PE database. Used with --dangerouslyforce."""
    if app_label != APP_LABEL:
        raise ValueError("PE syncdb only supports the 'home' app label.")

    pe_user = os.getenv("PE_DB_USERNAME", "pe")
    admin_user = os.getenv("DB_USERNAME", pe_user)

    LOGGER.info("Resetting PE database schema for app '%s'...", app_label)

    with connections[DATABASE].cursor() as cursor:
        try:
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute(f"GRANT ALL ON SCHEMA public TO {admin_user};")
            cursor.execute(f"GRANT ALL ON SCHEMA public TO {pe_user};")
            cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        except Exception as exc:
            LOGGER.error("Error resetting schema: %s", exc)

    LOGGER.info("PE database schema reset successfully.")
