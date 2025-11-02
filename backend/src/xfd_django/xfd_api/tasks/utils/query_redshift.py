"""Query Redshift Helpers."""

# Standard Python Libraries
import datetime
import json
import logging
import os
import time
from typing import Any, Tuple

# Third-Party Libraries
import psycopg2
from psycopg2 import sql
from psycopg2.pool import SimpleConnectionPool
from xfd_api.tasks.utils.datetime_utils import to_utc_naive
from xfd_api.utils.scan_utils.alerting import QueryError

SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="/tmp/vuln_scanning_sync.log",  # nosec B108
)
LOGGER = logging.getLogger(__name__)

# --- Connection pool (per process / worker) ---
_POOL = None


def _get_pool():
    """Create or return a singleton connection pool per worker."""
    global _POOL
    if _POOL is None:
        LOGGER.info("[Redshift] Initializing connection pool...")
        _POOL = SimpleConnectionPool(
            minconn=1,
            maxconn=2,  # allow a couple concurrent cursors per process
            dbname=os.environ.get("REDSHIFT_DATABASE"),
            user=os.environ.get("REDSHIFT_USER"),
            password=os.environ.get("REDSHIFT_PASSWORD"),
            host=os.environ.get("REDSHIFT_HOST"),
            port=5439,
            connect_timeout=10,
        )
    return _POOL


def query_redshift(query, params=None):
    """Execute a query on Redshift and return results as list of dicts."""
    pool = _get_pool()
    rows_returned = 0

    for attempt in range(5):  # retry up to 5 times
        conn = None
        cursor = None
        start = time.perf_counter()
        success = True
        try:
            conn = pool.getconn()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            rows_returned = len(results)
            return [dict(row) for row in results]  # ✅ success -> return immediately

        except psycopg2.OperationalError as e:
            success = False
            if "Connection refused" in str(e) or "terminating connection" in str(e):
                sleep = 2**attempt
                LOGGER.warning(
                    "[Redshift] Connection error (%s). Retrying in %ss (attempt %d/5)",
                    e,
                    sleep,
                    attempt + 1,
                )
                time.sleep(sleep)
                # drop the bad connection
                if conn:
                    pool.putconn(conn, close=True)
                _reset_pool()
                continue  # ✅ actually retry
            raise QueryError(SCAN_NAME, str(e)) from e

        except Exception as e:
            success = False
            raise QueryError(SCAN_NAME, str(e)) from e

        finally:
            duration = time.perf_counter() - start
            LOGGER.info(
                "[Redshift] [%0.3fs] [%d rows] success=%s",
                duration,
                rows_returned,
                success,
            )
            if cursor:
                cursor.close()
            if conn:
                pool.putconn(conn)
    # if we exhausted retries
    raise QueryError(SCAN_NAME, "Max Redshift retries exceeded")


def _reset_pool():
    """Safely reset the global connection pool."""
    global _POOL
    if _POOL:
        _POOL.closeall()

    _POOL = None


def detect_data_set(query):
    """Detect the data set from the query."""
    if "requests" in query:
        return "requests"
    if "vuln_scans" in query:
        return "vuln_scan"
    if "hosts" in query:
        return "hosts"
    if "tickets" in query:
        return "tickets"
    if "port_scans" in query:
        return "port_scans"
    return None


def fetch_from_redshift(query):
    """Fetch data from Redshift and log execution time."""
    if IS_LOCAL:
        data_set = detect_data_set(query)
        return load_test_data(data_set)
    try:
        start_time = datetime.datetime.now()
        result = query_redshift(query)
        end_time = datetime.datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        LOGGER.info(f"[Redshift] [{duration_seconds}s] [{len(result)} records] {query}")
        return result
    except Exception as e:
        LOGGER.info("Error fetching data from Redshift: %s", e)
        LOGGER.info("Erroneous query: %s", query)
        return []


def fetch_from_redshift_with_params(query: str, params: Tuple[Any, ...]):
    """
    Fetch data from Redshift with parameters and log execution time.

    Mirrors fetch_from_redshift() but forwards params to query_redshift().
    """
    if IS_LOCAL:
        data_set = detect_data_set(query)
        return load_test_data(data_set)
    try:
        result = query_redshift(query, params=params)
        return result
    except Exception as e:
        LOGGER.info("Error fetching data from Redshift: %s", e)
        LOGGER.info("Erroneous query: %s", query)
        return []


