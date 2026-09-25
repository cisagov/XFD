"""Regression tests for private logs and useful, sanitized diagnostics."""

# Standard Python Libraries
import json
import logging
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

# Third-Party Libraries
import requests
from was_reports.utils.logging_config import (
    LOG_FORMAT,
    LoggingContextFilter,
    PrivateJsonLineHandler,
    PrivateRotatingFileHandler,
    exception_details,
    logging_context,
)


class LoggingConfigTests(unittest.TestCase):
    """Check error metadata without exposing external payloads."""

    def test_log_format_includes_source_file_and_line(self) -> None:
        """Identify the source location responsible for every log message."""
        self.assertIn("%(filename)s:%(lineno)d", LOG_FORMAT)
        for field in ("batch_id", "role", "worker", "phase", "tag", "tracker_id"):
            self.assertIn("%({})s".format(field), LOG_FORMAT)

    def test_context_filter_adds_operation_identity(self) -> None:
        """Attach tag and tracker identity without changing every log call."""
        record = logging.LogRecord("test", logging.ERROR, "file.py", 4, "failed", (), None)
        with logging_context(tag="TAG1", tracker_id=42, event="test_failure"):
            LoggingContextFilter().filter(record)
        self.assertEqual(record.tag, "TAG1")
        self.assertEqual(record.tracker_id, 42)
        self.assertEqual(record.event, "test_failure")

    def test_json_lines_are_private_and_structured(self) -> None:
        """Write one parseable record with private filesystem permissions."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "worker-01.jsonl"
            handler = PrivateJsonLineHandler(path)
            handler.addFilter(LoggingContextFilter())
            record = logging.LogRecord(
                "test.logger", logging.ERROR, "worker.py", 8, "safe failure", (), None
            )
            with logging_context(tag="TAG1", tracker_id=42, event="test_failure"):
                handler.handle(record)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["tag"], "TAG1")
            self.assertEqual(payload["tracker_id"], 42)
            self.assertEqual(payload["event"], "test_failure")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

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

    def test_exception_details_include_original_failure_location(self) -> None:
        """Identify the traceback frame where a handled exception originated."""
        try:
            raise RuntimeError("sensitive failure text")
        except RuntimeError as error:
            details = exception_details(error)

        self.assertIn("RuntimeError", details)
        self.assertIn("origin=", details)
        self.assertIn("test_logging_config.py:", details)
        self.assertNotIn("sensitive failure text", details)

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
