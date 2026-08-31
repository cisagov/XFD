"""Store and retrieve generated WAS report PDFs in Amazon S3."""

# Standard Python Libraries
from contextlib import contextmanager
from datetime import date
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Iterator, Optional, Tuple

# Third-Party Libraries
# First-Party Libraries
from was_reports.reporting.latex_renderer import validate_filename_component
from was_reports.utils.env import getenv, require_env

DEFAULT_REPORTS_PREFIX = "was_reports"
LOCAL_STORAGE = "local"
S3_STORAGE = "s3"
S3_URI_PREFIX = "s3://"
VALID_STORAGE_MODES = (LOCAL_STORAGE, S3_STORAGE)


def reports_bucket_name() -> str:
    """Return the S3 bucket configured for WAS report storage."""
    return require_env("WAS_REPORTS_BUCKET_NAME")


def reports_prefix() -> str:
    """Return the normalized S3 key prefix for WAS report storage."""
    configured_prefix = getenv("WAS_REPORTS_PREFIX", DEFAULT_REPORTS_PREFIX)
    normalized_prefix = (configured_prefix or DEFAULT_REPORTS_PREFIX).strip("/")
    if not normalized_prefix:
        return DEFAULT_REPORTS_PREFIX
    components = normalized_prefix.split("/")
    for component in components:
        validate_filename_component(component)
    return "/".join(components)


def resolve_storage_mode(value: Optional[str] = None) -> str:
    """Return a validated WAS report storage mode."""
    configured_value = value or getenv("WAS_REPORT_STORAGE", S3_STORAGE)
    normalized_value = (configured_value or S3_STORAGE).strip().lower()
    if normalized_value not in VALID_STORAGE_MODES:
        raise ValueError(
            "WAS report storage mode must be one of: {}.".format(
                ", ".join(VALID_STORAGE_MODES)
            )
        )
    return normalized_value


def report_object_key(
    stakeholder_tag: str,
    report_date: date,
    report_run_id: int,
    filename: str,
    prefix: Optional[str] = None,
) -> str:
    """Return the run-specific S3 key for an encrypted WAS report PDF."""
    safe_tag = validate_filename_component(stakeholder_tag)
    safe_filename = validate_filename_component(Path(filename).name)
    if report_run_id < 1:
        raise ValueError("WAS report run id must be a positive integer.")
    normalized_prefix = (prefix or reports_prefix()).strip("/")
    for component in normalized_prefix.split("/"):
        validate_filename_component(component)
    return str(
        PurePosixPath(
            normalized_prefix,
            report_date.isoformat(),
            safe_tag,
            str(report_run_id),
            safe_filename,
        )
    )


def s3_uri(bucket: str, key: str) -> str:
    """Return an S3 URI for a bucket and object key."""
    if not bucket.strip() or not key.strip("/"):
        raise ValueError("S3 bucket and object key are required.")
    return "{}{}{}{}".format(S3_URI_PREFIX, bucket, "/", key.strip("/"))


def parse_s3_uri(report_reference: str) -> Tuple[str, str]:
    """Parse and validate an S3 report URI."""
    if not report_reference.startswith(S3_URI_PREFIX):
        raise ValueError("WAS report reference is not an S3 URI.")
    bucket_and_key = report_reference[len(S3_URI_PREFIX) :]
    if "/" not in bucket_and_key:
        raise ValueError("WAS report S3 URI does not include an object key.")
    bucket, key = bucket_and_key.split("/", 1)
    if not bucket or not key or key.endswith("/"):
        raise ValueError("WAS report S3 URI is incomplete.")
    for component in PurePosixPath(key).parts:
        validate_filename_component(component)
    return bucket, key


def validate_report_location(
    bucket: str,
    key: str,
    expected_bucket: Optional[str] = None,
    expected_prefix: Optional[str] = None,
) -> None:
    """Require a report object to remain in the configured bucket and prefix."""
    configured_bucket = expected_bucket or reports_bucket_name()
    configured_prefix = (expected_prefix or reports_prefix()).strip("/")
    if bucket != configured_bucket:
        raise ValueError("WAS report S3 URI uses an unexpected bucket.")
    if not key.startswith("{}/".format(configured_prefix)):
        raise ValueError("WAS report S3 URI uses an unexpected object prefix.")


