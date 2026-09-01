"""Query Databricks Helpers."""

# Standard Python Libraries
import datetime
import json
import logging
import os
import time
from typing import Any, List, Optional, Tuple

# Third-Party Libraries
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (
    Disposition,
    Format,
    StatementParameterListItem,
    StatementState,
)
from xfd_api.tasks.utils.cloudwatch_metrics import (
    cloudwatch_metric,
    emit_databricks_metric,
)
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

# --- Databricks Shared Client Management ---
_CLIENT = None

_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
_CATALOG = os.environ.get("DATABRICKS_CATALOG") or None
_SCHEMA = os.environ.get("DATABRICKS_SCHEMA") or None

# Max time to wait between poll attempts, and how many attempts before giving up.
_POLL_INTERVAL_SECONDS = 5
_MAX_POLL_ATTEMPTS = 120  # ~10 minutes total at 5s intervals


def _get_client():
    """Create or return a reusable Databricks WorkspaceClient instance."""
    global _CLIENT
    if _CLIENT is None:
        LOGGER.info("[Databricks] Initializing WorkspaceClient...")
        _CLIENT = WorkspaceClient(
            host="https://{}".format(os.environ.get("DATABRICKS_SERVER_HOSTNAME")),
            client_id=os.environ.get("DATABRICKS_CLIENT_ID"),
            client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET"),
        )
    return _CLIENT


def _reset_client():
    """Safely clear out a stale client so the next call rebuilds it."""
    global _CLIENT
    _CLIENT = None


