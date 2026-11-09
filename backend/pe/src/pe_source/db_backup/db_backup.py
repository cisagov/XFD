"""Backup the database and upload files to S3 bucket."""

# Standard Python Libraries
import datetime
import logging
import os
from pathlib import Path
import shutil

# Subprocess library is required to run psql backup tools
import subprocess  # nosec B404

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = ""
BACKUP_ROOT = Path("/var/www/db_backups")
DATE = datetime.datetime.now().strftime("%Y-%m-%d")
ZIP_DATE = datetime.datetime.now().strftime("%m-%d-%Y")
LOGGER = logging.getLogger(__name__)


def locate_executable(name):
    """Return the absolute path to the specified executable."""
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(f"Required executable was not found on PATH: {name}")
    return executable


def run_dump_cmd(command, output_file, error_file):
    """Run a PostgreSQL dump command without invoking a shell."""
    with (
        output_file.open("wb") as stdout_file,
        error_file.open("wb") as stderr_file,
    ):
        # Executable is trusted, arguments passed as list, and shell set to False
        subprocess.run(  # nosec B603
            command,
            check=True,
            stdout=stdout_file,
            stderr=stderr_file,
        )


def create_backup_files():
    """Create PostgreSQL globals, database, and ZIP backups."""
    # Determine file paths
    backup_folder = BACKUP_ROOT / f"backups_{DATE}"
    globals_file = backup_folder / "pedb_globals.sql"
    database_file = backup_folder / "pedb_dump.sql"
    error_file = backup_folder / "stderr.txt"
    # Attempt to create backup files
    try:
        # Create backup folder if it doesn't exist
        backup_folder.mkdir(parents=True, exist_ok=True)
        # Locate required executables for dump commands
        pg_dumpall = locate_executable("pg_dumpall")
        pg_dump = locate_executable("pg_dump")
        # Load env variables for DB
        database_name = os.environ["PE_DB_NAME"]
        database_port = os.environ["PE_DB_PORT"]
        database_user = os.environ["PE_DB_USER"]
        database_host = os.environ["DATABASE_HOST"]
        # Call pg_dumpall command (globals file)
        LOGGER.info("Creating PostgreSQL globals backup")
        run_dump_cmd(
            [
                pg_dumpall,
                "--globals-only",
                "--no-role-passwords",
                "--database",
                database_name,
                "--port",
                database_port,
                "--username",
                database_user,
                "--host",
                database_host,
                "--no-password",
            ],
            globals_file,
            error_file,
        )
        LOGGER.info("Globals dump created")
        # Call pg_dump command (database file)
        LOGGER.info("Creating PostgreSQL database backup")
        run_dump_cmd(
            [
                pg_dump,
                "--dbname",
                database_name,
                "--port",
                database_port,
                "--username",
                database_user,
                "--host",
                database_host,
                "--format",
                "custom",
                "--no-password",
            ],
            database_file,
            error_file,
        )
        LOGGER.info("Database dump created")
    except (
        KeyError,
        OSError,
        subprocess.CalledProcessError,
    ):
        # Catch any errors
        LOGGER.exception("Failed creating database backup")
        return True
    LOGGER.info("Database backup completed successfully")
    return False


def upload_backup_to_s3(file_name, datestring, bucket):
    """Upload a file to an S3 bucket."""
    LOGGER.info("Uploading %s to S3", file_name)
    # Locate the local file
    object_name = f"{datestring}/{file_name.name}"
    s3_client = boto3.client("s3")
    # Attempt to upload the file to S3
    try:
        s3_client.upload_file(
            str(file_name),
            bucket,
            object_name,
        )
        LOGGER.info(
            "Successfully uploaded %s to s3://%s/%s",
            file_name,
            bucket,
            object_name,
        )
    except ClientError:
        LOGGER.exception("Failed uploading %s to S3", file_name)


def run_db_backup():
    """Create database backup files and upload them to S3."""
    # Create backup files
    if create_backup_files():
        LOGGER.error("Database backup failed; files will not be uploaded")
        return
    backup_folder = BACKUP_ROOT / f"backups_{DATE}"
    backup_files = [
        backup_folder / "pedb_dump.sql",
        backup_folder / "pedb_globals.sql",
        backup_folder / "stderr.txt",
    ]
    # Upload each backup file to S3 bucket
    for backup_file in backup_files:
        upload_backup_to_s3(
            backup_file,
            DATE,
            BUCKET_NAME,
        )