def create_s3_client():
    """Create an S3 client using the runtime IAM role and AWS configuration."""
    # Third-Party Libraries
    import boto3

    return boto3.client("s3")


def upload_report(
    report_path: Path,
    stakeholder_tag: str,
    report_date: date,
    report_run_id: int,
    s3_client=None,
    bucket: Optional[str] = None,
    prefix: Optional[str] = None,
) -> str:
    """Upload an encrypted WAS PDF and return its S3 URI."""
    if not report_path.is_file():
        raise FileNotFoundError(
            "WAS report upload file was not found at {}.".format(report_path)
        )
    if report_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF report artifacts may be uploaded to WAS S3.")

    resolved_bucket = bucket or reports_bucket_name()
    object_key = report_object_key(
        stakeholder_tag=stakeholder_tag,
        report_date=report_date,
        report_run_id=report_run_id,
        filename=report_path.name,
        prefix=prefix,
    )
    client = s3_client or create_s3_client()
    client.upload_file(
        str(report_path),
        resolved_bucket,
        object_key,
        ExtraArgs={
            "ContentType": "application/pdf",
            "ServerSideEncryption": "AES256",
        },
    )
    return s3_uri(resolved_bucket, object_key)


@contextmanager
def materialize_report(
    report_reference: str,
    s3_client=None,
    expected_bucket: Optional[str] = None,
    expected_prefix: Optional[str] = None,
    storage_mode: Optional[str] = None,
    expected_local_root: Optional[Path] = None,
) -> Iterator[Path]:
    """Yield a local report path from an S3 URI or local compatibility path."""
    if not report_reference.startswith(S3_URI_PREFIX):
        if resolve_storage_mode(storage_mode) != LOCAL_STORAGE:
            raise ValueError("Local WAS report references require local storage mode.")
        configured_root = expected_local_root or Path(
            require_env("WAS_OUTPUT_DIRECTORY")
        )
        resolved_root = configured_root.resolve()
        candidate_path = Path(report_reference)
        if not candidate_path.is_file():
            raise FileNotFoundError(
                "WAS report attachment was not found at {}.".format(candidate_path)
            )
        local_path = candidate_path.resolve()
        if local_path.suffix.lower() != ".pdf":
            raise ValueError("Local WAS report reference must be a PDF artifact.")
        try:
            local_path.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError(
                "Local WAS report reference is outside the configured output directory."
            ) from error
        yield local_path
        return

    bucket, key = parse_s3_uri(report_reference)
    if PurePosixPath(key).suffix.lower() != ".pdf":
        raise ValueError("WAS report S3 URI must reference a PDF artifact.")
    validate_report_location(
        bucket=bucket,
        key=key,
        expected_bucket=expected_bucket,
        expected_prefix=expected_prefix,
    )
    client = s3_client or create_s3_client()
    with TemporaryDirectory(prefix="was-mailer-") as directory:
        local_path = Path(directory) / PurePosixPath(key).name
        client.download_file(bucket, key, str(local_path))
        local_path.chmod(0o600)
        if not local_path.is_file():
            raise FileNotFoundError("S3 download did not create a WAS report file.")
        yield local_path


def delete_report(
    report_reference: str,
    s3_client=None,
    expected_bucket: Optional[str] = None,
    expected_prefix: Optional[str] = None,
) -> None:
    """Logically delete the current S3 object after persistence failure."""
    bucket, key = parse_s3_uri(report_reference)
    validate_report_location(
        bucket=bucket,
        key=key,
        expected_bucket=expected_bucket,
        expected_prefix=expected_prefix,
    )
    client = s3_client or create_s3_client()
    client.delete_object(Bucket=bucket, Key=key)
