"""Production entrypoint safety and shared-engine regression coverage."""

import os
import unittest
from unittest.mock import MagicMock, patch

from was_reports.commands import batch_coordinator


class BatchCoordinatorTests(unittest.TestCase):
    """Verify production cannot accidentally enter the isolated capacity route."""

    def test_default_and_unlimited_window(self):
        """Normal and explicitly unlimited batches retain their selection windows."""
        arguments = batch_coordinator.parse_args([])
        self.assertEqual(arguments.workers, 30)
        self.assertEqual(arguments.worker_backend, "docker")
        self.assertEqual(arguments.days_back, 7)
        self.assertFalse(arguments.apply)
        self.assertIsNone(batch_coordinator.parse_args(["--days-back", "all"]).days_back)

    def test_invalid_workers_and_windows(self):
        """Invalid execution configuration fails before connecting."""
        for option in (["--workers", "31"], ["--days-back", "0"],
                       ["--lookback-days", "0"], ["--max-seconds", "0"],
                       ["--test-recipients", ""], ["--test-recipients", "   "]):
            with self.subTest(option=option), self.assertRaises(SystemExit):
                batch_coordinator.parse_args(option)

    def test_capacity_environment_rejected_before_connect(self):
        """An inherited capacity scope never reaches the production database."""
        for setting in ({"WAS_RUN_MODE": "capacity"}, {"WAS_CAPACITY_TRACKER_IDS": "[]"}):
            with patch.dict(os.environ, setting, clear=True), patch.object(
                batch_coordinator, "connect"
            ) as connect, self.assertRaises(ValueError):
                batch_coordinator.guard_database(batch_coordinator.parse_args([]))
            connect.assert_not_called()

    def test_capacity_identity_rejected(self):
        """Neither a capacity database nor its dedicated role is production."""
        for identity in (("was_capacity_test", "was_app"), ("was", "was_capacity_test_user")):
            with patch.dict(os.environ, {}, clear=True), patch.object(
                batch_coordinator, "require_env", side_effect=identity
            ), patch.object(batch_coordinator, "connect") as connect, self.assertRaises(ValueError):
                batch_coordinator.guard_database(batch_coordinator.parse_args([]))
            connect.assert_not_called()

    def test_database_guard_allows_completed_pending_but_not_active(self):
        """Completed deliveries may resume, but ambiguous active operations cannot."""
        for active in (False, True):
            connection = MagicMock()
            cursor = connection.cursor.return_value.__enter__.return_value
            cursor.fetchone.side_effect = [("was", "was_app"), (True,), (False,), (active,)]
            with patch.dict(os.environ, {}, clear=True), patch.object(
                batch_coordinator, "require_env", side_effect=("was", "was_app")
            ), patch.object(batch_coordinator, "connect", return_value=connection):
                arguments = batch_coordinator.parse_args(["--apply"])
                if active:
                    with self.assertRaises(ValueError):
                        batch_coordinator.guard_database(arguments)
                    connection.close.assert_called_once()
                else:
                    self.assertIs(batch_coordinator.guard_database(arguments), connection)
                    connection.rollback.assert_called_once()
            operation_query = cursor.execute.call_args.args[0]
            self.assertNotIn("completed", operation_query)

    def test_guard_identity_lock_and_duplicate_failures(self):
        """Failed checks release the connection and any session lock."""
        for results in ([('other', 'was_app')], [("was", "was_app"), (False,)],
                        [("was", "was_app"), (True,), (True,)]):
            connection = MagicMock()
            connection.cursor.return_value.__enter__.return_value.fetchone.side_effect = results
            with patch.dict(os.environ, {}, clear=True), patch.object(
                batch_coordinator, "require_env", side_effect=("was", "was_app")
            ), patch.object(batch_coordinator, "connect", return_value=connection), self.assertRaises(ValueError):
                batch_coordinator.guard_database(batch_coordinator.parse_args(["--apply"]))
            connection.close.assert_called_once()

    def test_preview_never_executes_engine(self):
        """Default preview only performs read-only checks and releases resources."""
        connection = MagicMock()
        with patch.object(batch_coordinator, "load_env_file"), patch.object(
            batch_coordinator, "guard_database", return_value=connection
        ), patch.object(batch_coordinator.capacity_test, "verify_worker_backend"), patch.object(
            batch_coordinator.capacity_test, "run_coordinated", create=True
        ) as execute:
            self.assertEqual(batch_coordinator.main([]), 0)
        execute.assert_not_called()
        connection.close.assert_called_once()

    def test_apply_uses_shared_engine_and_validated_override(self):
        """Production and analyst test runs invoke the same capacity-tested engine."""
        for recipients in (None, "analyst@example.gov"):
            connection = MagicMock()
            options = ["--apply"] + (["--test-recipients", recipients] if recipients else [])
            with patch.object(batch_coordinator, "load_env_file"), patch.object(
                batch_coordinator, "guard_database", return_value=connection
            ), patch.object(batch_coordinator.capacity_test, "verify_worker_backend"), patch.object(
                batch_coordinator, "require_env", return_value="configured"
            ), patch.object(batch_coordinator, "approved_analyst_recipients", return_value=[recipients]) as approved, patch.object(
                batch_coordinator.capacity_test, "run_coordinated", return_value=0, create=True
            ) as execute:
                self.assertEqual(batch_coordinator.main(options), 0)
            self.assertEqual(execute.call_args.args[0].run_mode, "production")
            self.assertEqual(execute.call_args.args[1], recipients)
            self.assertEqual(approved.call_count, int(recipients is not None))
            connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
