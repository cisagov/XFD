"""Deterministic tests for optional capacity diagnostics."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import requests

from was_reports.qualys.qualys_client import QualysClient, QualysRequest, QualysRetryPolicy
from was_reports.utils import capacity_telemetry as telemetry


class CapacityTelemetryTests(unittest.TestCase):
    """Keep telemetry optional, bounded, and free of request secrets."""

    def test_disabled_telemetry_does_not_open_files(self):
        """Normal runs do not create metric files unless explicitly configured."""
        with patch.dict(os.environ, {}, clear=True), patch.object(os, "open") as opened:
            telemetry.emit_metric("test")
        opened.assert_not_called()

    def test_metric_file_has_restricted_permissions(self):
        """Write structured metadata to a private process-local file."""
        with TemporaryDirectory() as directory, patch.dict(
            os.environ, {"WAS_METRICS_DIRECTORY": directory, "WAS_ANALYST_BATCH_ID": "test"}
        ):
            telemetry.emit_metric("test", duration_seconds=1.5)
            path = next(Path(directory).glob("*.jsonl"))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            record = json.loads(path.read_text())
            self.assertEqual(record["batch_id"], "test")
            self.assertEqual(record["duration_seconds"], 1.5)

    def test_write_failure_does_not_break_reports(self):
        """Observability failure warns instead of changing delivery outcome."""
        with patch.dict(os.environ, {"WAS_METRICS_DIRECTORY": "/unused"}), patch.object(
            Path, "mkdir", side_effect=OSError("unavailable")
        ), self.assertLogs(telemetry.LOGGER, level="WARNING"):
            telemetry.emit_metric("test")

    def test_unavailable_resources_are_unknown_not_zero(self):
        """Unsupported cgroup metrics must not appear as idle resources."""
        with patch.object(Path, "read_text", side_effect=OSError()), patch.object(
            telemetry.shutil, "disk_usage", side_effect=OSError()
        ):
            sample = telemetry.resource_sample(Path("/unused"))
        self.assertIsNone(sample["cpu_usage_usec"])
        self.assertIsNone(sample["memory_current_bytes"])

    def test_resource_monitor_stops_on_error(self):
        """Capture initial/final samples even when the tested workflow fails."""
        with patch.object(telemetry, "resource_sample", return_value={}), patch.object(
            telemetry, "emit_metric"
        ) as emit:
            with self.assertRaises(RuntimeError):
                with telemetry.resource_monitor("/unused", interval=60):
                    raise RuntimeError("test")
        self.assertEqual(emit.call_count, 2)

    def test_qualys_metrics_include_retry_but_not_payload(self):
        """Each attempt records only endpoint, timing and safe outcome metadata."""
        from unittest.mock import Mock

        connection = Mock()
        connection.request.side_effect = [requests.ReadTimeout("secret value"), "<ok/>"]
        client = QualysClient(connection, retry_policy=QualysRetryPolicy(), sleep_function=lambda _: None)
        with patch("was_reports.qualys.qualys_client.emit_metric") as emit:
            self.assertEqual(client.request(QualysRequest(
                endpoint="/search/was/finding?credential=secret", payload="private payload",
                http_method="POST", retry_safe=True,
            )), "<ok/>")
        self.assertEqual(emit.call_count, 2)
        self.assertEqual(emit.call_args_list[0].kwargs["outcome"], "ReadTimeout")
        self.assertEqual(emit.call_args_list[1].kwargs["attempt_number"], 2)
        serialized = str(emit.call_args_list)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("private payload", serialized)
