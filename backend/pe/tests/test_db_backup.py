"""Tests for the PE database backup script."""

# Standard Python Libraries
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import call, patch

# Third-Party Libraries
from botocore.exceptions import ClientError
from pe_source.db_backup import db_backup


class BackupConfigurationTests(unittest.TestCase):
    """Verify backup configuration and executable discovery."""

    @patch.dict(
        os.environ,
        {"DB_BACKUP_BUCKET_NAME": "  test-backup-bucket  "},
        clear=False,
    )
    def test_get_backup_bucket_name(self):
        """Return the configured bucket name without surrounding whitespace."""
        self.assertEqual(
            db_backup.get_backup_bucket_name(),
            "test-backup-bucket",
        )

    @patch.dict(os.environ, {"DB_BACKUP_BUCKET_NAME": ""}, clear=False)
    def test_missing_backup_bucket_name_raises(self):
        """Require the backup bucket environment variable."""
        with self.assertRaisesRegex(
            RuntimeError,
            "DB_BACKUP_BUCKET_NAME",
        ):
            db_backup.get_backup_bucket_name()

    @patch.object(db_backup.shutil, "which", return_value="/usr/bin/pg_dump")
    def test_locate_executable(self, mock_which):
        """Return the resolved executable path."""
        self.assertEqual(
            db_backup.locate_executable("pg_dump"),
            "/usr/bin/pg_dump",
        )
        mock_which.assert_called_once_with("pg_dump")

    @patch.object(db_backup.shutil, "which", return_value=None)
    def test_missing_executable_raises(self, mock_which):
        """Raise an informative error when a required executable is missing."""
        with self.assertRaisesRegex(FileNotFoundError, "pg_dump"):
            db_backup.locate_executable("pg_dump")

        mock_which.assert_called_once_with("pg_dump")


class DumpCommandTests(unittest.TestCase):
    """Verify PostgreSQL dump command execution."""

    @patch.object(db_backup.subprocess, "run")
    def test_run_dump_cmd_uses_safe_subprocess_options(self, mock_run):
        """Run commands without a shell and redirect output to files."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_file = Path(temporary_directory) / "dump.sql"
            error_file = Path(temporary_directory) / "stderr.txt"
            environment = {"PGPASSWORD": "test-password"}
            command = ["/usr/bin/pg_dump", "--dbname", "pe"]

            db_backup.run_dump_cmd(
                command,
                output_file,
                error_file,
                environment,
            )

        positional_args, keyword_args = mock_run.call_args

        self.assertEqual(positional_args[0], command)
        self.assertFalse(keyword_args["shell"])
        self.assertTrue(keyword_args["check"])
        self.assertEqual(keyword_args["env"], environment)
        self.assertEqual(keyword_args["stdout"].name, str(output_file))
        self.assertEqual(keyword_args["stderr"].name, str(error_file))

    @patch.object(db_backup, "run_dump_cmd")
    @patch.object(db_backup, "config")
    @patch.object(db_backup, "locate_executable")
    def test_create_backup_files_builds_expected_commands(
        self,
        mock_locate_executable,
        mock_config,
        mock_run_dump_cmd,
    ):
        """Create globals and database dumps using configured credentials."""
        mock_locate_executable.side_effect = [
            "/usr/bin/pg_dumpall",
            "/usr/bin/pg_dump",
        ]
        mock_config.return_value = {
            "host": "database.example",
            "database": "pe",
            "user": "pe-user",
            "password": "test-password",
            "port": 5432,
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.object(
                    db_backup,
                    "BACKUP_ROOT",
                    Path(temporary_directory),
                ),
                patch.object(db_backup, "DATE", "2026-11-19"),
            ):
                result = db_backup.create_backup_files()

        self.assertFalse(result)
        self.assertEqual(mock_run_dump_cmd.call_count, 2)

        globals_command = mock_run_dump_cmd.call_args_list[0].args[0]
        database_command = mock_run_dump_cmd.call_args_list[1].args[0]
        dump_environment = mock_run_dump_cmd.call_args_list[0].args[3]

        self.assertEqual(globals_command[0], "/usr/bin/pg_dumpall")
        self.assertIn("--globals-only", globals_command)
        self.assertIn("--no-role-passwords", globals_command)
        self.assertIn("database.example", globals_command)
        self.assertIn("pe-user", globals_command)

        self.assertEqual(database_command[0], "/usr/bin/pg_dump")
        self.assertIn("--format", database_command)
        self.assertIn("custom", database_command)
        self.assertIn("database.example", database_command)

        # The password should be passed through the subprocess environment,
        # not exposed in the command-line arguments.
        self.assertEqual(dump_environment["PGPASSWORD"], "test-password")
        self.assertNotIn("test-password", globals_command)
        self.assertNotIn("test-password", database_command)

    @patch.object(
        db_backup,
        "locate_executable",
        side_effect=FileNotFoundError("pg_dumpall missing"),
    )
    def test_create_backup_files_reports_failure(self, mock_locate_executable):
        """Return a failure result when required dump utilities are unavailable."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.object(
                    db_backup,
                    "BACKUP_ROOT",
                    Path(temporary_directory),
                ),
                patch.object(db_backup, "DATE", "2026-11-19"),
                self.assertLogs(db_backup.LOGGER, level="ERROR"),
            ):
                result = db_backup.create_backup_files()

        self.assertTrue(result)
        mock_locate_executable.assert_called_once_with("pg_dumpall")


