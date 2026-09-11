"""Centralized console and retained file logging for WAS commands."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from uuid import uuid4

# Third-Party Libraries
# First-Party Libraries
from was_reports.utils.env import getenv

DEFAULT_LOG_DIRECTORY = "/output/logs"
DEFAULT_LOG_MAX_BYTES = 10485760
DEFAULT_LOG_BACKUP_COUNT = 5
DEFAULT_RETENTION_DAYS = 14
HANDLER_MARKER = "was_reporting_handler"
LOG_FILENAME_PREFIX = "was-reporting-"
_CONFIGURED_LOG_PATH: Path | None = None


def exception_details(error: Exception) -> str:
    """Describe failures without logging SQL values, URLs, or response bodies."""
    details = [type(error).__name__]
    sqlstate = getattr(error, "pgcode", None)
    if isinstance(sqlstate, str) and sqlstate.isalnum():
        details.append("SQLSTATE={}".format(sqlstate))
    diagnostics = getattr(error, "diag", None)
    if sqlstate == "42703" and not getattr(diagnostics, "column_name", None):
        primary = getattr(diagnostics, "message_primary", "") or ""
        if primary.startswith('column "'):
            column_name = primary.split('"', 2)[1]
            if column_name and all(
                character.isalnum() or character in "_." for character in column_name
            ):
                details.append("column_name={}".format(column_name[:128]))
    for field_name in ("table_name", "column_name", "constraint_name"):
        value = getattr(diagnostics, field_name, None)
        if (
            isinstance(value, str)
            and value
            and all(character.isalnum() or character == "_" for character in value)
        ):
            details.append("{}={}".format(field_name, value[:128]))
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        details.append("HTTP={}".format(status_code))
    return "; ".join(details)


class PrivateRotatingFileHandler(RotatingFileHandler):
    """Keep newly created log files private, including after rotation."""

    def _open(self):
        """Open a log with owner-only permissions without changing the umask."""

        def private_opener(path: str, flags: int) -> int:
            """Create a private file descriptor for the logging stream."""
            return os.open(path, flags, 0o600)

        return open(
            self.baseFilename,
            self.mode,
            encoding=self.encoding,
            errors=self.errors,
            opener=private_opener,
        )


def positive_integer(name: str, default: int) -> int:
    """Return one positive integer from WAS environment configuration."""
    raw_value = getenv(name, str(default))
    try:
        value = int(raw_value or default)
    except ValueError as error:
        raise ValueError("{} must be an integer.".format(name)) from error
    if value < 1:
        raise ValueError("{} must be at least 1.".format(name))
    return value


def remove_expired_logs(log_directory: Path, retention_days: int) -> None:
    """Remove WAS log files whose modification time exceeds retention."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    for log_path in log_directory.glob("{}*.log*".format(LOG_FILENAME_PREFIX)):
        try:
            modified_at = datetime.fromtimestamp(
                log_path.stat().st_mtime,
                tz=timezone.utc,
            )
            if modified_at < cutoff:
                log_path.unlink()
        except OSError as error:
            logging.getLogger(__name__).warning(
                "Unable to inspect or remove expired WAS log %s: %s",
                log_path,
                error,
            )


def configure_logging() -> Path | None:
    """Configure stderr and a bounded, per-process application log."""
    global _CONFIGURED_LOG_PATH

    root_logger = logging.getLogger()
    if any(getattr(handler, HANDLER_MARKER, False) for handler in root_logger.handlers):
        return _CONFIGURED_LOG_PATH

    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = __import__("time").gmtime

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    setattr(console_handler, HANDLER_MARKER, True)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

    configured_directory = getenv("WAS_LOG_DIRECTORY", DEFAULT_LOG_DIRECTORY)
    if not configured_directory:
        return None
    log_directory = Path(configured_directory)
    try:
        log_directory.mkdir(parents=True, exist_ok=True)
        retention_days = positive_integer(
            "WAS_LOG_RETENTION_DAYS",
            DEFAULT_RETENTION_DAYS,
        )
        remove_expired_logs(log_directory, retention_days)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log_path = log_directory / "{}{}-{}-{}.log".format(
            LOG_FILENAME_PREFIX,
            timestamp,
            os.getpid(),
            uuid4().hex[:12],
        )
        log_path.touch(mode=0o600, exist_ok=False)
        file_handler = PrivateRotatingFileHandler(
            filename=log_path,
            maxBytes=positive_integer(
                "WAS_LOG_MAX_BYTES",
                DEFAULT_LOG_MAX_BYTES,
            ),
            backupCount=positive_integer(
                "WAS_LOG_BACKUP_COUNT",
                DEFAULT_LOG_BACKUP_COUNT,
            ),
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(formatter)
        setattr(file_handler, HANDLER_MARKER, True)
        root_logger.addHandler(file_handler)
        _CONFIGURED_LOG_PATH = log_path
        root_logger.info("WAS application log: %s", log_path)
    except OSError as error:
        root_logger.warning(
            "Unable to configure WAS log directory %s: %s",
            log_directory,
            error,
        )
        return None
    return log_path
