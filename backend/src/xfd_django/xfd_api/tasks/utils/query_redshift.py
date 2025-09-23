"""Query Redshift Helpers."""

# Standard Python Libraries
import datetime
import json
import logging
import os
from typing import Any, Tuple

# Third-Party Libraries
import psycopg2
from xfd_api.tasks.utils.datetime_utils import to_utc_naive
from xfd_api.utils.scan_utils.alerting import QueryError

SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)


def query_redshift(query, params=None):
    """Execute a query on Redshift and return results as a list of dictionaries."""
    conn = psycopg2.connect(
        dbname=os.environ.get("REDSHIFT_DATABASE"),
        user=os.environ.get("REDSHIFT_USER"),
        password=os.environ.get("REDSHIFT_PASSWORD"),
        host=os.environ.get("REDSHIFT_HOST"),
        port=5439,
    )

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        return [dict(row) for row in results]
    except Exception as e:
        raise QueryError(SCAN_NAME, str(e)) from e
    finally:
        cursor.close()
        conn.close()


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

    start_time = datetime.datetime.now()
    try:
        result = query_redshift(query, params=params)
        duration_seconds = (datetime.datetime.now() - start_time).total_seconds()
        # Do NOT log params to avoid leaking sensitive values
        LOGGER.info(
            "[Redshift] [%.3fs] [%s records] %s", duration_seconds, len(result), query
        )
        return result
    except Exception as e:
        LOGGER.info("Error fetching data from Redshift: %s", e)
        LOGGER.info("Erroneous query: %s", query)
        return []


def fetch_in_chunks_keyset_frozen(
    table: str, time_col: str, start_dt, end_dt, chunk_size: int = 500_000
):
    """
    Keyset pagination over a fixed window with ORDER BY ("time_col", "_id").

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

        if last_time is not None and last_id is not None:
            where += f" AND ({q_time} > %s OR ({q_time} = %s AND {q_id} > %s))"
            params.extend([last_time, last_time, last_id])

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
        last_time = last_row[time_col]  # keep dict access unquoted
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
