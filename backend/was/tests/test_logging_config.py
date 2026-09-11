"""Regression tests for private logs and useful, sanitized diagnostics."""

# Standard Python Libraries
import logging
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

# Third-Party Libraries
import requests
from was_reports.utils.logging_config import (
    PrivateRotatingFileHandler,
    exception_details,
)


class LoggingConfigTests(unittest.TestCase):
    """Check error metadata without exposing external payloads."""

    def test_sql_details_exclude_statement_and_values(self) -> None:
        """Keep a useful missing-column diagnostic without SQL parameter values."""
        error = RuntimeError("password=do-not-log")
        setattr(error, "pgcode", "42703")
        setattr(
            error,
            "diag",
            SimpleNamespace(
                column_name=None,
                table_name="was_report_runs",
                message_primary='column "generation_token" does not exist',
            ),
        )
        details = exception_details(error)
        self.assertIn("SQLSTATE=42703", details)
        self.assertIn("column_name=generation_token", details)
        self.assertNotIn("do-not-log", details)

    def test_http_details_exclude_url_and_response_body(self) -> None:
        """Expose an HTTP status but neither credentials nor payloads."""
        response = requests.Response()
        response.status_code = 403
        response._content = b"sensitive body"
        error = requests.HTTPError(
            "https://secret.example/?token=secret", response=response
        )
        self.assertEqual(exception_details(error), "HTTPError; HTTP=403")

    def test_rotated_logs_remain_private(self) -> None:
        """Both the active file and rotated backup require owner access."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.log"
            handler = PrivateRotatingFileHandler(path, maxBytes=10, backupCount=1)
            try:
                record = logging.LogRecord(
                    "test", logging.INFO, "", 1, "test record", (), None
                )
                handler.emit(record)
                handler.emit(record)
            finally:
                handler.close()
            for log_path in Path(directory).iterdir():
                self.assertEqual(log_path.stat().st_mode & 0o777, 0o600)
