"""xfd_django.helpers.log_helpers project‑wide logging helpers.

This module registers ``XfdLogger`` as the default logger class and
installs a factory that automatically prefixes every logger name with
“xfd.” so the central LOGGING configuration can target the entire
project with a single stanza.
"""
# Standard Python Libraries
from datetime import datetime, timezone
import json
import logging


class XfdLogger(logging.Logger):
    """Logger subclass whose children automatically live under ``xfd.``."""

    def getChild(self, suffix: str):
        """Return a child logger, making sure its name starts with ``xfd.``."""
        if suffix and not suffix.startswith("xfd."):
            suffix = "xfd.{}".format(suffix)
        return super().getChild(suffix)


def install_xfd_prefix():
    """
    Make ``logging.getLogger()`` return loggers in the ``xfd.`` hierarchy.

    Must be called **once**, early in ``settings.py`` *before* any project
    modules import ``logging``.
    """
    logging.setLoggerClass(XfdLogger)

    _orig_get_logger = logging.getLogger

    def prefixed_get_logger(name=None):
        if name and not name.startswith("xfd."):
            name = "xfd.{}".format(name)
        if name is None:
            name = "xfd"
        return _orig_get_logger(name)

    logging.getLogger = prefixed_get_logger


# Context fields copied from a LogRecord into the JSON output when present.
CONTEXT_FIELDS = (
    "scan_name",
    "scan_id",
    "is_global",
    "organization_name",
    "organization_id",
)


class JsonFormatter(logging.Formatter):
    """Custom logging formatter outputting JSON strings for CloudWatch Insights."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_record = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Inject scan/organization context if present on the record
        for key in CONTEXT_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                log_record[key] = value

        # Preserve stack traces for exception logs
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)

        # default=str keeps a non-serializable value from breaking the log call
        return json.dumps(log_record, default=str)


class LogContextFilter(logging.Filter):
    """Stamp shared context (e.g. scan_name, scan_id) onto every record.

    Attach it to handlers rather than loggers: handler filters run for
    records propagated from child loggers, so one filter covers every
    module that logs through those handlers. Fields set explicitly on a
    record (via ``extra=``) take precedence.
    """

    def __init__(self, **context):
        """Initialize the filter with the given context fields."""
        super().__init__()
        self.context = dict(context)

    def update(self, **context):
        """Add or replace context fields (e.g. per organization)."""
        self.context.update(context)

    def filter(self, record: logging.LogRecord) -> bool:
        """Copy context onto the record without overriding existing fields."""
        for key, value in self.context.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


def install_log_context(loggers=None, **context) -> LogContextFilter:
    """Attach a ``LogContextFilter`` to the handlers of the given loggers.

    Defaults to the ``xfd`` project logger and the root logger, which
    between them handle every log record the worker and its tasks emit.
    Returns the filter so callers can ``update()`` it later.
    """
    if loggers is None:
        # logging.getLogger() is patched to return "xfd"; use logging.root
        loggers = [logging.getLogger("xfd"), logging.root]

    context_filter = LogContextFilter(**context)
    seen = set()
    for logger in loggers:
        for handler in logger.handlers:
            if id(handler) not in seen:
                seen.add(id(handler))
                handler.addFilter(context_filter)
    return context_filter
