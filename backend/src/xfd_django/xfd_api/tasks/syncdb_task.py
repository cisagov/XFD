"""Synchronize databases task."""
# File: xfd_api/utils/db_utils.py
# Standard Python Libraries
from collections import defaultdict, deque
import logging
import os

# Third-Party Libraries
from django.apps import apps
from django.db import connections
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.utils import strip_quotes
from django.db.utils import OperationalError, ProgrammingError
from psycopg2.errors import WrongObjectType

LOGGER = logging.getLogger(__name__)


def table_exists_in_db(table_name, database):
    """Check table exists."""
    with connections[database].cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s);", [table_name])
        return cursor.fetchone()[0] is not None


def synchronize(target_app_label=None, using=None):
    """
    Synchronize the database schema with Django models.

    Handles creation, update, and removal of tables and fields dynamically,
    including Many-to-Many linking tables.
    """
    allowed_labels = ["xfd_mini_dl", "xfd_api"]
    db_mapping = {
        "xfd_mini_dl": "mini_data_lake",
        "xfd_api": "default",
    }

    if target_app_label is None:
        raise ValueError(
            "The 'target_app_label' parameter is required to synchronize specific models. "
            "Please provide an app label."
        )

    if target_app_label not in allowed_labels:
        raise ValueError(
            "Invalid 'target_app_label' provided. Must be one of: {}.".format(
                ", ".join(allowed_labels)
            )
        )

    # Get database name for 'connections':
    # The 'connections' object gets all databases defined in settings.py
    database = db_mapping.get(target_app_label, "default")
    # Used only for syncing a duplicate database that mirrors the xfd_mini_dl schema
    if using:
        database = using
    LOGGER.info(
        "Synchronizing database schema for app '%s' in database '%s'...",
        target_app_label,
        database,
    )

    # Warning: Cursor automatically closes after use of 'with'
    with connections[database].schema_editor() as schema_editor:
        ordered_models = get_ordered_models(target_app_label)
        # Compute allowed table names from the models we are syncing.
        allowed_tables = {m._meta.db_table for m in ordered_models}
        for model in ordered_models:
            LOGGER.info("Processing model: %s", model.__name__)
            process_model(schema_editor, model, database, allowed_tables)

        LOGGER.info("Processing Many-to-Many tables...")
        process_m2m_tables(schema_editor, ordered_models, database)

        if target_app_label == "xfd_mini_dl":
            LOGGER.info("Ensuring GiST index exists on ip.ip...")
            with connections[database].cursor() as cursor:
                cursor.execute(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_indexes
                            WHERE tablename = 'ip' AND indexname = 'ip_ip_gist_idx'
                        ) THEN
                            EXECUTE 'CREATE INDEX ip_ip_gist_idx ON ip USING gist (ip inet_ops)';
                        END IF;
                    END
                    $$;
                """
                )

        cleanup_stale_tables(ordered_models, database)

    LOGGER.info("Database synchronization complete.")


def get_ordered_models(target_app_label):
    """
    Get models in dependency order to ensure foreign key constraints are respected.

    Only consider dependencies among models within the same app, and break cycles
    deterministically (alphabetically by model name).
    """
    # Get all models for the app and create a set for quick membership checks.
    models = [
        m for m in apps.get_app_config(target_app_label).get_models() if m._meta.managed
    ]
    model_set = set(models)

    # Build dependency graph, but only include dependencies to models within the app.
    dependencies = defaultdict(set)
    dependents = defaultdict(set)
    for model in models:
        for field in model._meta.get_fields():
            # Only add a dependency if the related model is in our app's set.
            if field.is_relation and field.related_model in model_set:
                dependencies[model].add(field.related_model)
                dependents[field.related_model].add(model)

    # Start with models that have no dependencies.
    ordered = []
    independent_models = deque([model for model in models if not dependencies[model]])

    while independent_models:
        model = independent_models.popleft()
        ordered.append(model)
        # Remove this model as a dependency from its dependents.
        for dependent in list(dependents[model]):
            dependencies[dependent].discard(model)
            dependents[model].discard(dependent)
            if not dependencies[dependent]:
                independent_models.append(dependent)

    # Any models not yet added are in a dependency cycle.
    remaining = [model for model in models if model not in ordered]
    if remaining:
        LOGGER.warning(
            "Circular dependencies detected among: %s",
            ", ".join(m.__name__ for m in remaining),
        )
        # Sort them deterministically (alphabetically) so that, for example, 'User' comes before 'Organization'
        remaining_sorted = sorted(remaining, key=lambda m: m.__name__)
        ordered.extend(remaining_sorted)

    return ordered


def process_model(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):
    """Process a single model: create or update its table."""
    table_name = model._meta.db_table

    with connections[database].cursor() as cursor:
        try:
            # Check if the table exists
            cursor.execute("SELECT to_regclass(%s);", [table_name])
            table_exists = cursor.fetchone()[0] is not None

            if table_exists:
                LOGGER.info("Updating table for model: %s", model.__name__)
                update_table(schema_editor, model, database, allowed_tables)
            else:
                LOGGER.info("Creating table for model: %s", model.__name__)
                schema_editor.create_model(model)

        except Exception as e:
            LOGGER.error("Error processing model %s: %s", model.__name__, e)


def process_m2m_tables(schema_editor: BaseDatabaseSchemaEditor, models, database):
    """Handle creation of Many-to-Many linking tables."""
    with connections[database].cursor() as cursor:
        for model in models:
            for field in model._meta.local_many_to_many:
                m2m_table_name = field.m2m_db_table()

                # Check if the M2M table exists
                cursor.execute("SELECT to_regclass('{}');".format(m2m_table_name))
                table_exists = cursor.fetchone()[0] is not None

                if not table_exists:
                    LOGGER.info("Creating Many-to-Many table: %s", m2m_table_name)
                    schema_editor.create_model(field.remote_field.through)
                else:
                    LOGGER.info(
                        "Many-to-Many table %s already exists. Skipping.",
                        m2m_table_name,
                    )


def index_exists_in_db(model_index, existing_defs):
    """
    Return True if an index with the same name or the same definition already exists.

    existing_defs is a list of (indexname, indexdef) from pg_indexes.
    """
    fields = [strip_quotes(f) for f in model_index.fields]
    condition = getattr(model_index, "condition", None)

    for name, definition in existing_defs:
        # Exact name match: definitely exists
        if name == model_index.name:
            return True

        # Match by same fields in the same order
        if all(f in definition for f in fields):
            if condition:
                if str(condition).lower() in definition.lower():
                    return True
            else:
                return True
    return False


def update_table(
    schema_editor: BaseDatabaseSchemaEditor, model, database, allowed_tables
):  # pylint: disable=R0915
    """Update an existing table for the given model. Ensure columns match fields."""
    table_name = model._meta.db_table
    db_fields = {field.column for field in model._meta.fields}

    with connections[database].cursor() as cursor:
        # Get existing columns
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s;",
            [table_name],
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        # Add missing columns
        missing_columns = db_fields - existing_columns
        for field in model._meta.fields:
            if field.column in missing_columns:
                if hasattr(field, "remote_field") and field.remote_field:
                    related_table = field.remote_field.model._meta.db_table
                    # If the related table isn't in allowed_tables or doesn't exist yet, skip adding this field.
                    if related_table not in allowed_tables or not table_exists_in_db(
                        related_table, database
                    ):
                        LOGGER.warning(
                            "Skipping addition of foreign key field '%s' on model '%s' because referenced table '%s' does not exist yet.",
                            field.column,
                            model.__name__,
                            related_table,
                        )
                        continue
                LOGGER.info(
                    "Adding column '%s' to table '%s'", field.column, table_name
                )
                schema_editor.add_field(model, field)

        # --- NEW: Sync nullability for existing columns ---
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
                        # Before trying SET NOT NULL, check if column already has NULLs
                        cursor.execute(
                            f"SELECT COUNT(*) FROM {safe_table_name} WHERE {safe_column_name} IS NULL;"  # nosec B608
                        )
                        null_count = cursor.fetchone()[0]
                        if null_count > 0:
                            LOGGER.warning(
                                "⚠️ Cannot set NOT NULL on %s.%s: %s row(s) contain NULL values. "
                                "Please clean up data manually.",
                                table_name,
                                field.column,
                                null_count,
                            )
                            continue  # skip ALTER
                        alter_sql = f"ALTER TABLE {safe_table_name} ALTER COLUMN {safe_column_name} SET NOT NULL;"
                    else:
                        alter_sql = f"ALTER TABLE {safe_table_name} ALTER COLUMN {safe_column_name} DROP NOT NULL;"

                    try:
                        cursor.execute(alter_sql)
                        LOGGER.info(
                            "Updated nullability of column '%s' in table '%s' to %s",
                            field.column,
                            table_name,
                            "NULL" if desired_nullable else "NOT NULL",
                        )
                    except Exception as e:
                        LOGGER.error(
                            "⚠️ Failed to update nullability of %s.%s: %s",
                            table_name,
                            field.column,
                            e,
                        )
        # Remove extra columns
        extra_columns = existing_columns - db_fields
        for column in extra_columns:
            LOGGER.info(
                "Removing extra column '%s' from table '%s'", column, table_name
            )
            try:
                safe_table_name = connections[database].ops.quote_name(table_name)
                safe_column_name = connections[database].ops.quote_name(column)
                query = "ALTER TABLE {} DROP COLUMN IF EXISTS {};".format(
                    safe_table_name, safe_column_name
                )
                cursor.execute(query)
            except Exception as e:
                LOGGER.error(
                    "Error dropping column '%s' from table '%s': %s",
                    column,
                    table_name,
                    e,
                )

        # Add missing indexes
        with connections[database].cursor() as idx_cursor:
            idx_cursor.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s;
            """,
                [table_name],
            )
            existing_defs = [  # pylint: disable=unnecessary-comprehension
                (name, definition) for name, definition in idx_cursor.fetchall()
            ]

        for model_index in model._meta.indexes:
            if not index_exists_in_db(model_index, existing_defs):
                try:
                    LOGGER.info(
                        "Adding index '%s' to table '%s'", model_index.name, table_name
                    )
                    schema_editor.add_index(model, model_index)
                except Exception as e:
                    LOGGER.error(
                        "Failed to add index '%s' on '%s': %s",
                        model_index.name,
                        table_name,
                        e,
                    )


