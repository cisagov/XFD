"""Task to refresh or create all views/materialized views in mini_data_lake."""

# Standard Python Libraries
import logging
import os

# Third-Party Libraries
import django
from django.db import connections

# Import your existing view creation functions
from xfd_api.tasks.helpers.syncdb_helpers.create_db_views import (
    DOMAIN_MAT_VIEW_VERSION,
    DOMAIN_SEARCH_MAT_VIEW_VERSION,
    MAT_VW_COMBINED_VULNS_VERSION,
    VW_SERVICE_VERSION,
    create_domain_materialized_view,
    create_domain_search_mat_view,
    create_service_mat_view,
    create_vuln_materialized_views,
)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

LOGGER = logging.getLogger(__name__)

# Define your materialized views and their create functions
MATERIALIZED_VIEWS = [
    {
        "name": "mat_vw_domain",
        "create_fn": create_domain_materialized_view,
        "version": DOMAIN_MAT_VIEW_VERSION,
        "depends_on": [],
    },
    {
        "name": "mat_vw_service",
        "create_fn": create_service_mat_view,
        "version": VW_SERVICE_VERSION,
        "depends_on": [],
    },
    {
        "name": "mat_vw_combined_vulns",
        "create_fn": create_vuln_materialized_views,
        "version": MAT_VW_COMBINED_VULNS_VERSION,
        "depends_on": [],
    },
    {
        "name": "mat_vw_domain_search",
        "create_fn": create_domain_search_mat_view,
        "version": DOMAIN_SEARCH_MAT_VIEW_VERSION,
        "depends_on": [
            "mat_vw_domain",
            "mat_vw_service",
            "mat_vw_combined_vulns",
        ],
    },
]


def list_matview_versions(database="mini_data_lake"):
    """Print current materialized views and their version comments."""
    with connections[database].cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname AS matviewname,
                   obj_description(c.oid) AS comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'm'
              AND n.nspname = current_schema()
            ORDER BY matviewname;
            """
        )
        rows = cursor.fetchall()
        LOGGER.info("\nCurrent materialized views and versions:")
        for row in rows:
            name, comment = row
            version = "unknown"
            if comment and comment.startswith("version:"):
                version = comment.split("version:", 1)[1].strip()
            LOGGER.info("  %s → version: %s", name, version)


def view_exists(cursor, view_name, materialized=False):
    """Check if a view or materialized view exists."""
    if materialized:
        cursor.execute(
            """
            SELECT 1 FROM pg_matviews
            WHERE matviewname = %s AND schemaname = current_schema()
            """,
            [view_name],
        )
    else:
        cursor.execute(
            """
            SELECT 1 FROM pg_views
            WHERE viewname = %s AND schemaname = current_schema()
            """,
            [view_name],
        )
    return cursor.fetchone() is not None


def has_unique_index(cursor, matview_name):
    """Check if a materialized view has a unique index."""
    cursor.execute(
        """
        SELECT 1
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indrelid
        WHERE c.relname = %s AND i.indisunique = TRUE
        LIMIT 1
        """,
        [matview_name],
    )
    return cursor.fetchone() is not None


def get_matview_version(cursor, matview_name):
    """Fetch version comment from materialized view."""
    cursor.execute(
        """
        SELECT obj_description(c.oid)
        FROM pg_class c
        WHERE c.relname = %s AND c.relkind = 'm'
        """,
        [matview_name],
    )
    row = cursor.fetchone()
    if row and row[0] and row[0].startswith("version:"):
        return row[0].split(":", 1)[1].strip()
    return None


def handler(event):
    """Refresh or create key materialized views in mini_data_lake."""
    list_matview_versions()
    refreshed = []
    created = []
    errors = []

    try:
        with connections["mini_data_lake"].cursor() as cursor:
            deps = {v["name"]: set(v.get("depends_on", [])) for v in MATERIALIZED_VIEWS}
            rev_deps = {n: set() for n in deps}
            for n, dset in deps.items():
                for d in dset:
                    rev_deps[d].add(n)

            def mv_exists(name):
                return view_exists(cursor, name, materialized=True)

            def mv_version(name):
                return get_matview_version(cursor, name)

            # Which MVs are going to be rebuilt (missing or version bump)?
            to_rebuild = {
                v["name"]
                for v in MATERIALIZED_VIEWS
                if (not mv_exists(v["name"])) or (mv_version(v["name"]) != v["version"])
            }

            # Any dependent of a to_rebuild MV must be dropped first.
            to_drop = set()
            stack = list(to_rebuild)
            while stack:
                cur = stack.pop()
                for child in rev_deps.get(cur, ()):
                    if child not in to_drop:
                        to_drop.add(child)
                        stack.append(child)

            # Drop dependents first (reverse of your list; your list is already base->dependent)
            for v in reversed(MATERIALIZED_VIEWS):
                name = v["name"]
                if name in to_drop and mv_exists(name):
                    LOGGER.info("Pre-dropping dependent MV %s ...", name)
                    cursor.execute(f"DROP MATERIALIZED VIEW IF EXISTS {name};")

            for view in MATERIALIZED_VIEWS:
                try:
                    name = view["name"]
                    create_fn = view["create_fn"]
                    expected_version = view["version"]

                    if view_exists(cursor, name, materialized=True):
                        current_version = get_matview_version(cursor, name)
                        if current_version != expected_version:
                            # View definition changed → recreate it
                            create_fn("mini_data_lake")
                            created.append("{} (version updated)".format(name))
                        else:
                            # Version matches → refresh
                            if has_unique_index(cursor, name):
                                LOGGER.info("Refreshing view %s", name)
                                cursor.execute(
                                    "REFRESH MATERIALIZED VIEW CONCURRENTLY {};".format(
                                        name
                                    )
                                )
                            else:
                                cursor.execute(
                                    "REFRESH MATERIALIZED VIEW {};".format(name)
                                )
                            refreshed.append(name)
                    else:
                        # View does not exist → create
                        create_fn("mini_data_lake")
                        created.append(name)

                except Exception as e:
                    errors.append({"view": name, "error": str(e)})

        result = {
            "status_code": 200,
            "refreshed": refreshed,
            "created": created,
            "errors": errors,
        }
        LOGGER.info(result)
        return result

    except Exception as e:
        return {"status_code": 500, "error": str(e)}
