"""Qualys API client boundary for WAS report generation."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import random
import time
from typing import Any, Callable, TypeVar

# Third-Party Libraries
import requests
from was_reports.utils.env import getenv

# First-Party Libraries
from was_reports.utils.qualys_config import (
    QualysCredentials,
    load_qualys_credentials_from_environment,
)

LOGGER = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
RETRY_SAFE_ENDPOINT_PREFIXES = frozenset({"count", "download", "search", "status"})
OperationResult = TypeVar("OperationResult")


def _environment_integer(name: str, default: int, minimum: int = 1) -> int:
    """Return a validated integer retry setting from the environment."""
    raw_value = getenv(name, str(default))
    try:
        value = int(raw_value) if raw_value is not None else default
    except ValueError as error:
        raise ValueError("{} must be an integer.".format(name)) from error
    if value < minimum:
        raise ValueError("{} must be at least {}.".format(name, minimum))
    return value


def _environment_float(name: str, default: float, minimum: float = 0.0) -> float:
    """Return a validated floating-point retry setting from the environment."""
    raw_value = getenv(name, str(default))
    try:
        value = float(raw_value) if raw_value is not None else default
    except ValueError as error:
        raise ValueError("{} must be numeric.".format(name)) from error
    if value < minimum:
        raise ValueError("{} must be at least {}.".format(name, minimum))
    return value


@dataclass(frozen=True)
class QualysRetryPolicy:
    """Bounded retry and timeout settings for Qualys API operations."""

    max_attempts: int = 4
    request_timeout_seconds: float = 60.0
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_ratio: float = 0.25

    @classmethod
    def from_environment(cls) -> QualysRetryPolicy:
        """Load validated Qualys retry settings from environment variables."""
        policy = cls(
            max_attempts=_environment_integer("WAS_QUALYS_MAX_ATTEMPTS", 4),
            request_timeout_seconds=_environment_float(
                "WAS_QUALYS_REQUEST_TIMEOUT_SECONDS",
                60.0,
                minimum=0.1,
            ),
            base_delay_seconds=_environment_float(
                "WAS_QUALYS_RETRY_BASE_DELAY_SECONDS",
                1.0,
            ),
            max_delay_seconds=_environment_float(
                "WAS_QUALYS_RETRY_MAX_DELAY_SECONDS",
                30.0,
            ),
            jitter_ratio=_environment_float(
                "WAS_QUALYS_RETRY_JITTER_RATIO",
                0.25,
            ),
        )
        if policy.max_delay_seconds < policy.base_delay_seconds:
            raise ValueError(
                "WAS_QUALYS_RETRY_MAX_DELAY_SECONDS must be greater than or "
                "equal to WAS_QUALYS_RETRY_BASE_DELAY_SECONDS."
            )
        return policy


class TimeoutSession:
    """Requests session that applies a default timeout to every operation."""

    def __init__(self, timeout_seconds: float):
        """Initialize the session with a required default timeout."""
        self._session = requests.Session()
        self._timeout_seconds = timeout_seconds

    @property
    def auth(self) -> Any:
        """Return authentication configured on the wrapped requests session."""
        return self._session.auth

    @auth.setter
    def auth(self, value: Any) -> None:
        """Set authentication on the wrapped requests session."""
        self._session.auth = value

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Send a GET request using the configured default timeout."""
        kwargs.setdefault("timeout", self._timeout_seconds)
        return self._session.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """Send a POST request using the configured default timeout."""
        kwargs.setdefault("timeout", self._timeout_seconds)
        return self._session.post(url, **kwargs)


@dataclass(frozen=True)
class QualysRequest:
    """Description of one Qualys API request."""

    endpoint: str
    payload: str | None = None
    http_method: str | None = None
    retry_safe: bool | None = None


def is_retry_safe(qualys_request: QualysRequest) -> bool:
    """Return whether repeating a Qualys request cannot create a side effect."""
    if qualys_request.retry_safe is not None:
        return qualys_request.retry_safe
    if (qualys_request.http_method or "").lower() == "get":
        return True
    endpoint_root = qualys_request.endpoint.lstrip("/").split("/", 1)[0].lower()
    return endpoint_root in RETRY_SAFE_ENDPOINT_PREFIXES


def _retry_after_seconds(error: Exception) -> float | None:
    """Return a server-requested retry delay from an HTTP error when present."""
    if not isinstance(error, requests.HTTPError) or error.response is None:
        return None
    raw_value = error.response.headers.get("Retry-After")
    if not raw_value:
        return None
    try:
        delay_seconds = float(raw_value)
    except ValueError:
        try:
            retry_time = parsedate_to_datetime(raw_value)
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_time.tzinfo is None:
            retry_time = retry_time.replace(tzinfo=timezone.utc)
        delay_seconds = (retry_time - datetime.now(timezone.utc)).total_seconds()
    return max(0.0, delay_seconds)