def cleanup_stale_tables(models, database):
    """Remove tables that no longer correspond to any Django model or Many-to-Many relationship."""
    LOGGER.info("Checking for stale tables...")

    with connections[database].cursor() as cursor:
        model_tables = {model._meta.db_table for model in models if model._meta.managed}
        # [m for m in apps.get_app_config(target_app_label).get_models() if m._meta.managed]
        m2m_tables = {
            field.m2m_db_table()
            for model in models
            # if model._meta.managed
            for field in model._meta.local_many_to_many
        }
        expected_tables = model_tables.union(m2m_tables)

        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        existing_tables = {row[0] for row in cursor.fetchall()}

        # Get regular views
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public';
        """
        )
        regular_views = {row[0] for row in cursor.fetchall()}

        # Get materialized views
        cursor.execute(
            """
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'public';
        """
        )
        materialized_views = {row[0] for row in cursor.fetchall()}

        # Combine both
        all_views = regular_views.union(materialized_views)
        existing_tables = existing_tables - all_views
        stale_tables = existing_tables - expected_tables
        for table in stale_tables:
            LOGGER.info("Removing stale table: %s", table)
            try:
                # Use `quote_ident` to safely handle table names with special characters or reserved words
                cursor.execute(
                    "DROP TABLE {} CASCADE;".format(
                        connections[database].ops.quote_name(table)
                    )
                )
            except OperationalError as e:
                LOGGER.error("Error dropping stale table %s: %s", table, e)
            except WrongObjectType as e:
                LOGGER.error("Tried to drop a non table entity %s: %s", table, e)
            except ProgrammingError as e:
                LOGGER.error("Issue dropping entity %s: %s", table, e)


def drop_all_tables(app_label=None):
    """Drop all tables in the database. Used with `dangerouslyforce`."""
    allowed_labels = ["xfd_mini_dl", "xfd_api"]
    db_mapping = {
        "xfd_mini_dl": "mini_data_lake",
        "xfd_api": "default",
    }

    if app_label is None:
        raise ValueError(
            "The 'app_label' parameter is required to synchronize specific models."
        )

    if app_label not in allowed_labels:
        raise ValueError(
            "Invalid 'app_label' provided. Must be one of: {}.".format(
                ", ".join(allowed_labels)
            )
        )

    database = db_mapping.get(app_label, "default")
    LOGGER.info(
        "Resetting database schema for app '%s' in database '%s'...",
        app_label,
        database,
    )

    with connections[database].cursor() as cursor:
        try:
            # Drop all constraints first to avoid foreign key dependency issues
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
            cursor.execute(
                "GRANT ALL ON SCHEMA public TO {};".format(os.getenv("DB_USERNAME"))
            )
            cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        except Exception as e:
            LOGGER.error("Error resetting schema: %s", e)

    LOGGER.info("Database schema reset successfully.")