class S3UploadTests(unittest.TestCase):
    """Verify S3 backup uploads."""

    @patch.object(db_backup.boto3, "client")
    def test_upload_backup_to_s3(self, mock_boto_client):
        """Upload a backup using the expected bucket and object key."""
        s3_client = mock_boto_client.return_value
        backup_file = Path("pedb_dump.sql")

        db_backup.upload_backup_to_s3(
            backup_file,
            "2026-11-19",
            "test-backup-bucket",
        )

        mock_boto_client.assert_called_once_with("s3")
        s3_client.upload_file.assert_called_once_with(
            str(backup_file),
            "test-backup-bucket",
            "2026-11-19/pedb_dump.sql",
        )

    @patch.object(db_backup.boto3, "client")
    def test_upload_failure_is_reraised(self, mock_boto_client):
        """Propagate an S3 failure so the worker reports an unsuccessful job."""
        s3_client = mock_boto_client.return_value
        error = ClientError(
            {
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "Access denied",
                }
            },
            "PutObject",
        )
        s3_client.upload_file.side_effect = error

        with (
            self.assertLogs(db_backup.LOGGER, level="ERROR"),
            self.assertRaises(ClientError),
        ):
            db_backup.upload_backup_to_s3(
                Path("pedb_dump.sql"),
                "2026-11-19",
                "test-backup-bucket",
            )


class RunDatabaseBackupTests(unittest.TestCase):
    """Verify the top-level database backup workflow."""

    @patch.object(db_backup, "upload_backup_to_s3")
    @patch.object(db_backup, "get_backup_bucket_name")
    @patch.object(db_backup, "create_backup_files")
    def test_run_db_backup_uploads_all_files(
        self,
        mock_create_backup_files,
        mock_get_bucket_name,
        mock_upload,
    ):
        """Upload the database, globals, and stderr files after a valid dump."""
        mock_create_backup_files.return_value = False
        mock_get_bucket_name.return_value = "test-backup-bucket"

        with tempfile.TemporaryDirectory() as temporary_directory:
            backup_root = Path(temporary_directory)

            with (
                patch.object(db_backup, "BACKUP_ROOT", backup_root),
                patch.object(db_backup, "DATE", "2026-11-19"),
            ):
                db_backup.run_db_backup()

            backup_folder = backup_root / "backups_2026-11-19"

        self.assertEqual(
            mock_upload.call_args_list,
            [
                call(
                    backup_folder / "pedb_dump.sql",
                    "2026-11-19",
                    "test-backup-bucket",
                ),
                call(
                    backup_folder / "pedb_globals.sql",
                    "2026-11-19",
                    "test-backup-bucket",
                ),
                call(
                    backup_folder / "stderr.txt",
                    "2026-11-19",
                    "test-backup-bucket",
                ),
            ],
        )

    @patch.object(db_backup, "upload_backup_to_s3")
    @patch.object(db_backup, "create_backup_files", return_value=True)
    def test_run_db_backup_raises_when_dump_fails(
        self,
        mock_create_backup_files,
        mock_upload,
    ):
        """Do not upload files or report success when dump creation fails."""
        with self.assertRaisesRegex(RuntimeError, "Database backup failed"):
            db_backup.run_db_backup()

        mock_create_backup_files.assert_called_once_with()
        mock_upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
