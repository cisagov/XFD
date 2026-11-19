"""Query Databricks Helpers."""

# Standard Python Libraries
import datetime
import json
import logging
import os
import random
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
import requests
from xfd_api.tasks.utils.cloudwatch_metrics import (
    cloudwatch_metric,
    emit_databricks_metric,
)
from xfd_api.tasks.utils.datetime_utils import to_utc_naive
from xfd_api.utils.scan_utils.alerting import QueryError

SCAN_NAME = "VulnScanningSync"
IS_LOCAL = os.getenv("IS_LOCAL")

LOGGER = logging.getLogger(__name__)

# --- Databricks Shared Client Management ---
_CLIENT = None

_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
_CATALOG = os.environ.get("DATABRICKS_CATALOG") or None
_SCHEMA = os.environ.get("DATABRICKS_SCHEMA") or None

# --- Databricks Retry and Timeout Configuration ---
#
# Defaults preserve the prior behavior as closely as practical while adding
# retries for external-result downloads and configurable settings.

DATABRICKS_MAX_RETRIES = int(os.getenv("DATABRICKS_MAX_RETRIES", "5"))

DATABRICKS_RETRY_BASE_SECONDS = float(os.getenv("DATABRICKS_RETRY_BASE_SECONDS", "2"))

DATABRICKS_RETRY_MAX_SECONDS = float(os.getenv("DATABRICKS_RETRY_MAX_SECONDS", "30"))

DATABRICKS_EXTERNAL_LINK_TIMEOUT_SECONDS = int(
    os.getenv("DATABRICKS_EXTERNAL_LINK_TIMEOUT_SECONDS", "120")
)

DATABRICKS_POLL_INTERVAL_SECONDS = int(
    os.getenv("DATABRICKS_POLL_INTERVAL_SECONDS", "5")
)

DATABRICKS_MAX_POLL_ATTEMPTS = int(os.getenv("DATABRICKS_MAX_POLL_ATTEMPTS", "120"))

_POLL_INTERVAL_SECONDS = DATABRICKS_POLL_INTERVAL_SECONDS
_MAX_POLL_ATTEMPTS = DATABRICKS_MAX_POLL_ATTEMPTS


def _get_client():
    """Create or return a reusable Databricks WorkspaceClient instance."""
    global _CLIENT

    if _CLIENT is None:
        server_hostname = os.environ.get("DATABRICKS_SERVER_HOSTNAME")
        client_id = os.environ.get("DATABRICKS_CLIENT_ID")
        client_secret = os.environ.get("DATABRICKS_CLIENT_SECRET")

        missing = [
            name
            for name, value in (
                ("DATABRICKS_SERVER_HOSTNAME", server_hostname),
                ("DATABRICKS_CLIENT_ID", client_id),
                ("DATABRICKS_CLIENT_SECRET", client_secret),
                ("DATABRICKS_WAREHOUSE_ID", _WAREHOUSE_ID),
            )
            if not value
        ]

        if missing:
            raise QueryError(
                SCAN_NAME,
                "Missing required Databricks environment variable(s): "
                + ", ".join(missing),
            )

        LOGGER.info("[Databricks] Initializing WorkspaceClient.")

        _CLIENT = WorkspaceClient(
            host=f"https://{server_hostname}",
            client_id=client_id,
            client_secret=client_secret,
        )

    return _CLIENT


def _reset_client():
    """Clear the cached Databricks client so the next call creates a new one."""
    global _CLIENT
    _CLIENT = None


def _retry_delay_seconds(attempt: int) -> float:
    """Calculate exponential-backoff delay with bounded jitter."""
    delay = min(
        DATABRICKS_RETRY_MAX_SECONDS,
        DATABRICKS_RETRY_BASE_SECONDS * (2 ** (attempt - 1)),
    )

    # Add up to 25% jitter so concurrent workers do not retry together.
    return delay + random.uniform(0, delay * 0.25)


def _is_retryable_databricks_error(error: Exception) -> bool:
    """Return True when an error is likely transient and safe to retry."""
    if isinstance(
        error,
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.Timeout,
        ),
    ):
        return True

    if isinstance(error, requests.exceptions.HTTPError):
        response = error.response
        status_code = response.status_code if response is not None else None
        return status_code in {408, 425, 429, 500, 502, 503, 504}

    message = str(error).lower()

    retryable_markers = (
        "connection reset",
        "connection aborted",
        "connection refused",
        "connection error",
        "connect timeout",
        "read timeout",
        "timed out",
        "temporarily unavailable",
        "service unavailable",
        "gateway timeout",
        "bad gateway",
        "internal server error",
        "too many requests",
        "rate limit",
        "http 408",
        "http 429",
        "http 500",
        "http 502",
        "http 503",
        "http 504",
        "status code 408",
        "status code 429",
        "status code 500",
        "status code 502",
        "status code 503",
        "status code 504",
    )

    return any(marker in message for marker in retryable_markers)


