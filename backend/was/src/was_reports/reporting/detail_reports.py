"""Qualys detail-report download and post-processing helpers."""

# Standard Python Libraries
import errno
import logging
import os
from pathlib import Path
import random
import shutil
import time
from typing import Any, Callable

# Third-Party Libraries
import requests

# First-Party Libraries
from was_reports.qualys import report_data
from was_reports.qualys.qualys_client import (
    RETRYABLE_STATUS_CODES,
    QualysClient,
    QualysRetryPolicy,
    TimeoutSession,
    execute_retryable_operation,
)
from was_reports.reporting.exceptions import (
    ReportXmlDiskSpaceError,
    ReportXmlSizeLimitError,
    ReportXmlUnsafeContentError,
)
from was_reports.reporting.pdf_helpers import post_process_detail_pdf
from was_reports.utils.env import getenv
from was_reports.utils.operation_cancellation import (
    cancellable_sleep,
    raise_if_operation_cancelled,
)
from was_reports.utils.qualys_config import QualysCredentials

DETAIL_POLL_SECONDS = 60
DETAIL_PROGRESS_SECONDS = 300
DETAIL_POLL_TIMEOUT_SECONDS = 0
DEFAULT_REPORT_XML_MAX_BYTES = 10 * 1024 * 1024 * 1024
DEFAULT_REPORT_XML_MIN_FREE_BYTES = 5 * 1024 * 1024 * 1024
REPORT_XML_CHUNK_BYTES = 1024 * 1024
PROHIBITED_XML_DECLARATIONS = (b"<!DOCTYPE", b"<!ENTITY")
TERMINAL_FAILURE_STATUSES = frozenset(
    {"CANCELED", "CANCELLED", "DELETED", "ERROR", "FAILED"}
)
LOGGER = logging.getLogger(__name__)


def report_poll_timeout_seconds_from_environment() -> int | None:
    """Return the optional Qualys polling timeout, with zero meaning unlimited."""
    raw_value = getenv(
        "WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS",
        str(DETAIL_POLL_TIMEOUT_SECONDS),
    )
    try:
        timeout_seconds = int(raw_value) if raw_value is not None else 0
    except ValueError as error:
        raise ValueError(
            "WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS must be an integer."
        ) from error
    if timeout_seconds < 0:
        raise ValueError(
            "WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS must be zero or greater."
        )
    return timeout_seconds or None


def positive_poll_setting(name: str, default: int) -> int:
    """Return one positive Qualys polling interval from the environment."""
    raw_value = getenv(name, str(default))
    try:
        value = int(raw_value) if raw_value is not None else default
    except ValueError as error:
        raise ValueError("{} must be an integer.".format(name)) from error
    if value < 1:
        raise ValueError("{} must be at least 1.".format(name))
    return value


def positive_byte_setting(name: str, default: int) -> int:
    """Return one positive byte-count setting from the environment."""
    raw_value = getenv(name, str(default))
    try:
        value = int(raw_value) if raw_value is not None else default
    except ValueError as error:
        raise ValueError("{} must be an integer.".format(name)) from error
    if value < 1:
        raise ValueError("{} must be at least 1.".format(name))
    return value


def sanitized_detail_filename(filename: str) -> str:
    """Return a filesystem-safe legacy detail-report filename stem."""
    sanitized = filename.replace("https://", "")
    sanitized = sanitized.replace("http://", "")
    sanitized = sanitized.replace("/", "")
    sanitized = sanitized.replace(":", "")
    return sanitized.replace(" ", "")


def detail_pdf_path(
    filename: str,
    output_directory: Path,
    asset_directory: Path,
    from_webapp: bool,
) -> Path:
    """Return the legacy detail-report output path."""
    if from_webapp:
        return output_directory / "{}Details.pdf".format(
            sanitized_detail_filename(filename)
        )
    return asset_directory / "{}Details.pdf".format(filename)


def build_download_url(hostname: str, report_id: str) -> str:
    """Build the direct Qualys detail-report download URL."""
    return "https://{}/qps/rest/3.0/download/was/report/{}".format(
        hostname,
        report_id,
    )


