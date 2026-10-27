"""Tests for WAS operation leases and retained application logs."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.data import report_runs
from was_reports.utils import logging_config, operation_lease


class OperationReliabilityTests(unittest.TestCase):
    """Validate stale-operation recovery, heartbeats, and log cleanup."""

    def test_recover_stale_operations_fails_generation_and_holds_email(
        self,
    ) -> None:
        """Recover stale work without blindly retrying uncertain email."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1, [])
        cursor.fetchall.return_value = [(8, None, "customer")]

        with patch.object(report_runs, "_positive_seconds", return_value=300):
            recovered = report_runs.recover_stale_report_operations(conn)

        self.assertEqual(recovered, (1, 1))
        self.assertEqual(cursor.execute.call_count, 2)
        generation_parameters = cursor.execute.call_args_list[0].args[1]
        email_parameters = cursor.execute.call_args_list[1].args[1]
        self.assertEqual(generation_parameters[0], report_runs.FAILED)
        self.assertEqual(generation_parameters[2], report_runs.RUNNING)
        self.assertEqual(email_parameters[0], report_runs.EMAIL_HELD)
        self.assertEqual(email_parameters[2], report_runs.EMAIL_SENDING)
        conn.commit.assert_called_once_with()

    def test_operation_heartbeat_starts_and_stops_worker(self) -> None:
        """Start one bounded heartbeat worker around long-running work."""
        heartbeat = Mock(return_value=True)
        with patch.object(operation_lease, "Thread") as thread_class, patch.object(
            operation_lease,
            "heartbeat_seconds",
            return_value=30,
        ):
            thread_class.return_value.is_alive.return_value = False
            with operation_lease.operation_heartbeat(heartbeat, "test operation"):
                pass

        thread = thread_class.return_value
        thread.start.assert_called_once_with()
        thread.join.assert_called_once_with(timeout=31)

    def test_thread_start_failure_restores_ownership_context(self) -> None:
        """Do not leak a dead operation guard when worker startup fails."""
        with patch.object(operation_lease, "Thread") as thread_class:
            thread_class.return_value.start.side_effect = RuntimeError("start failed")
            with self.assertRaises(RuntimeError):
                with operation_lease.operation_heartbeat(lambda: True, "test"):
                    self.fail("Work must not begin when the heartbeat cannot start.")
        self.assertIsNone(operation_lease.CURRENT_OWNERSHIP_CHECK.get())

    def test_remove_expired_logs_preserves_recent_files(self) -> None:
        """Delete WAS logs older than retention without removing recent logs."""
        with tempfile.TemporaryDirectory() as directory:
            log_directory = Path(directory)
            expired_log = log_directory / "was-reporting-expired.log"
            recent_log = log_directory / "was-reporting-recent.log"
            expired_log.write_text("old", encoding="utf-8")
            recent_log.write_text("new", encoding="utf-8")
            expired_time = datetime.now(timezone.utc) - timedelta(days=15)
            os.utime(
                expired_log,
                (expired_time.timestamp(), expired_time.timestamp()),
            )

            logging_config.remove_expired_logs(log_directory, retention_days=14)

            self.assertFalse(expired_log.exists())
            self.assertTrue(recent_log.exists())


if __name__ == "__main__":
    unittest.main()
