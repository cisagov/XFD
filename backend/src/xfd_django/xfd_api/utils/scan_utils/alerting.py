"""Contains custom exceptions to be thrown when a scan fails."""
# Standard Python Libraries
import json
import logging

LOGGER = logging.getLogger(__name__)


def build_and_write_log(exception, scan_name, details, context):
    """
    Write a log to CloudWatch for the given exception.

    Args:
        exception (str): The exception type.
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict): Extra debugging context.
    """
    search_pattern = f"[ERROR]::{exception}::{scan_name}"

    log_payload = {
        "level": "ERROR",
        "exception": exception,
        "scan_name": scan_name,
        "details": details,
        "context": context,
        "search_pattern": search_pattern,
    }

    LOGGER.error(json.dumps(log_payload))


class ScanError(Exception):
    """Base class for all scan-related exceptions."""

    def __init__(self, scan_name, details, context=None, exception="ScanError"):
        """Initialize the ScanError with given parameters."""
        context = context or {}
        self.scan_name = scan_name
        self.exception = exception
        self.details = details
        self.context = context
        # Write a log to CloudWatch
        build_and_write_log(self.exception, self.scan_name, self.details, self.context)


class ScanExecutionError(ScanError):
    """
    Thrown when a generic exception occurs during scan execution.

    Args:
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict, optional): Extra debugging context. Defaults to None.

    Example:
        >>> raise ScanExecutionError("VS Scan", str(e), {"scan_id": "12345"}) from e
    """

    def __init__(self, scan_name, details, context=None):
        """Initialize the ScanError with given parameters, passes exception name to base class."""
        super().__init__(scan_name, details, context, "ScanExecutionError")


class ScanTimeoutError(ScanError):
    """
    Thrown when a request made by the scan execution times out.

    Args:
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict, optional): Extra debugging context. Defaults to None.

    Example:
        >>> raise ScanTimeoutError("VS Scan", "Scan execution timed out", {"timeout": "30s"}) from e
    """

    def __init__(self, scan_name, details, context=None):
        """Initialize the ScanError with given parameters, passes exception name to base class."""
        super().__init__(scan_name, details, context, "ScanTimeoutError")


class ScanNotFoundError(ScanError):
    """
    Thrown when a scan is not found. Generally points to configuration issues within scan schema.

    Args:
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict, optional): Extra debugging context. Defaults to None.

    Example:
        >>> raise ScanNotFoundError("VS Scan", "Scan not found in configuration", {"scan_id": "12345"}) from e
    """

    def __init__(self, scan_name, details, context=None):
        """Initialize the ScanError with given parameters, passes exception name to base class."""
        super().__init__(scan_name, details, context, "ScanNotFoundError")


class QueryError(ScanError):
    """
    Thrown when a query against a database fails.

    Args:
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict, optional): Extra debugging context. Defaults to None.

    Example:
        >>> raise QueryError("VS Scan", str(e), {"query": "SELECT * FROM table"}) from e
    """

    def __init__(self, scan_name, details, context=None):
        """Initialize the ScanError with given parameters, passes exception name to base class."""
        super().__init__(scan_name, details, context, "QueryError")


class IngestionError(ScanError):
    """
    Thrown when an ingestion process fails against a database we control.

    Args:
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict, optional): Extra debugging context. Defaults to None.

    Example:
        >>> raise IngestionError("VS Scan", str(e), {"endpoint": "/ingest"}) from e
    """

    def __init__(self, scan_name, details, context=None):
        """Initialize the ScanError with given parameters, passes exception name to base class."""
        super().__init__(scan_name, details, context, "IngestionError")


class SyncError(ScanError):
    """
    Thrown when a sync process fails against a sync API we control.

    Args:
        scan_name (str): The name of the scan or job that failed.
        details (str): Additional information about the failure.
        context (dict, optional): Extra debugging context. Defaults to None.

    Example:
        >>> raise SyncError("VS Scan", str(e), {"endpoint": "/sync"}) from e
    """

    def __init__(self, scan_name, details, context=None):
        """Initialize the ScanError with given parameters, passes exception name to base class."""
        super().__init__(scan_name, details, context, "SyncError")