def wait_for_report_completion(
    client: QualysClient,
    report_id: str,
    sleep_seconds: int | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
    timeout_seconds: int | None = None,
    progress_seconds: int | None = None,
    status_callback: Callable[[str], None] | None = None,
    monotonic_function: Callable[[], float] = time.monotonic,
) -> None:
    """Poll until a Qualys report completes or reaches a terminal failure."""
    resolved_sleep_seconds = sleep_seconds or positive_poll_setting(
        "WAS_QUALYS_REPORT_POLL_SECONDS",
        DETAIL_POLL_SECONDS,
    )
    resolved_progress_seconds = progress_seconds or positive_poll_setting(
        "WAS_QUALYS_REPORT_PROGRESS_SECONDS",
        DETAIL_PROGRESS_SECONDS,
    )
    resolved_timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else report_poll_timeout_seconds_from_environment()
    )
    if resolved_timeout_seconds is not None and resolved_timeout_seconds < 1:
        resolved_timeout_seconds = None
    started_at = monotonic_function()
    last_progress_at = started_at - resolved_progress_seconds
    last_status = None
    LOGGER.info(
        "Polling Qualys report %s every %s seconds until it completes.",
        report_id,
        resolved_sleep_seconds,
    )
    while True:
        raise_if_operation_cancelled()
        if (
            last_status is not None
            and resolved_timeout_seconds is not None
            and monotonic_function() - started_at >= resolved_timeout_seconds
        ):
            raise TimeoutError(
                "Qualys report {} did not complete within {} seconds.".format(
                    report_id, resolved_timeout_seconds
                )
            )
        poll_error = None
        try:
            status = report_data.get_report_status(client, report_id)
        except requests.RequestException as error:
            if isinstance(error, requests.exceptions.SSLError):
                raise
            transient = isinstance(error, (requests.ConnectionError, requests.Timeout))
            if isinstance(error, requests.HTTPError) and error.response is not None:
                transient = error.response.status_code in RETRYABLE_STATUS_CODES
            if not transient:
                raise
            poll_error = error
            status = None

        checked_at = monotonic_function()
        elapsed_seconds = int(checked_at - started_at)
        if poll_error is not None:
            LOGGER.warning(
                "Qualys report %s status check failed after %s seconds (%s). "
                "Polling will continue.",
                report_id,
                elapsed_seconds,
                type(poll_error).__name__,
            )

        normalized_status = (status or "UNKNOWN").strip().upper()
        if status_callback is not None:
            status_callback(normalized_status)
        if (
            normalized_status != last_status
            or checked_at - last_progress_at >= resolved_progress_seconds
        ):
            LOGGER.info(
                "Qualys report %s status is %s after %s seconds.",
                report_id,
                normalized_status,
                elapsed_seconds,
            )
            last_status = normalized_status
            last_progress_at = checked_at

        if normalized_status == "COMPLETE":
            LOGGER.info(
                "Qualys report %s completed after %s seconds.",
                report_id,
                elapsed_seconds,
            )
            return
        if normalized_status in TERMINAL_FAILURE_STATUSES:
            raise RuntimeError(
                "Qualys report {} reached terminal status {}.".format(
                    report_id,
                    normalized_status,
                )
            )
        if (
            resolved_timeout_seconds is not None
            and elapsed_seconds >= resolved_timeout_seconds
        ):
            raise TimeoutError(
                "Qualys report {} did not complete within {} seconds.".format(
                    report_id,
                    resolved_timeout_seconds,
                )
            )
        remaining_seconds = (
            resolved_timeout_seconds - (checked_at - started_at)
            if resolved_timeout_seconds is not None
            else resolved_sleep_seconds
        )
        cancellable_sleep(
            min(resolved_sleep_seconds, remaining_seconds),
            sleep_function=sleep_function,
        )


def _download_response(session: Any, url: str) -> Any:
    """Download and validate one Qualys detail-report response."""
    response = session.get(url)
    response.raise_for_status()
    return response


def _stream_report_xml_once(
    session: Any,
    url: str,
    output_path: Path,
    maximum_bytes: int,
    minimum_free_bytes: int,
) -> Path:
    """Stream one Qualys XML response to an owner-readable temporary file."""
    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    partial_path = output_path.with_name("{}.part".format(output_path.name))
    response = session.get(url, stream=True)
    response.raise_for_status()
    content_length = getattr(response, "headers", {}).get("Content-Length")
    if content_length is not None:
        try:
            expected_bytes = int(content_length)
        except ValueError as error:
            response.close()
            raise ValueError("Qualys returned an invalid Content-Length.") from error
        if expected_bytes > maximum_bytes:
            response.close()
            raise ReportXmlSizeLimitError(expected_bytes, maximum_bytes)
    total_bytes = 0
    declaration_prefix = b""
    try:
        output_path.parent.chmod(0o700)
        partial_path.unlink(missing_ok=True)
        with partial_path.open("xb") as output_file:
            partial_path.chmod(0o600)
            for chunk in response.iter_content(chunk_size=REPORT_XML_CHUNK_BYTES):
                raise_if_operation_cancelled()
                if not chunk:
                    continue
                total_bytes += len(chunk)
                if total_bytes > maximum_bytes:
                    raise ReportXmlSizeLimitError(total_bytes, maximum_bytes)
                inspection = declaration_prefix + chunk
                if any(
                    declaration in inspection
                    for declaration in PROHIBITED_XML_DECLARATIONS
                ):
                    raise ReportXmlUnsafeContentError(
                        "Qualys report XML contains a prohibited DTD declaration."
                    )
                declaration_prefix = inspection[-16:]
                free_bytes = shutil.disk_usage(output_path.parent).free
                if free_bytes - len(chunk) < minimum_free_bytes:
                    raise ReportXmlDiskSpaceError(
                        "Qualys report XML download stopped to preserve the "
                        "configured free-disk reserve."
                    )
                try:
                    output_file.write(chunk)
                except OSError as error:
                    if error.errno == errno.ENOSPC:
                        raise ReportXmlDiskSpaceError(
                            "Qualys report XML download exhausted local disk space."
                        ) from error
                    raise
        os.replace(partial_path, output_path)
        output_path.chmod(0o600)
        LOGGER.info(
            "Streamed Qualys report XML %s to private storage (%s bytes).",
            output_path.name,
            total_bytes,
        )
        return output_path
    finally:
        response.close()
        partial_path.unlink(missing_ok=True)