def _infer_statement_param(name: str, value: Any) -> StatementParameterListItem:
    """Map a Python value to a Databricks named statement parameter."""
    if value is None:
        return StatementParameterListItem(name=name, value=None)

    if isinstance(value, bool):
        return StatementParameterListItem(
            name=name,
            value=str(value),
            type="BOOLEAN",
        )

    if isinstance(value, int):
        return StatementParameterListItem(
            name=name,
            value=str(value),
            type="INT",
        )

    if isinstance(value, float):
        return StatementParameterListItem(
            name=name,
            value=str(value),
            type="DOUBLE",
        )

    if isinstance(value, (datetime.datetime, datetime.date)):
        if isinstance(value, datetime.datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)

        return StatementParameterListItem(
            name=name,
            value=value.isoformat(),
            type="TIMESTAMP",
        )

    return StatementParameterListItem(
        name=name,
        value=str(value),
        type="STRING",
    )


def _build_parameters(
    params: Optional[List[Any]],
) -> Optional[List[StatementParameterListItem]]:
    """Convert positional values to Databricks named :p0, :p1 parameters."""
    if not params:
        return None

    return [_infer_statement_param(f"p{i}", value) for i, value in enumerate(params)]


def _download_external_rows(external_links) -> List[list]:
    """Download Databricks external result chunks with bounded retries."""
    rows: List[list] = []

    for link_info in external_links or []:
        external_link = link_info.external_link

        for attempt in range(1, DATABRICKS_MAX_RETRIES + 1):
            try:
                response = requests.get(
                    external_link,
                    timeout=DATABRICKS_EXTERNAL_LINK_TIMEOUT_SECONDS,
                )
                response.raise_for_status()

                chunk_rows = response.json()

                if not isinstance(chunk_rows, list):
                    raise ValueError(
                        "Expected JSON_ARRAY response from Databricks external "
                        f"link, received {type(chunk_rows).__name__}."
                    )

                rows.extend(chunk_rows)
                break

            except Exception as error:
                should_retry = (
                    _is_retryable_databricks_error(error)
                    and attempt < DATABRICKS_MAX_RETRIES
                )

                if not should_retry:
                    raise QueryError(
                        SCAN_NAME,
                        "Unable to download Databricks external result chunk "
                        f"after {attempt} attempt(s): {error}",
                    ) from error

                delay = _retry_delay_seconds(attempt)

                LOGGER.warning(
                    "[Databricks] External result download failed; retrying | "
                    "attempt=%d | max_attempts=%d | delay_seconds=%.2f | "
                    "error=%s",
                    attempt,
                    DATABRICKS_MAX_RETRIES,
                    delay,
                    error,
                )

                time.sleep(delay)

    return rows


def _fetch_all_rows(client, statement_id: str, first_result) -> List[list]:
    """Fetch all Databricks result chunks from inline or external links."""
    if first_result is None:
        return []

    rows: List[list] = []

    if first_result.data_array:
        rows.extend(first_result.data_array)

    if first_result.external_links:
        rows.extend(_download_external_rows(first_result.external_links))

    next_index = first_result.next_chunk_index

    while next_index is not None:
        chunk = client.statement_execution.get_statement_result_chunk_n(
            statement_id,
            next_index,
        )

        if chunk.data_array:
            rows.extend(chunk.data_array)

        if chunk.external_links:
            rows.extend(_download_external_rows(chunk.external_links))

        next_index = chunk.next_chunk_index

    return rows


