"""Tests for structured JSON logging and worker context enrichment."""

# Standard Python Libraries
from datetime import datetime
from io import StringIO
import json
import logging

# Third-Party Libraries
from django.test import SimpleTestCase
from xfd_django.helpers.log_helpers import (
    JsonFormatter,
    LogContextFilter,
    install_log_context,
)


class LoggingTestCase(SimpleTestCase):
    """Test suite for structured JSON logging and scan context."""

    def setUp(self):
        """Set up an isolated logger hierarchy writing JSON to a buffer."""
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(JsonFormatter())

        # Stands in for the "xfd" project logger the worker's handlers live on
        self.logger = logging.getLogger("test_logging_parent")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False  # keep test output off the console
        self.logger.addHandler(self.handler)

        # Stands in for a task module logger, e.g. xfd_api.tasks.shodan
        self.task_logger = logging.getLogger("test_logging_parent.tasks.shodan")

    def tearDown(self):
        """Clean up log handlers after each test."""
        self.logger.removeHandler(self.handler)

    def _records(self):
        """Return every emitted log line parsed as JSON."""
        return [json.loads(line) for line in self.stream.getvalue().splitlines()]

    def test_json_formatter_basic_output(self):
        """Verify standard log messages format into JSON."""
        self.logger.info("Worker event started")
        (data,) = self._records()

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["message"], "Worker event started")
        self.assertEqual(data["logger"], self.logger.name)
        self.assertEqual(data["function"], "test_json_formatter_basic_output")
        self.assertIsInstance(data["line"], int)
        # ISO-8601 UTC timestamp with milliseconds
        self.assertTrue(data["timestamp"].endswith("+00:00"))
        datetime.fromisoformat(data["timestamp"])

    def test_json_formatter_omits_missing_context(self):
        """Verify context keys are absent, not null, when no context is set."""
        self.logger.info("No context here")
        (data,) = self._records()

        self.assertNotIn("scan_name", data)
        self.assertNotIn("scan_id", data)
        self.assertNotIn("is_global", data)

    def test_json_formatter_includes_exception(self):
        """Verify exception tracebacks are preserved."""
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            self.logger.exception("Scan failed")
        (data,) = self._records()

        self.assertEqual(data["message"], "Scan failed")
        self.assertIn("RuntimeError: boom", data["exception"])

    def test_json_formatter_handles_unserializable_values(self):
        """Verify a non-JSON-serializable context value does not break logging."""
        self.logger.info("Odd value", extra={"scan_id": object()})
        (data,) = self._records()

        self.assertIn("object object", data["scan_id"])

    def test_install_log_context_tags_task_module_logs(self):
        """Verify context reaches logs from child (task module) loggers."""
        install_log_context(
            loggers=[self.logger],
            scan_name="shodan",
            scan_id="scan-abc-123",
            is_global=True,
        )
        self.logger.info("Executing scan")
        self.task_logger.info("Task doing work")

        records = self._records()
        self.assertEqual(len(records), 2)
        for data in records:
            self.assertEqual(data["scan_name"], "shodan")
            self.assertEqual(data["scan_id"], "scan-abc-123")
            self.assertIs(data["is_global"], True)

    def test_log_context_update_adds_organization(self):
        """Verify per-organization context can be added after install."""
        context = install_log_context(
            loggers=[self.logger], scan_name="shodan", scan_id="scan-abc-123"
        )
        context.update(organization_name="Example Org", organization_id="org-1")
        self.task_logger.info("Processing organization")
        (data,) = self._records()

        self.assertEqual(data["scan_name"], "shodan")
        self.assertEqual(data["organization_name"], "Example Org")
        self.assertEqual(data["organization_id"], "org-1")

    def test_log_context_clearing_organization_removes_fields(self):
        """Verify clearing org context stops it leaking into later logs."""
        context = install_log_context(loggers=[self.logger], scan_name="shodan")
        context.update(organization_name="Example Org", organization_id="org-1")
        self.task_logger.info("Processing organization")

        context.update(organization_name=None, organization_id=None)
        self.logger.info("No more messages in the queue.")

        org_log, queue_log = self._records()
        self.assertEqual(org_log["organization_name"], "Example Org")
        self.assertNotIn("organization_name", queue_log)
        self.assertNotIn("organization_id", queue_log)
        self.assertEqual(queue_log["scan_name"], "shodan")

    def test_explicit_extra_overrides_context(self):
        """Verify fields passed via extra= take precedence over the filter."""
        self.handler.addFilter(LogContextFilter(scan_name="shodan"))
        self.task_logger.info("Override", extra={"scan_name": "censys"})
        (data,) = self._records()

        self.assertEqual(data["scan_name"], "censys")