def download_report_xml(
    report_id: str,
    output_path: Path,
    credentials: QualysCredentials,
    session_factory: Callable | None = None,
    retry_policy: QualysRetryPolicy | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
    random_function: Callable[[], float] = random.random,
) -> Path:
    """Stream a generated Qualys XML report to private local storage."""
    resolved_retry_policy = retry_policy or QualysRetryPolicy.from_environment()
    maximum_bytes = positive_byte_setting(
        "WAS_QUALYS_REPORT_XML_MAX_BYTES",
        DEFAULT_REPORT_XML_MAX_BYTES,
    )
    minimum_free_bytes = positive_byte_setting(
        "WAS_QUALYS_REPORT_XML_MIN_FREE_BYTES",
        DEFAULT_REPORT_XML_MIN_FREE_BYTES,
    )
    if session_factory is None:
        session = TimeoutSession(resolved_retry_policy.request_timeout_seconds)
    else:
        session = session_factory()
    session.auth = (credentials.username, credentials.password)
    download_url = build_download_url(credentials.hostname, report_id)
    return execute_retryable_operation(
        operation=lambda: _stream_report_xml_once(
            session,
            download_url,
            output_path,
            maximum_bytes,
            minimum_free_bytes,
        ),
        operation_name="download XML report {}".format(report_id),
        policy=resolved_retry_policy,
        sleep_function=sleep_function,
        random_function=random_function,
    )


def download_detail_pdf(
    report_id: str,
    output_path: Path,
    credentials: QualysCredentials,
    session_factory: Callable | None = None,
    retry_policy: QualysRetryPolicy | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
    random_function: Callable[[], float] = random.random,
) -> Path:
    """Download a Qualys detail PDF to disk."""
    resolved_retry_policy = retry_policy or QualysRetryPolicy.from_environment()
    if session_factory is None:
        session = TimeoutSession(resolved_retry_policy.request_timeout_seconds)
    else:
        session = session_factory()
    session.auth = (credentials.username, credentials.password)
    download_url = build_download_url(credentials.hostname, report_id)
    response = execute_retryable_operation(
        operation=lambda: _download_response(session, download_url),
        operation_name="download detail report {}".format(report_id),
        policy=resolved_retry_policy,
        sleep_function=sleep_function,
        random_function=random_function,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def download_and_process_detail_report(
    client: QualysClient,
    report_id: str,
    filename: str,
    credentials: QualysCredentials,
    output_directory: Path,
    resource_root: Path,
    from_webapp: bool = False,
    python_executable: str = "python",
    sleep_seconds: int | None = None,
    sleep_function: Callable[[float], None] = time.sleep,
    session_factory: Callable | None = None,
    poll_timeout_seconds: int | None = None,
    retry_policy: QualysRetryPolicy | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> Path:
    """Download, redact, watermark, and trim a Qualys detail report."""
    wait_for_report_completion(
        client=client,
        report_id=report_id,
        sleep_seconds=sleep_seconds,
        sleep_function=sleep_function,
        timeout_seconds=poll_timeout_seconds,
        status_callback=status_callback,
    )
    output_path = detail_pdf_path(
        filename=filename,
        output_directory=output_directory,
        asset_directory=resource_root / "assets",
        from_webapp=from_webapp,
    )
    downloaded_path = download_detail_pdf(
        report_id=report_id,
        output_path=output_path,
        credentials=credentials,
        session_factory=session_factory,
        retry_policy=retry_policy,
        sleep_function=sleep_function,
    )
    post_process_detail_pdf(
        detail_path=downloaded_path,
        redacted_path=Path("{}_redacted.pdf".format(str(downloaded_path))),
        watermark_path=resource_root / "cisa_marker_new.pdf",
        redactor_path=resource_root / "redact_qualys.py",
        python_executable=python_executable,
    )
    return downloaded_path
