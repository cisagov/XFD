"""Safety regressions for database-only capacity baseline restoration."""

from contextlib import redirect_stdout
from io import StringIO
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from was_reports.commands import capacity_database_reset as reset


class CapacityDatabaseResetTests(unittest.TestCase):
    """Verify isolation, credential handling, and explicit mutation controls."""

    def environment(self, prefix, database, username):
        """Build synthetic environment settings without real credentials."""
        values = {"HOST": "example.invalid", "NAME": database, "USERNAME": username,
                  "PASSWORD": "synthetic-password", "PORT": "5432", "SSLMODE": "require",
                  "CONNECT_TIMEOUT_SECONDS": "10"}
        return {prefix + name: value for name, value in values.items()}

    def test_missing_test_settings_never_use_ordinary_values(self):
        """Require a complete explicit target even when source values exist."""
        source = self.environment("WAS_DB_", "was", "was_app")
        target = self.environment("TEST_WAS_DB_", "was_capacity_test", "was_capacity_test_user")
        for missing in target:
            environment = dict(source)
            environment.update({name: value for name, value in target.items() if name != missing})
            with self.subTest(missing=missing), patch.dict(os.environ, environment, clear=True):
                with self.assertRaises(ValueError):
                    reset.load_settings("TEST_WAS_DB_", "was_capacity_test")

    def test_operational_database_cannot_be_target(self):
        """Refuse settings naming the operational database before any connection."""
        environment = self.environment("TEST_WAS_DB_", "was", "was_capacity_test_user")
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(ValueError):
                reset.load_settings("TEST_WAS_DB_", "was_capacity_test")

    def test_postgres_environment_scrubs_ambient_routing(self):
        """Service files and PG options must not redirect or weaken a connection."""
        environment = self.environment("WAS_DB_", "was", "was_app")
        environment.update({"PGSERVICE": "production-admin", "PGOPTIONS": "unsafe",
                            "PGHOST": "wrong-host", "PGDATABASE": "wrong-db"})
        with patch.dict(os.environ, environment, clear=True):
            settings = reset.load_settings("WAS_DB_", "was")
            child = reset.postgres_environment(settings, readonly=True)
        self.assertNotIn("PGSERVICE", child)
        self.assertEqual(child["PGHOST"], "example.invalid")
        self.assertEqual(child["PGDATABASE"], "was")
        self.assertIn("default_transaction_read_only=on", child["PGOPTIONS"])
        self.assertEqual(child["PGSSLMODE"], "require")

    def test_preview_never_executes_reset(self):
        """Default mode only checks prerequisites, without dumps or restore."""
        environment = self.environment("WAS_DB_", "was", "was_app")
        environment.update(self.environment("TEST_WAS_DB_", "was_capacity_test",
                                            "was_capacity_test_user"))
        with TemporaryDirectory() as directory, patch.dict(os.environ, environment, clear=True), patch.object(
            reset, "load_env_file"
        ), patch.object(reset, "verify_database"), patch.object(reset, "execute_reset") as execute:
            with redirect_stdout(StringIO()):
                self.assertEqual(reset.main(["--output-directory", directory]), 0)
            execute.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])

    def run_reset(self, directory, tool_failure=None):
        """Exercise real orchestration while replacing database and tool boundaries."""
        environment = self.environment("WAS_DB_", "was", "was_app")
        environment.update(self.environment("TEST_WAS_DB_", "was_capacity_test",
                                            "was_capacity_test_user"))
        calls = []

        def record_tool(arguments, child_environment, log_path):
            """Record tool invocations and optionally simulate one failed stage."""
            calls.append((arguments, child_environment, log_path))
            if len(calls) == tool_failure:
                raise RuntimeError("simulated tool failure")

        with patch.dict(os.environ, environment, clear=True), patch.object(
            reset, "verify_database"
        ), patch.object(reset.shutil, "which", side_effect=lambda name: "/bin/" + name), patch.object(
            reset, "run_tool", side_effect=record_tool
        ), redirect_stdout(StringIO()):
            source = reset.load_settings("WAS_DB_", "was")
            target = reset.load_settings("TEST_WAS_DB_", "was_capacity_test")
            if tool_failure:
                with self.assertRaises(RuntimeError):
                    reset.execute_reset(source, target, directory)
                operation = next(Path(directory).iterdir())
            else:
                operation = reset.execute_reset(source, target, directory)
        return calls, operation

    def test_restore_is_guarded_atomic_and_only_targets_test_database(self):
        """Back up both databases before one guarded restore/cleanup transaction."""
        with TemporaryDirectory() as directory:
            calls, operation = self.run_reset(directory)
            self.assertEqual([Path(call[0][0]).name for call in calls],
                             ["pg_dump", "pg_dump", "pg_restore", "psql"])
            self.assertEqual(calls[0][1]["PGDATABASE"], "was")
            self.assertEqual(calls[1][1]["PGDATABASE"], "was_capacity_test")
            for call in calls[:2]:
                self.assertIn("default_transaction_read_only=on", call[1]["PGOPTIONS"])
            command, environment, log_path = calls[-1]
            self.assertEqual(environment["PGDATABASE"], "was_capacity_test")
            self.assertIn("--single-transaction", command)
            self.assertIn("--set=ON_ERROR_STOP=1", command)
            self.assertIn("-X", command)
            files = [Path(command[index + 1]).name for index, value in enumerate(command)
                     if value == "--file"]
            self.assertEqual(files, ["guard.sql", "restore.sql", "cleanup.sql"])
            for arguments, child_environment, log in calls:
                self.assertNotIn("synthetic-password", str(arguments))
            self.assertEqual(stat.S_IMODE(operation.stat().st_mode), 0o700)
            for path in operation.iterdir():
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertIn("current_database() <> 'was_capacity_test'", reset.GUARD_SQL)
            self.assertIn("pg_try_advisory_xact_lock", reset.GUARD_SQL)
            self.assertNotIn("was_daily_report_tracker", reset.CLEANUP_SQL)
            self.assertNotIn("was_assignees", reset.CLEANUP_SQL)

    def test_backup_or_render_failure_prevents_restore(self):
        """Never mutate the destination if a preceding archive step failed."""
        for stage in (1, 2, 3):
            with self.subTest(stage=stage), TemporaryDirectory() as directory:
                calls, operation = self.run_reset(directory, tool_failure=stage)
                self.assertEqual(len(calls), stage)
                self.assertFalse(any(Path(call[0][0]).name == "psql" for call in calls))

    def test_grants_without_ownership_are_rejected(self):
        """An application role with only table grants cannot perform full restore."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            ("was_capacity_test", "was_capacity_test_user", False, False, False),
            (True, True, False),
        ]
        settings = {"dbname": "was_capacity_test", "user": "was_capacity_test_user"}
        with patch.object(reset.psycopg2, "connect", return_value=connection) as connect:
            with self.assertRaises(ValueError):
                reset.verify_database(settings, target=True)
            self.assertIn("default_transaction_read_only=on", connect.call_args.kwargs["options"])
        connection.close.assert_called_once()

    def test_tool_failure_keeps_raw_output_private(self):
        """Tool failures expose only a safe summary, with private logs retained."""
        with TemporaryDirectory() as directory, patch.object(
            reset.subprocess, "run", return_value=MagicMock(returncode=1)
        ) as run:
            log_path = Path(directory) / "failure.log"
            with self.assertRaises(RuntimeError):
                reset.run_tool(["/bin/psql"], {"PGPASSWORD": "synthetic-password"}, log_path)
            self.assertEqual(stat.S_IMODE(log_path.stat().st_mode), 0o600)
            self.assertNotIn("synthetic-password", str(run.call_args.args))
            self.assertFalse(run.call_args.kwargs.get("shell", False))


if __name__ == "__main__":
    unittest.main()
