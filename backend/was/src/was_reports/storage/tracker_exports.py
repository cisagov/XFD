"""Archive password-free tracker exports separately from stakeholder exports."""

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

from was_reports.storage.s3_reports import (
    create_s3_client,
    reports_bucket_name,
    reports_prefix,
    s3_uri,
)
from was_reports.reporting.latex_renderer import validate_filename_component


def upload_tracker_export(path: Path, s3_client=None) -> str:
    """Upload a CSV with encryption and a unique tracker-export object key."""
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise ValueError("A tracker CSV file is required.")
    prefix = reports_prefix().strip("/")
    for component in prefix.split("/"):
        validate_filename_component(component)
    key = str(
        PurePosixPath(
            prefix,
            "tracker_exports",
            datetime.now(timezone.utc).date().isoformat(),
            "{}-{}.csv".format(validate_filename_component(path.stem), uuid4()),
        )
    )
    bucket = reports_bucket_name()
    client = s3_client or create_s3_client()
    client.upload_file(
        str(path),
        bucket,
        key,
        ExtraArgs={"ContentType": "text/csv", "ServerSideEncryption": "AES256"},
    )
    return s3_uri(bucket, key)