def fetch_in_chunks_keyset_frozen(
    table: str,
    time_col: str,
    start_dt,
    end_dt,
    chunk_size: int = 500_000,
    owners: list[str] | None = None,
):
    """
    Keyset pagination over a fixed window with ORDER BY ("time_col", "_id").

    Uses = ANY(array) for owner filtering if owners are provided.
    Quotes identifiers so Redshift doesn't parse `time` as a type.
    """
    last_time = None
    last_id = None
    start_param = to_utc_naive(start_dt)
    end_param = to_utc_naive(end_dt)

    # Quote identifiers
    q_time = f'"{time_col}"'
    q_id = '"_id"'

    while True:
        where = f"WHERE {q_time} >= %s AND {q_time} < %s"
        params = [start_param, end_param]

        # Add keyset pagination if needed
        if last_time is not None and last_id is not None:
            where += f" AND ({q_time} > %s OR ({q_time} = %s AND {q_id} > %s))"
            params.extend([last_time, last_time, last_id])

        # Add org filtering if owners provided
        if owners:
            where += " AND owner = ANY(%s)"
            params.append(
                owners
            )  # pass list directly, psycopg2/Redshift turns into array

        query = f"""
            SELECT *
            FROM {table}
            {where}
            ORDER BY {q_time}, {q_id}
            LIMIT {chunk_size}
        """  # nosec B608

        chunk = query_redshift(query, params=params)
        if not chunk:
            break

        last_row = chunk[-1]
        last_time = last_row[time_col]  # dict access, not quoted
        last_id = str(last_row["_id"])

        yield chunk


def fetch_in_chunks_keyset_frozen_bulk(
    table: str,
    time_col: str,
    start_dt,
    end_dt,
    chunk_size: int = 500_000,
    org_acronyms: list[str] | None = None,
):
    """
    Keyset pagination over a fixed window with ORDER BY (time_col, _id).

    Filters by multiple org acronyms using an IN clause.
    Uses psycopg2.sql for safe identifier handling and parameterized values.
    """
    last_time = None
    last_id = None
    start_param = to_utc_naive(start_dt)
    end_param = to_utc_naive(end_dt)

    while True:
        # Build WHERE clause dynamically but safely
        where_clauses = []
        params = [start_param, end_param]

        # Base window
        where_clauses.append(sql.SQL("{} >= %s").format(sql.Identifier(time_col)))
        where_clauses.append(sql.SQL("{} < %s").format(sql.Identifier(time_col)))

        # Keyset pagination
        if last_time is not None and last_id is not None:
            where_clauses.append(
                sql.SQL("({} > %s OR ({} = %s AND {} > %s))").format(
                    sql.Identifier(time_col),
                    sql.Identifier(time_col),
                    sql.Identifier("_id"),
                )
            )
            params.extend([last_time, last_time, last_id])

        # Org filter
        if org_acronyms:
            # Generate placeholders for each org acronym
            placeholders = sql.SQL(", ").join(sql.Placeholder() * len(org_acronyms))
            where_clauses.append(sql.SQL("owner IN ({})").format(placeholders))
            params.extend(org_acronyms)

        # Combine WHERE clauses
        where_sql = sql.SQL(" AND ").join(where_clauses)

        # Handle schema-qualified table names
        if "." in table:
            schema, table_name = table.split(".", 1)
            table_ident = sql.SQL(".").join(
                [sql.Identifier(schema), sql.Identifier(table_name)]
            )
        else:
            table_ident = sql.Identifier(table)

        # Build full query
        query_sql = sql.SQL(
            "SELECT * FROM {table} WHERE {where} ORDER BY {time_col}, {id_col} LIMIT %s"
        ).format(
            table=table_ident,
            where=where_sql,
            time_col=sql.Identifier(time_col),
            id_col=sql.Identifier("_id"),
        )
        params.append(chunk_size)

        # Execute query
        chunk = query_redshift(query_sql, params=params)

        if not chunk:
            break

        last_row = chunk[-1]
        last_time = last_row[time_col]
        last_id = str(last_row["_id"])

        yield chunk


# Used for loading test data from file for vuln_scans, port_scans, hosts, tickets
def load_test_data(data_set: str) -> list:
    """Load test data from local files for scanning simulations.

    Args:
        data_set (str): The type of data set to load (e.g., "requests", "vuln_scan").

    Returns:
        list: The parsed JSON data from the file.

    Raises:
        ValueError: If an unknown data_set is provided.
        FileNotFoundError: If the specified file does not exist.
    """
    file_paths = {
        "requests": "~/Downloads/requests_full_redshift.json",
        "vuln_scan": "~/Downloads/vuln_scan_sample.json",
        "port_scans": "~/Downloads/port_scans_sample.json",
        "hosts": "~/Downloads/hosts_sample.json",
        "tickets": "~/Downloads/tickets_sample_new.json",
    }

    file_path = file_paths.get(data_set)

    if file_path is None:
        raise ValueError(f"Unknown data set: {data_set}")

    expanded_path = os.path.expanduser(file_path)

    if not os.path.exists(expanded_path):
        raise FileNotFoundError(f"Test data file not found: {expanded_path}")

    with open(expanded_path, encoding="utf-8") as file:
        return json.load(file)