def _is_retryable_error(error: Exception) -> bool:
    """Return whether an exception represents a transient Qualys failure."""
    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
        return True
    if not isinstance(error, requests.HTTPError) or error.response is None:
        return False
    return error.response.status_code in RETRYABLE_STATUS_CODES


def _retry_delay_seconds(
    error: Exception,
    failed_attempt: int,
    policy: QualysRetryPolicy,
    random_function: Callable[[], float],
) -> float:
    """Calculate capped exponential backoff with jitter and Retry-After support."""
    exponential_delay = policy.base_delay_seconds * (2 ** (failed_attempt - 1))
    jitter = exponential_delay * policy.jitter_ratio * random_function()
    calculated_delay = exponential_delay + jitter
    retry_after = _retry_after_seconds(error)
    if retry_after is not None:
        calculated_delay = max(calculated_delay, retry_after)
    return min(calculated_delay, policy.max_delay_seconds)


def execute_retryable_operation(
    operation: Callable[[], OperationResult],
    operation_name: str,
    policy: QualysRetryPolicy,
    sleep_function: Callable[[float], None] = time.sleep,
    random_function: Callable[[], float] = random.random,
) -> OperationResult:
    """Execute a read-safe Qualys operation with bounded transient retries."""
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return operation()
        except Exception as error:
            if not _is_retryable_error(error) or attempt >= policy.max_attempts:
                raise
            delay_seconds = _retry_delay_seconds(
                error=error,
                failed_attempt=attempt,
                policy=policy,
                random_function=random_function,
            )
            LOGGER.warning(
                "Transient Qualys failure during %s on attempt %d of %d. "
                "Retrying in %.2f seconds.",
                operation_name,
                attempt,
                policy.max_attempts,
                delay_seconds,
            )
            sleep_function(delay_seconds)
    raise RuntimeError("Qualys retry loop exited unexpectedly.")


class QualysClient:
    """Retry-aware wrapper around the Qualys API connector."""

    def __init__(
        self,
        connection: Any,
        retry_policy: QualysRetryPolicy | None = None,
        sleep_function: Callable[[float], None] = time.sleep,
        random_function: Callable[[], float] = random.random,
    ):
        """Initialize the client with a Qualys API connection."""
        self._connection = connection
        self._retry_policy = retry_policy or QualysRetryPolicy()
        self._sleep_function = sleep_function
        self._random_function = random_function

    def request(self, qualys_request: QualysRequest) -> str:
        """Execute a Qualys request, retrying only read-safe transient failures."""
        if not is_retry_safe(qualys_request):
            return self._request_once(qualys_request)
        return execute_retryable_operation(
            operation=lambda: self._request_once(qualys_request),
            operation_name=qualys_request.endpoint,
            policy=self._retry_policy,
            sleep_function=self._sleep_function,
            random_function=self._random_function,
        )

    def _request_once(self, qualys_request: QualysRequest) -> str:
        """Execute one request through the Qualys connector interface."""
        if qualys_request.payload is None and qualys_request.http_method is None:
            return self._connection.request(qualys_request.endpoint)

        if qualys_request.http_method is None:
            return self._connection.request(
                qualys_request.endpoint,
                qualys_request.payload,
            )

        if qualys_request.payload is None:
            return self._connection.request(
                qualys_request.endpoint,
                http_method=qualys_request.http_method,
            )

        return self._connection.request(
            qualys_request.endpoint,
            qualys_request.payload,
            http_method=qualys_request.http_method,
        )


def create_qualys_client(
    credentials: QualysCredentials | None = None,
    retry_policy: QualysRetryPolicy | None = None,
) -> QualysClient:
    """Create a Qualys client directly from environment-backed credentials."""
    resolved_credentials = credentials or load_qualys_credentials_from_environment()
    resolved_retry_policy = retry_policy or QualysRetryPolicy.from_environment()
    # Third-Party Libraries
    from qualysapi.connector import QGConnector

    connection = QGConnector(
        auth=(resolved_credentials.username, resolved_credentials.password),
        server=resolved_credentials.hostname,
        max_retries=0,
    )
    connection.session = TimeoutSession(
        timeout_seconds=resolved_retry_policy.request_timeout_seconds
    )
    return QualysClient(connection, retry_policy=resolved_retry_policy)
