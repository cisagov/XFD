"""Qualys API client boundary for WAS report generation."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import logging
import random
import shlex
import time
from typing import Any, Callable, TypeVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

# Third-Party Libraries
import requests
from was_reports.utils.env import getenv
from was_reports.utils.capacity_telemetry import emit_metric
from was_reports.utils.logging_config import exception_details
from was_reports.utils.operation_cancellation import (
    OperationCancelledError,
    cancellable_sleep,
    raise_if_operation_cancelled,
)

# First-Party Libraries
from was_reports.utils.qualys_config import (
    QualysCredentials,
    load_qualys_credentials_from_environment,
)

LOGGER = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
RETRY_SAFE_ENDPOINT_PREFIXES = frozenset({"count", "download", "search", "status"})
SENSITIVE_XML_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "credentials",
        "password",
        "secret",
        "token",
        "username",
    }
)
SAFE_RESPONSE_HEADERS = frozenset(
    {
        "content-type",
        "date",
        "retry-after",
        "x-amzn-requestid",
        "x-correlation-id",
        "x-powered-by",
        "x-request-id",
    }
)
MAX_LOGGED_RESPONSE_CHARACTERS = 16384
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
    authentication_retry_delay_seconds: float = 5.0
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
                120.0,
                minimum=0.1,
            ),
            authentication_retry_delay_seconds=_environment_float(
                "WAS_QUALYS_AUTH_RETRY_DELAY_SECONDS",
                5.0,
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
        response = self._session.get(url, **kwargs)
        response.raise_for_status()
        return response

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """Send a POST request using the configured default timeout."""
        kwargs.setdefault("timeout", self._timeout_seconds)
        response = self._session.post(url, **kwargs)
        response.raise_for_status()
        return response


@dataclass(frozen=True)
class QualysRequest:
    """Description of one Qualys API request."""

    endpoint: str
    payload: str | None = None
    http_method: str | None = None
    retry_safe: bool | None = None


def _xml_name(value: str) -> str:
    """Return a lowercase XML name without a namespace prefix."""
    return value.rsplit("}", 1)[-1].lower().replace("-", "_")


def sanitized_qualys_payload(payload: str | None) -> str | None:
    """Return reproducible request XML with credential-like values removed."""
    if payload is None:
        return None
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return "<invalid-xml sha256={}>".format(payload_hash)

    for element in root.iter():
        element_name = _xml_name(element.tag)
        field_name = ""
        for attribute_name, attribute_value in element.attrib.items():
            normalized_attribute = _xml_name(attribute_name)
            if normalized_attribute == "field":
                field_name = attribute_value.lower().replace("-", "_")
            if normalized_attribute in SENSITIVE_XML_NAMES:
                element.attrib[attribute_name] = "REDACTED"
        if element_name in SENSITIVE_XML_NAMES or field_name in SENSITIVE_XML_NAMES:
            element.text = "REDACTED"
            for child in element:
                child.text = "REDACTED"
    serialized_payload = ElementTree.tostring(root, encoding="unicode")
    for variable_name in ("WAS_QUALYS_USERNAME", "WAS_QUALYS_PASSWORD"):
        secret_value = getenv(variable_name)
        if secret_value:
            serialized_payload = serialized_payload.replace(secret_value, "REDACTED")
    return serialized_payload


def _safe_request_url(url: str) -> str:
    """Return a request URL with credentials and sensitive query values removed."""
    parsed_url = urlsplit(url)
    hostname = parsed_url.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = "[{}]".format(hostname)
    netloc = hostname
    if parsed_url.port is not None:
        netloc = "{}:{}".format(netloc, parsed_url.port)
    sanitized_query = []
    for name, value in parse_qsl(parsed_url.query, keep_blank_values=True):
        normalized_name = name.lower().replace("-", "_")
        if normalized_name in SENSITIVE_XML_NAMES:
            value = "REDACTED"
        sanitized_query.append((name, value))
    return urlunsplit(
        (
            parsed_url.scheme,
            netloc,
            parsed_url.path,
            urlencode(sanitized_query),
            "",
        )
    )


def _prepared_request(error: Exception) -> requests.PreparedRequest | None:
    """Return the exact prepared request retained by a requests exception."""
    if not isinstance(error, requests.RequestException):
        return None
    if error.request is not None:
        return error.request
    if error.response is not None:
        return error.response.request
    return None


def _request_body(payload: Any) -> str | None:
    """Return a request body as text when it can be sanitized safely."""
    if payload is None:
        return None
    if isinstance(payload, bytes):
        return payload.decode("utf-8", errors="replace")
    return str(payload)


def _fallback_qualys_url(endpoint: str) -> str:
    """Return the expected URL when an exception has no prepared request."""
    api_version = "1.0" if endpoint.lstrip("/").startswith("search/am/") else "3.0"
    return "${{WAS_QUALYS_HOSTNAME%/}}/qps/rest/{}/{}".format(
        api_version,
        endpoint.lstrip("/"),
    )


def qualys_replay_command(
    qualys_request: QualysRequest,
    error: Exception | None = None,
) -> str:
    """Build a credential-free curl command for reproducing a failed request."""
    prepared_request = _prepared_request(error) if error is not None else None
    method = prepared_request.method if prepared_request is not None else None
    if method is None:
        method = qualys_request.http_method
    if method is None:
        method = "POST" if qualys_request.payload is not None else "GET"
    command_parts = [
        "curl",
        "--fail-with-body",
        "--user",
        '"${WAS_QUALYS_USERNAME}:${WAS_QUALYS_PASSWORD}"',
        "--request",
        method.upper(),
    ]
    payload = qualys_request.payload
    if prepared_request is not None:
        payload = _request_body(prepared_request.body)
    sanitized_payload = sanitized_qualys_payload(payload)
    if sanitized_payload is not None:
        command_parts.extend(
            [
                "--header",
                shlex.quote("Content-Type: application/xml"),
                "--data-binary",
                shlex.quote(sanitized_payload),
            ]
        )
    request_url = _fallback_qualys_url(qualys_request.endpoint)
    if prepared_request is not None and prepared_request.url:
        request_url = _safe_request_url(prepared_request.url)
        command_parts.append(shlex.quote(request_url))
    else:
        command_parts.append('"{}"'.format(request_url))
    return " ".join(command_parts)


def qualys_failure_response_summary(error: Exception) -> str:
    """Return bounded and sanitized response evidence for a failed request."""
    if not isinstance(error, requests.RequestException) or error.response is None:
        return "No HTTP response was received."

    response = error.response
    safe_headers = []
    for name, value in response.headers.items():
        if name.lower() in SAFE_RESPONSE_HEADERS:
            safe_headers.append("{}={}".format(name, value))
    header_summary = ", ".join(sorted(safe_headers)) or "none"
    body = sanitized_qualys_payload(response.text)
    if body is None:
        body = "none"
    if len(body) > MAX_LOGGED_RESPONSE_CHARACTERS:
        body = "{}...[truncated; original characters={}]".format(
            body[:MAX_LOGGED_RESPONSE_CHARACTERS],
            len(body),
        )
    return "HTTP status={}; safe headers={}; sanitized body={}".format(
        response.status_code,
        header_summary,
        body,
    )


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
    if isinstance(error, requests.exceptions.SSLError):
        return False
    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
        return True
    if not isinstance(error, requests.HTTPError) or error.response is None:
        return False
    return error.response.status_code in RETRYABLE_STATUS_CODES


def _is_authentication_error(error: Exception) -> bool:
    """Return whether Qualys rejected one request with HTTP 401."""
    return (
        isinstance(error, requests.HTTPError)
        and error.response is not None
        and error.response.status_code == 401
    )


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
    authentication_retry_used = False
    for attempt in range(1, policy.max_attempts + 1):
        raise_if_operation_cancelled()
        try:
            result = operation()
            raise_if_operation_cancelled()
            return result
        except OperationCancelledError:
            raise
        except Exception as error:
            authentication_failure = _is_authentication_error(error)
            if authentication_failure:
                if authentication_retry_used or attempt >= policy.max_attempts:
                    raise
                authentication_retry_used = True
                delay_seconds = policy.authentication_retry_delay_seconds
                LOGGER.warning(
                    "Qualys authentication was rejected during %s on attempt %d. "
                    "Retrying once in %.2f seconds.",
                    operation_name,
                    attempt,
                    delay_seconds,
                )
                cancellable_sleep(delay_seconds, sleep_function=sleep_function)
                continue
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
            cancellable_sleep(delay_seconds, sleep_function=sleep_function)
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
        raise_if_operation_cancelled()
        started = time.monotonic()
        LOGGER.info("Requesting Qualys %s.", qualys_request.endpoint)
        attempt_number = 0

        def perform_request() -> str:
            """Measure each HTTP attempt without recording payloads or credentials."""
            nonlocal attempt_number
            attempt_number += 1
            attempt_started = time.monotonic()
            outcome = "success"
            http_status = None
            try:
                return self._request_once(qualys_request)
            except Exception as error:
                outcome = type(error).__name__
                response = getattr(error, "response", None)
                http_status = getattr(response, "status_code", None)
                raise
            finally:
                emit_metric(
                    "qualys_attempt",
                    endpoint=urlsplit(qualys_request.endpoint).path,
                    attempt_number=attempt_number,
                    duration_seconds=time.monotonic() - attempt_started,
                    outcome=outcome,
                    http_status=http_status,
                )

        try:
            if not is_retry_safe(qualys_request):
                result = perform_request()
            else:
                result = execute_retryable_operation(
                    operation=perform_request,
                    operation_name=qualys_request.endpoint,
                    policy=self._retry_policy,
                    sleep_function=self._sleep_function,
                    random_function=self._random_function,
                )
        except OperationCancelledError:
            LOGGER.info(
                "Qualys %s cancelled by operator after %.1f seconds.",
                qualys_request.endpoint,
                time.monotonic() - started,
            )
            raise
        except Exception as error:
            LOGGER.warning(
                "Qualys %s failed after %.1f seconds: %s.",
                qualys_request.endpoint,
                time.monotonic() - started,
                exception_details(error),
            )
            LOGGER.error(
                "Qualys failure replay command, credentials omitted: %s",
                qualys_replay_command(qualys_request, error=error),
            )
            LOGGER.error(
                "Qualys failure response evidence: %s",
                qualys_failure_response_summary(error),
            )
            raise
        LOGGER.info(
            "Qualys %s completed in %.1f seconds.",
            qualys_request.endpoint,
            time.monotonic() - started,
        )
        raise_if_operation_cancelled()
        return result

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

    logging.getLogger("qualysapi.connector").disabled = True
    connection = QGConnector(
        auth=(resolved_credentials.username, resolved_credentials.password),
        server=resolved_credentials.hostname,
        max_retries=0,
    )
    connection.session = TimeoutSession(
        timeout_seconds=resolved_retry_policy.request_timeout_seconds
    )
    return QualysClient(connection, retry_policy=resolved_retry_policy)
