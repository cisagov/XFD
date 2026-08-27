"""Qualys detail-report download and post-processing helpers."""

# Standard Python Libraries
import time
from pathlib import Path
from typing import Callable, Optional

# First-Party Libraries
from was_reports import report_data
from was_reports.pdf_helpers import post_process_detail_pdf
from was_reports.qualys_client import QualysClient
from was_reports.utils.qualys_config import QualysCredentials

DETAIL_POLL_SECONDS = 30


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
    sleep_function: Callable[[int], None] = time.sleep,
) -> None:
    """Wait until a Qualys report is complete or fails."""
    status = report_data.get_report_status(client, report_id)
    while status != "COMPLETE":
        if status == "ERROR":
            raise RuntimeError("Qualys report status returned ERROR.")
        sleep_function(sleep_seconds)
        status = report_data.get_report_status(client, report_id)


def download_detail_pdf(
    report_id: str,
    output_path: Path,
    credentials: QualysCredentials,
    session_factory: Optional[Callable] = None,
) -> Path:
    """Download a Qualys detail PDF to disk."""
    # Third-Party Libraries
    import requests

    resolved_session_factory = session_factory or requests.Session
    session = resolved_session_factory()
    session.auth = (credentials.username, credentials.password)
    response = session.get(build_download_url(credentials.hostname, report_id))
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def download_and_process_detail_report(
    client: QualysClient,
    report_id: str,
    filename: str,
    credentials: QualysCredentials,
    output_directory: Path,
    legacy_root: Path,
    from_webapp: bool = False,
    python_executable: str = "python",
    sleep_seconds: int = DETAIL_POLL_SECONDS,
    sleep_function: Callable[[int], None] = time.sleep,
    session_factory: Optional[Callable] = None,
) -> Path:
    """Download, redact, watermark, and trim a Qualys detail report."""
    wait_for_report_completion(
        client=client,
        report_id=report_id,
        sleep_seconds=sleep_seconds,
        sleep_function=sleep_function,
    )
    output_path = detail_pdf_path(
        filename=filename,
        output_directory=output_directory,
        asset_directory=legacy_root / "assets",
        from_webapp=from_webapp,
    )
    downloaded_path = download_detail_pdf(
        report_id=report_id,
        output_path=output_path,
        credentials=credentials,
        session_factory=session_factory,
    )
    post_process_detail_pdf(
        detail_path=downloaded_path,
        redacted_path=Path("{}_redacted.pdf".format(str(downloaded_path))),
        watermark_path=legacy_root / "cisa_marker_new.pdf",
        redactor_path=legacy_root / "redact_qualys.py",
        python_executable=python_executable,
    )
    return downloaded_path