@cloudwatch_metric()
def query_databricks(query, params=None):
    """Execute a Databricks statement and return results as dictionaries."""
    query_name = str(query)[:120].replace("\n", " ")
    rows_returned = 0
    last_error = None

    for attempt in range(1, DATABRICKS_MAX_RETRIES + 1):
        started_at = time.perf_counter()
        success = True

        try:
            client = _get_client()
            parameter_items = _build_parameters(params)

            response = client.statement_execution.execute_statement(
                statement=query,
                warehouse_id=_WAREHOUSE_ID,
                parameters=parameter_items,
                catalog=_CATALOG,
                schema=_SCHEMA,
                wait_timeout="0s",
                disposition=Disposition.EXTERNAL_LINKS,
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
                        f"Databricks statement {statement_id} did not complete "
                        f"within {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SECONDS}s.",
                    )

                time.sleep(_POLL_INTERVAL_SECONDS)

                response = client.statement_execution.get_statement(statement_id)
                state = response.status.state

            if state != StatementState.SUCCEEDED:
                error = response.status.error
                error_message = getattr(error, "message", None) if error else None

                raise QueryError(
                    SCAN_NAME,
                    f"Databricks statement {statement_id} ended in state "
                    f"{state}: {error_message or 'no error message provided'}",
                )

            columns = [column.name for column in response.manifest.schema.columns]
            raw_rows = _fetch_all_rows(client, statement_id, response.result)

            dict_results = [dict(zip(columns, row)) for row in raw_rows]
            rows_returned = len(dict_results)

            return dict_results

        except QueryError:
            success = False
            raise

        except Exception as error:
            success = False
            last_error = error

            should_retry = (
                _is_retryable_databricks_error(error)
                and attempt < DATABRICKS_MAX_RETRIES
            )

            if not should_retry:
                raise QueryError(
                    SCAN_NAME,
                    f"Databricks query failed after {attempt} attempt(s): {error}",
                ) from error

            delay = _retry_delay_seconds(attempt)

            LOGGER.warning(
                "[Databricks] Transient query failure; retrying | "
                "attempt=%d | max_attempts=%d | delay_seconds=%.2f | error=%s",
                attempt,
                DATABRICKS_MAX_RETRIES,
                delay,
                error,
            )

            _reset_client()
            time.sleep(delay)

        finally:
            duration = time.perf_counter() - started_at

            emit_databricks_metric(
                query_name,
                duration,
                rows_returned,
                success,
            )

            LOGGER.info(
                "[Databricks] query_duration_seconds=%.3f | rows=%d | "
                "success=%s | attempt=%d/%d",
                duration,
                rows_returned,
                success,
                attempt,
                DATABRICKS_MAX_RETRIES,
            )

    raise QueryError(
        SCAN_NAME,
        "Databricks query failed after all retry attempts: "
        f"{last_error or 'unknown error'}",
    )


def detect_data_set(query):
    """Detect the local test-data set associated with a query."""
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
        return load_test_data(detect_data_set(query))

    try:
        started_at = datetime.datetime.now()
        result = query_databricks(query)
        duration_seconds = (datetime.datetime.now() - started_at).total_seconds()

        LOGGER.info(
            "[Databricks] duration_seconds=%.3f | record_count=%d",
            duration_seconds,
            len(result),
        )

        return result

    except Exception as error:
        LOGGER.exception("Error fetching data from Databricks: %s", error)
        LOGGER.info("Erroneous query: %s", query)
        raise


def fetch_from_databricks_with_params(query: str, params: Tuple[Any, ...]):
    """Fetch parameterized data from Databricks."""
    if IS_LOCAL:
        return load_test_data(detect_data_set(query))

    try:
        return query_databricks(query, params=params)
    except Exception:
        LOGGER.exception(
            "Error fetching data from Databricks. Params: %r",
            params,
        )
        raise


def fetch_in_chunks_keyset_frozen(
    table: str,
    time_col: str,
    start_dt,
    end_dt,
    chunk_size: int = 500_000,
    owners: list[str] | None = None,
):
    """Retrieve Databricks rows using keyset pagination over a fixed window."""
    last_time = None
    last_id = None
    start_param = to_utc_naive(start_dt)
    end_param = to_utc_naive(end_dt)

    q_time = f"`{time_col}`"
    q_id = "`_id`"

    while True:
        params: List[Any] = []

        def add_param(value):
            params.append(value)
            return f":p{len(params) - 1}"

        where = (
            f"WHERE {q_time} >= {add_param(start_param)} "
            f"AND {q_time} < {add_param(end_param)}"
        )

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
    """Retrieve multiple organizations' Databricks rows via keyset pagination."""
    last_time = None
    last_id = None
    start_param = to_utc_naive(start_dt)
    end_param = to_utc_naive(end_dt)

    table_ident = ".".join(f"`{part}`" for part in table.split("."))
    q_time = f"`{time_col}`"
    q_id = "`_id`"

    while True:
        params: List[Any] = []

        def add_param(value):
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
                f"({q_time} > {gt_marker} OR "
                f"({q_time} = {eq_marker} AND {q_id} > {id_marker}))"
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


def load_test_data(data_set: str) -> list:
    """Load local JSON test data for scan simulations."""
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
