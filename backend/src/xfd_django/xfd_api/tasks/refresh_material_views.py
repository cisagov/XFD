"""Lambda to refresh all materialized views in mini_data_lake."""

# Standard Python Libraries
import os

# Third-Party Libraries
import django
from django.db import connections

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()


def handler(event, context):
    """
    Refresh all materialized views in mini_data_lake.

    Uses CONCURRENTLY if the view has a unique index.
    """
    refreshed = []
    skipped = []

    try:
        with connections["mini_data_lake"].cursor() as cursor:
            # Get all materialized views in the current schema
            cursor.execute(
                """
                SELECT schemaname, matviewname
                FROM pg_matviews
                WHERE schemaname = current_schema()
            """
            )
            matviews = cursor.fetchall()

            for schemaname, matviewname in matviews:
                try:
                    # Check if the view has a unique index (required for CONCURRENTLY)
                    cursor.execute(
                        """
                        SELECT 1
                        FROM pg_index i
                        JOIN pg_class c ON c.oid = i.indrelid
                        WHERE c.relname = %s AND i.indisunique = TRUE
                        LIMIT 1
                    """,
                        [matviewname],
                    )
                    has_unique_index = cursor.fetchone() is not None

                    if has_unique_index:
                        cursor.execute(
                            'REFRESH MATERIALIZED VIEW CONCURRENTLY "{}"'.format(
                                matviewname
                            )
                        )
                    else:
                        cursor.execute(
                            'REFRESH MATERIALIZED VIEW "{}"'.format(matviewname)
                        )

                    refreshed.append(matviewname)
                except Exception as ve:
                    skipped.append({"view": matviewname, "error": str(ve)})

        return {
            "status_code": 200,
            "refreshed": refreshed,
            "skipped": skipped,
        }

    except Exception as e:
        return {"status_code": 500, "error": str(e)}
