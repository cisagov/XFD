"""PostgreSQL connection utilities for the WAS reporting database."""

# Standard Python Libraries
import logging
from typing import Dict

# Third-Party Libraries
import psycopg2
from psycopg2 import OperationalError
from psycopg2.extensions import connection

# First-Party Libraries
from was_reports.utils.env import getenv, require_env

LOGGER = logging.getLogger(__name__)


def _require_environment_variable(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    return require_env(name)


def database_config() -> Dict[str, str]:
    """Return PostgreSQL connection settings for the WAS database."""
    return {
        "host": _require_environment_variable("WAS_DB_HOST"),
        "database": _require_environment_variable("WAS_DB_NAME"),
        "user": _require_environment_variable("WAS_DB_USERNAME"),
        "password": _require_environment_variable("WAS_DB_PASSWORD"),
        "port": getenv("WAS_DB_PORT", "5432"),
        "sslmode": getenv("WAS_DB_SSLMODE", "require"),
    }


def connect() -> connection:
    """Create and return a PostgreSQL connection for the WAS database."""
    try:
        return psycopg2.connect(**database_config())
    except OperationalError as error:
        LOGGER.error("Unable to connect to WAS database: %s", error)
        raise


def close(conn: connection) -> None:
    """Close a PostgreSQL connection."""
    conn.close()
