"""Centralized console and retained file logging for WAS commands."""

# Standard Python Libraries
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from typing import Iterator
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
LOG_FORMAT = (
    "%(asctime)sZ %(levelname)s %(name)s %(filename)s:%(lineno)d "
    "batch=%(batch_id)s role=%(role)s worker=%(worker)s phase=%(phase)s "
    "tag=%(tag)s tracker=%(tracker_id)s report_run=%(report_run_id)s "
    "event=%(event)s %(message)s"
)
_CONFIGURED_LOG_PATH: Path | None = None
_LOG_CONTEXT: ContextVar[dict[str, object]] = ContextVar(
    "was_log_context", default={}
)
CONTEXT_FIELDS = (
    "batch_id",
    "role",
    "worker",
    "phase",
    "tag",
    "tracker_id",
    "report_run_id",
    "event",
)


def _safe_component(value: str | None, fallback: str) -> str:
    """Return one filesystem-safe logging identity without regular expressions."""
    normalized = (value or "").strip()
    if not normalized or len(normalized) > 128:
        return fallback
    if not all(character.isalnum() or character in "-_." for character in normalized):
        return fallback
    return normalized


def _environment_context() -> dict[str, object]:
    """Return process-wide log correlation fields from non-secret settings."""
    return {
        "batch_id": getenv("WAS_ANALYST_BATCH_ID", "-") or "-",
        "role": getenv("WAS_LOG_ROLE", "command") or "command",
        "worker": getenv("WAS_LOG_WORKER_INDEX", "-") or "-",
        "phase": getenv("WAS_LOG_PHASE", "-") or "-",
    }


class LoggingContextFilter(logging.Filter):
    """Populate stable correlation fields on every application log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add process and operation context without replacing explicit fields."""
        values = dict(_environment_context())
        values.update(_LOG_CONTEXT.get())
        for field_name in CONTEXT_FIELDS:
            if not hasattr(record, field_name):
                setattr(record, field_name, values.get(field_name, "-"))
        return True


@contextmanager
def logging_context(**fields: object) -> Iterator[None]:
    """Temporarily add safe correlation fields to logs in the current context."""
    token = bind_logging_context(**fields)
    try:
        yield
    finally:
        reset_logging_context(token)


def bind_logging_context(**fields: object):
    """Bind correlation fields until the returned context token is reset."""
    invalid_fields = set(fields) - set(CONTEXT_FIELDS)
    if invalid_fields:
        raise ValueError("Unsupported logging context field.")
    current = dict(_LOG_CONTEXT.get())
    current.update(
        {
            field_name: value if value not in (None, "") else "-"
            for field_name, value in fields.items()
        }
    )
    return _LOG_CONTEXT.set(current)


def reset_logging_context(token) -> None:
    """Restore the logging context represented by a prior binding token."""
    _LOG_CONTEXT.reset(token)


class PrivateJsonLineHandler(logging.Handler):
    """Append structured, private log records for deterministic diagnostics."""

    def __init__(self, filename: Path):
        """Store the JSON-lines destination without keeping a shared stream open."""
        super().__init__()
        self.filename = filename

    def emit(self, record: logging.LogRecord) -> None:
        """Write one bounded JSON record using a single append operation."""
        try:
            timestamp = datetime.fromtimestamp(record.created, timezone.utc).isoformat()
            payload = {
                "time": timestamp,
                "level": record.levelname,
                "logger": record.name,
                "source": record.filename,
                "line": record.lineno,
                "message": record.getMessage()[:4096],
            }
            for field_name in CONTEXT_FIELDS:
                payload[field_name] = getattr(record, field_name, "-")
            encoded = (json.dumps(payload, sort_keys=True, default=str) + "\n").encode(
                "utf-8"
            )
            descriptor = os.open(
                self.filename,
                os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                0o600,
            )
            try:
                os.write(descriptor, encoded)
            finally:
                os.close(descriptor)
        except (OSError, TypeError, ValueError):
            return


def exception_details(error: Exception, include_origin: bool = True) -> str:
    """Describe failures without logging SQL values, URLs, or response bodies."""
    details = [type(error).__name__]
    traceback = error.__traceback__
    if include_origin and traceback is not None:
        while traceback.tb_next is not None:
            traceback = traceback.tb_next
        details.append(
            "origin={}:{}".format(
                traceback.tb_frame.f_code.co_filename,
                traceback.tb_lineno,
            )
        )
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
        LOG_FORMAT,
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    formatter.converter = __import__("time").gmtime
    context_filter = LoggingContextFilter()

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
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
        role = _safe_component(getenv("WAS_LOG_ROLE"), "")
        if role:
            worker = _safe_component(getenv("WAS_LOG_WORKER_INDEX"), "")
            filename = "{}{}.log".format(
                role,
                "-{}".format(worker) if worker else "",
            )
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = "{}{}-{}-{}.log".format(
                LOG_FILENAME_PREFIX,
                timestamp,
                os.getpid(),
                uuid4().hex[:12],
            )
        log_path = log_directory / filename
        descriptor = os.open(
            log_path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        os.close(descriptor)
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
        file_handler.addFilter(context_filter)
        setattr(file_handler, HANDLER_MARKER, True)
        root_logger.addHandler(file_handler)
        json_handler = PrivateJsonLineHandler(
            Path("{}.jsonl".format(log_path))
        )
        json_handler.addFilter(context_filter)
        setattr(json_handler, HANDLER_MARKER, True)
        root_logger.addHandler(json_handler)
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