def _infer_statement_param(name: str, value: Any) -> StatementParameterListItem:
    """Best-effort mapping of a Python value to a Databricks named statement parameter.

    Type strings follow Databricks SQL type names (INT, STRING, TIMESTAMP,
    BOOLEAN, DECIMAL(p,s), ...). If a value's type isn't recognized here it's
    passed as a plain string, matching Databricks' own default when no `type`
    is given.
    """
    if value is None:
        return StatementParameterListItem(name=name, value=None)
    if isinstance(value, bool):
        return StatementParameterListItem(name=name, value=str(value), type="BOOLEAN")
    if isinstance(value, int):
        return StatementParameterListItem(name=name, value=str(value), type="INT")
    if isinstance(value, float):
        return StatementParameterListItem(name=name, value=str(value), type="DOUBLE")
    if isinstance(value, (datetime.datetime, datetime.date)):
        # MODIFIED: naive datetimes are treated as UTC explicitly before
        # calling isoformat(). to_utc_naive() (datetime_utils.py) deliberately
        # strips tzinfo after converting to UTC - that contract made sense for
        # the old databricks-sql-connector's typed-param binding, but a naive
        # .isoformat() string sent as a Databricks TIMESTAMP parameter has no
        # UTC offset in it, leaving it ambiguous whether the warehouse
        # interprets it as UTC or session-local time. This is the one place
        # that actually serializes datetimes for the API, so the UTC
        # assumption is made explicit right here rather than changing
        # to_utc_naive()'s contract for every other caller.
        if isinstance(value, datetime.datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return StatementParameterListItem(
            name=name, value=value.isoformat(), type="TIMESTAMP"
        )
    return StatementParameterListItem(name=name, value=str(value))


def _build_parameters(
    params: Optional[List[Any]],
) -> Optional[List[StatementParameterListItem]]:
    """Convert a positional params list into :p0, :p1, ... named parameters.

    Caller's query text must already reference :p0, :p1, ... in the same
    order as this list - params[i] always maps to marker :p{i}.
    """
    if not params:
        return None
    return [_infer_statement_param(f"p{i}", value) for i, value in enumerate(params)]


def _fetch_all_rows(client, statement_id: str, first_result) -> List[list]:
    """Walk every INLINE/JSON_ARRAY result chunk and concatenate all rows.

    The first chunk comes back attached to the execute_statement/get_statement
    response itself (result.chunk_index == 0). Subsequent chunks (if the
    result spans more than one) are fetched by index via
    get_statement_result_chunk_n() until next_chunk_index is absent.
    """
    if first_result is None:
        return []
    rows = list(first_result.data_array or [])
    next_index = first_result.next_chunk_index
    while next_index is not None:
        chunk = client.statement_execution.get_statement_result_chunk_n(
            statement_id, next_index
        )
        rows.extend(chunk.data_array or [])
        next_index = chunk.next_chunk_index
    return rows


@cloudwatch_metric()
def query_databricks(query, params=None):
    """Execute a query on Databricks via the Statement Execution API and return results as list of dicts.

    IMPORTANT: `query` must use Databricks named parameter markers (:p0, :p1,
    ...) - NOT `?`. See module-level note at the top of this file for why.
    `params` is still passed positionally as a list, matching every existing
    call site; params[i] is bound to marker :p{i}.
    """
    query_name = str(query)[:120].replace("\n", " ")
    rows_returned = 0

    for attempt in range(5):  # retry up to 5 times
        start = time.perf_counter()
        success = True
        try:
            client = _get_client()
            parameter_items = _build_parameters(params)

            # Matches the working pattern from the verified test script:
            # wait_timeout="0s" (don't block server-side) + explicit client-side
            # polling loop via get_statement(), rather than relying on the
            # server's synchronous-with-fallback behavior at a longer timeout.
            response = client.statement_execution.execute_statement(
                statement=query,
                warehouse_id=_WAREHOUSE_ID,
                parameters=parameter_items,
                catalog=_CATALOG,
                schema=_SCHEMA,
                wait_timeout="0s",
                disposition=Disposition.INLINE,
                format=Format.JSON_ARRAY,
            )

            statement_id = response.statement_id
            state = response.status.state

            poll_attempt = 0
            while state in (StatementState.PENDING, StatementState.RUNNING):
                poll_attempt += 1
                if poll_attempt > _MAX_POLL_ATTEMPTS:
                    raise QueryError(
                        SCAN_NAME,
                        f"Statement {statement_id} did not complete within "
                        f"{_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SECONDS}s",
                    )
                time.sleep(_POLL_INTERVAL_SECONDS)
                response = client.statement_execution.get_statement(statement_id)
                state = response.status.state

            if state != StatementState.SUCCEEDED:
                error = response.status.error
                error_message = getattr(error, "message", None) if error else None
                raise QueryError(
                    SCAN_NAME,
                    f"Statement {statement_id} ended in state {state}: "
                    f"{error_message or 'no error message provided'}",
                )

            columns = [c.name for c in response.manifest.schema.columns]
            raw_rows = _fetch_all_rows(client, statement_id, response.result)
            dict_results = [dict(zip(columns, row)) for row in raw_rows]

            rows_returned = len(dict_results)
            return dict_results  # success -> return immediately

        except QueryError:
            # Already a terminal, well-formed error (bad SQL, statement failed,
            # timed out waiting) - don't retry, don't re-wrap.
            success = False
            raise

        except Exception as e:
            success = False
            # Best-effort heuristic for transient/retryable errors, mirroring
            # the previous connector-based version. The exact exception types
            # raised by databricks-sdk for network/auth-token issues were not
            # verified against a live SDK install here - treat this check as
            # approximate and revisit once real error behavior is observed.
            if "connection" in str(e).lower() or "timeout" in str(e).lower():
                sleep = 2**attempt
                LOGGER.warning(
                    "[Databricks] Transient error (%s). Retrying in %ss (attempt %d/5)",
                    e,
                    sleep,
                    attempt + 1,
                )
                time.sleep(sleep)
                _reset_client()
                continue  # retry loop
            raise QueryError(SCAN_NAME, str(e)) from e

        finally:
            duration = time.perf_counter() - start
            emit_databricks_metric(query_name, duration, rows_returned, success)
            LOGGER.info(
                "[Databricks] [%0.3fs] [%d rows] success=%s",
                duration,
                rows_returned,
                success,
            )

    # if we exhausted retries
    raise QueryError(SCAN_NAME, "Max Databricks retries exceeded")


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


def fetch_from_databricks(query):
    """Fetch data from Databricks and log execution time."""
    if IS_LOCAL:
        data_set = detect_data_set(query)
        return load_test_data(data_set)
    try:
        start_time = datetime.datetime.now()
        result = query_databricks(query)
        end_time = datetime.datetime.now()
        duration_seconds = (end_time - start_time).total_seconds()
        LOGGER.info(
            f"[Databricks] [{duration_seconds}s] [{len(result)} records] {query}"
        )
        return result
    except Exception as e:
        LOGGER.info("Error fetching data from Databricks: %s", e)
        LOGGER.info("Erroneous query: %s", query)
        return []


def fetch_from_databricks_with_params(query: str, params: Tuple[Any, ...]):
    """Fetch data from Databricks with parameters.

    `query` must use :p0, :p1, ... markers matching the order of `params` -
    see query_databricks() docstring.
    """
    if IS_LOCAL:
        data_set = detect_data_set(query)
        return load_test_data(data_set)
    try:
        result = query_databricks(query, params=params)
        return result
    except Exception as e:
        LOGGER.info("Error fetching data from Databricks: %s", e)
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
    Keyset pagination over a fixed window with ORDER BY (time_col, _id).

    Databricks equivalent of the Redshift version's `owner = ANY(%s)` filter,
    expressed as an `owner IN (:pN, :pN, ...)` clause - the Statement
    Execution API has no array-parameter equivalent to Postgres' ANY(array).
    """
    last_time = None
    last_id = None
    start_param = to_utc_naive(start_dt)
    end_param = to_utc_naive(end_dt)

    q_time = f"`{time_col}`"
    q_id = "`_id`"

    while True:
        params: List[Any] = []

        def add_param(value):
            """Append a value and return its :pN marker, keeping params/markers in sync."""
            params.append(value)
            return f":p{len(params) - 1}"

        where = f"WHERE {q_time} >= {add_param(start_param)} AND {q_time} < {add_param(end_param)}"

        if last_time is not None and last_id is not None:
            gt_marker = add_param(last_time)
            eq_marker = add_param(last_time)
            id_marker = add_param(last_id)
            where += (
                f" AND ({q_time} > {gt_marker} "
                f"OR ({q_time} = {eq_marker} AND {q_id} > {id_marker}))"
            )

        if owners:
            placeholders = ", ".join(add_param(owner) for owner in owners)
            where += f" AND owner IN ({placeholders})"

        limit_marker = add_param(chunk_size)

        query = f"""
            SELECT *
            FROM {table}
            {where}
            ORDER BY {q_time}, {q_id}
            LIMIT {limit_marker}
        """  # nosec B608

        chunk = query_databricks(query, params=params)
        if not chunk:
            break

        last_row = chunk[-1]
        last_time = last_row[time_col]
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

    Filters by multiple org acronyms using an IN clause, built with named
    :pN parameter markers (see fetch_in_chunks_keyset_frozen's note on why -
    the Statement Execution API doesn't support `?` or array parameters).
    """
    last_time = None
    last_id = None
    start_param = to_utc_naive(start_dt)
    end_param = to_utc_naive(end_dt)

    # Handle schema-qualified table names (e.g. "catalog.schema.table")
    table_ident = ".".join(f"`{part}`" for part in table.split("."))

    q_time = f"`{time_col}`"
    q_id = "`_id`"

    while True:
        params: List[Any] = []

        def add_param(value):
            """Append a value and return its :pN marker, keeping params/markers in sync."""
            params.append(value)
            return f":p{len(params) - 1}"

        where_clauses = [
            f"{q_time} >= {add_param(start_param)}",
            f"{q_time} < {add_param(end_param)}",
        ]

        if last_time is not None and last_id is not None:
            gt_marker = add_param(last_time)
            eq_marker = add_param(last_time)
            id_marker = add_param(last_id)
            where_clauses.append(
                f"({q_time} > {gt_marker} OR ({q_time} = {eq_marker} AND {q_id} > {id_marker}))"
            )

        if org_acronyms:
            placeholders = ", ".join(add_param(acronym) for acronym in org_acronyms)
            where_clauses.append(f"owner IN ({placeholders})")

        where_sql = " AND ".join(where_clauses)
        limit_marker = add_param(chunk_size)

        query = f"""
            SELECT *
            FROM {table_ident}
            WHERE {where_sql}
            ORDER BY {q_time}, {q_id}
            LIMIT {limit_marker}
        """  # nosec B608

        chunk = query_databricks(query, params=params)
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
