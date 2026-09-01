"""Qualys detail-report download and post-processing helpers."""

# Standard Python Libraries
from pathlib import Path
import random
import time
from typing import Any, Callable

# Third-Party Libraries
# First-Party Libraries
from was_reports.qualys import report_data
from was_reports.qualys.qualys_client import (
    QualysClient,
    QualysRetryPolicy,
    TimeoutSession,
    execute_retryable_operation,
)
from was_reports.reporting.pdf_helpers import post_process_detail_pdf
from was_reports.utils.env import getenv
from was_reports.utils.qualys_config import QualysCredentials

DETAIL_POLL_SECONDS = 30
DETAIL_POLL_TIMEOUT_SECONDS = 1800


def report_poll_timeout_seconds_from_environment() -> int:
    """Return the bounded Qualys report polling timeout from the environment."""
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
    if timeout_seconds < 1:
        raise ValueError("WAS_QUALYS_REPORT_POLL_TIMEOUT_SECONDS must be at least 1.")
    return timeout_seconds


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
    sleep_seconds: int = DETAIL_POLL_SECONDS,
    sleep_function: Callable[[float], None] = time.sleep,
    timeout_seconds: int | None = None,
    monotonic_function: Callable[[], float] = time.monotonic,
) -> None:
    """Wait until a Qualys report is complete or fails."""
    resolved_timeout_seconds = (
        timeout_seconds
        if timeout_seconds is not None
        else report_poll_timeout_seconds_from_environment()
    )
    deadline = monotonic_function() + resolved_timeout_seconds
    status = report_data.get_report_status(client, report_id)
    while status != "COMPLETE":
        if status == "ERROR":
            raise RuntimeError("Qualys report status returned ERROR.")
        if monotonic_function() >= deadline:
            raise TimeoutError(
                "Qualys report {} did not complete within {} seconds.".format(
                    report_id,
                    resolved_timeout_seconds,
                )
            )
        sleep_function(sleep_seconds)
        status = report_data.get_report_status(client, report_id)


def _download_response(session: Any, url: str) -> Any:
    """Download and validate one Qualys detail-report response."""
    response = session.get(url)
    response.raise_for_status()
    return response


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
    sleep_seconds: int = DETAIL_POLL_SECONDS,
    sleep_function: Callable[[float], None] = time.sleep,
    session_factory: Callable | None = None,
    poll_timeout_seconds: int | None = None,
    retry_policy: QualysRetryPolicy | None = None,
) -> Path:
    """Download, redact, watermark, and trim a Qualys detail report."""
    wait_for_report_completion(
        client=client,
        report_id=report_id,
        sleep_seconds=sleep_seconds,
        sleep_function=sleep_function,
        timeout_seconds=poll_timeout_seconds,
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
