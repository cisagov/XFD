"""Store stakeholder database exports in the configured WAS S3 location."""

# Standard Python Libraries
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Optional
from uuid import uuid4

# First-Party Libraries
from was_reports.reporting.latex_renderer import validate_filename_component
from was_reports.storage.s3_reports import (
    create_s3_client,
    reports_bucket_name,
    reports_prefix,
    s3_uri,
)


def stakeholder_export_object_key(
    filename: str,
    exported_at: Optional[datetime] = None,
    prefix: Optional[str] = None,
) -> str:
    """Return a unique S3 key for one stakeholder CSV export."""
    timestamp = exported_at or datetime.now(timezone.utc)
    safe_filename = validate_filename_component(Path(filename).name)
    if Path(safe_filename).suffix.lower() != ".csv":
        raise ValueError("Stakeholder exports must use a CSV filename.")
    normalized_prefix = (prefix or reports_prefix()).strip("/")
    for component in normalized_prefix.split("/"):
        validate_filename_component(component)
    unique_filename = "{}-{}{}".format(
        Path(safe_filename).stem,
        uuid4(),
        Path(safe_filename).suffix,
    )
    return str(
        PurePosixPath(
            normalized_prefix,
            "stakeholder_exports",
            timestamp.date().isoformat(),
            unique_filename,
        )
    )


def upload_stakeholder_export(
    export_path: Path,
    s3_client=None,
    bucket: Optional[str] = None,
    prefix: Optional[str] = None,
) -> str:
    """Upload one stakeholder CSV export and return its S3 URI."""
    if not export_path.is_file():
        raise FileNotFoundError(
            "Stakeholder export file was not found at {}.".format(export_path)
        )
    object_key = stakeholder_export_object_key(
        filename=export_path.name,
        prefix=prefix,
    )
    resolved_bucket = bucket or reports_bucket_name()
    client = s3_client or create_s3_client()
    client.upload_file(
        str(export_path),
        resolved_bucket,
        object_key,
        ExtraArgs={
            "ContentType": "text/csv",
            "ServerSideEncryption": "AES256",
        },
    )
    return s3_uri(resolved_bucket, object_key)
