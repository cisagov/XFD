"""Database and API configuration from environment variables."""

# Standard Python Libraries
import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def config(filename=None, section="postgres"):
    """Return PostgreSQL connection parameters for direct psycopg2 access."""
    del filename, section
    return {
        "host": os.environ.get("DB_HOST", os.environ.get("PE_DB_HOST", "localhost")),
        "database": _require("PE_DB_NAME"),
        "user": _require("PE_DB_USERNAME"),
        "password": _require("PE_DB_PASSWORD"),
        "port": os.environ.get("PE_DB_PORT", "5432"),
    }


def staging_config(filename=None, section="pe_api"):
    """Return PE API credentials used by scan workers."""
    del filename
    if section == "pe_api":
        base_url = os.environ.get("PE_API_URL", "http://127.0.0.1:8000").rstrip("/")
        if not base_url.endswith("/apiv1"):
            base_url = f"{base_url}/apiv1"
        if not base_url.endswith("/"):
            base_url = f"{base_url}/"
        return {
            "pe_api_url": base_url,
            "pe_api_key": os.environ.get("PE_API_KEY", ""),
        }
    return {}


def db_password_key() -> str:
    """Return the symmetric key used to PGP-decrypt per-org report passwords."""
    return _require("PE_DB_PASSWORD_KEY")


def reports_bucket_name() -> str:
    """Return the S3 bucket name containing generated report PDFs."""
    return _require("PE_REPORTS_BUCKET_NAME")


PE_API_REQUEST_TIMEOUT = int(os.environ.get("PE_API_REQUEST_TIMEOUT", "60"))
