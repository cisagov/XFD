"""Preview or explicitly replace the capacity database from an operational dump."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404
import sys
from uuid import uuid4

import psycopg2

from was_reports.utils.env import load_env_file


GUARD_SQL = """
DO $$
BEGIN
    IF current_database() <> 'was_capacity_test' THEN
        RAISE EXCEPTION 'Unexpected reset target';
    END IF;
    IF NOT pg_try_advisory_xact_lock(hashtext(current_database()),
                                   hashtext('was_capacity_trial')) THEN
        RAISE EXCEPTION 'Capacity trial or reset is running';
    END IF;
END;
$$;
"""

CLEANUP_SQL = """
DELETE FROM public.was_test_replay_items;
DELETE FROM public.was_test_replay_batches;
DELETE FROM public.was_batch_report_attempts;
DELETE FROM public.was_report_runs;
DELETE FROM public.was_batch_runs;
"""


def load_settings(prefix, expected_database):
    """Require every connection setting without operational fallback."""
    suffixes = {
        "HOST": "host", "NAME": "dbname", "USERNAME": "user",
        "PASSWORD": "password", "PORT": "port", "SSLMODE": "sslmode",
        "CONNECT_TIMEOUT_SECONDS": "connect_timeout",
    }
    settings = {}
    for suffix, keyword in suffixes.items():
        name = prefix + suffix
        value = os.environ.get(name)
        if not value or not value.strip():
            raise ValueError("Missing setting: {}".format(name))
        settings[keyword] = value
    if settings["dbname"] != expected_database:
        raise ValueError("Database must be {}".format(expected_database))
    if expected_database == "was_capacity_test" and not settings["user"].startswith(
        "was_capacity_"
    ):
        raise ValueError("Test username must start with was_capacity_.")
    if settings["sslmode"] not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("Encrypted PostgreSQL connections are required.")
    if not 1 <= int(settings["port"]) <= 65535 or int(settings["connect_timeout"]) <= 0:
        raise ValueError("Port or connection timeout is invalid.")
    return settings


def verify_database(settings, target=False):
    """Inspect identity and restore ownership without writing either database."""
    connection = psycopg2.connect(**settings, options="-c default_transaction_read_only=on")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user, rolsuper, rolcreatedb, "
                "rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
            database, username, superuser, createdb, createrole = cursor.fetchone()
            if (database, username) != (settings["dbname"], settings["user"]):
                raise ValueError("Connected database identity does not match configuration.")
            if not target:
                return
            if any((superuser, createdb, createrole)):
                raise ValueError("Test login must not have administrative role attributes.")
            cursor.execute(
                "SELECT has_database_privilege(current_user, current_database(), 'CREATE'), "
                "has_schema_privilege(current_user, 'public', 'CREATE'), "
                "pg_has_role(current_user, nspowner, 'USAGE') "
                "FROM pg_namespace WHERE nspname='public'"
            )
            privileges = cursor.fetchone()
            if not privileges or not all(privileges):
                raise ValueError(
                    "Test login needs CREATE on the test database and ownership of public "
                    "schema. Ask an administrator to provision test-only ownership."
                )
            cursor.execute(
                "SELECT COUNT(*) FROM pg_class relations "
                "JOIN pg_namespace namespaces ON namespaces.oid=relations.relnamespace "
                "WHERE namespaces.nspname='public' "
                "AND relations.relkind IN ('r','p','S','v','m','f') "
                "AND NOT pg_has_role(current_user, relations.relowner, 'USAGE')"
            )
            if cursor.fetchone()[0]:
                raise ValueError("Test login must own existing public tables, sequences and views.")
    finally:
        connection.close()


def postgres_environment(settings, readonly=False):
    """Build explicit subprocess connections with passwords absent from arguments."""
    environment = {name: value for name, value in os.environ.items()
                   if not name.startswith("PG")}
    mapping = {
        "host": "PGHOST", "dbname": "PGDATABASE", "user": "PGUSER",
        "password": "PGPASSWORD", "port": "PGPORT", "sslmode": "PGSSLMODE",
        "connect_timeout": "PGCONNECT_TIMEOUT",
    }
    environment.update({mapping[name]: value for name, value in settings.items()})
    if readonly:
        environment["PGOPTIONS"] = "-c default_transaction_read_only=on"
    return environment


def private_file(path, contents=None):
    """Create an exclusive owner-only file before a tool writes sensitive data."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        if contents is not None:
            stream.write(contents)


def run_tool(arguments, environment, log_path):
    """Run a PostgreSQL executable without exposing output or credentials."""
    private_file(log_path)
    with log_path.open("ab") as log_stream:
        result = subprocess.run(  # nosec B603
            arguments, env=environment, stdin=subprocess.DEVNULL,
            stdout=log_stream, stderr=log_stream, check=False,
        )
    if result.returncode:
        raise RuntimeError(
            "{} failed; inspect the private operation log locally. "
            "Do not share it without redaction.".format(Path(arguments[0]).name)
        )


def execute_reset(source, target, output_directory):
    """Back up both public schemas, then atomically restore and clear test history."""
    executables = {name: shutil.which(name) for name in ("pg_dump", "pg_restore", "psql")}
    if not all(executables.values()):
        raise RuntimeError("Install PostgreSQL client tools: pg_dump, pg_restore and psql.")
    verify_database(source)
    verify_database(target, target=True)
    output_directory = Path(output_directory).expanduser().resolve()
    output_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    operation_directory = output_directory / str(uuid4())
    operation_directory.mkdir(mode=0o700)
    source_environment = postgres_environment(source, readonly=True)
    target_environment = postgres_environment(target)
    print("Private backup directory: {}".format(operation_directory), flush=True)
    for name, environment in (("source", source_environment),
                              ("target-before-reset", postgres_environment(target, readonly=True))):
        archive = operation_directory / (name + ".dump")
        private_file(archive)
        run_tool(
            [executables["pg_dump"], "--no-password", "--lock-wait-timeout=30s",
             "--format=custom", "--schema=public",
             "--file", str(archive)], environment, operation_directory / (name + ".log"),
        )
    restore_file = operation_directory / "restore.sql"
    private_file(restore_file)
    run_tool(
        [executables["pg_restore"], "--clean", "--if-exists", "--no-owner", "--no-privileges",
         "--file", str(restore_file), str(operation_directory / "source.dump")],
        target_environment, operation_directory / "render.log",
    )
    guard_file = operation_directory / "guard.sql"
    cleanup_file = operation_directory / "cleanup.sql"
    private_file(guard_file, GUARD_SQL)
    private_file(cleanup_file, CLEANUP_SQL)
    run_tool(
        [executables["psql"], "-X", "--no-password", "--single-transaction",
         "--set=ON_ERROR_STOP=1", "--file", str(guard_file),
         "--file", str(restore_file), "--file", str(cleanup_file)],
        target_environment, operation_directory / "restore.log",
    )
    return operation_directory


def parse_args(argv=None):
    """Default to inspection and require a backup location for destructive apply."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output-directory")
    arguments = parser.parse_args(argv)
    if arguments.apply and not arguments.output_directory:
        parser.error("--apply requires --output-directory for retained private backups.")
    return arguments


def main(argv=None):
    """Load explicit settings and never print raw database or subprocess exceptions."""
    arguments = parse_args(argv)
    load_env_file()
    try:
        source = load_settings("WAS_DB_", "was")
        target = load_settings("TEST_WAS_DB_", "was_capacity_test")
        if arguments.apply:
            execute_reset(source, target, arguments.output_directory)
            print("Test public schema restored; five history tables cleared. "
                  "Tracker dates and assignee records are unchanged from the source copy.")
        else:
            verify_database(source)
            verify_database(target, target=True)
            print("Preview passed. Apply replaces the test public schema from was and clears "
                  "five history tables. No database data changed; no external services called.")
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        print("Database reset failed ({}); check connectivity, permissions and private logs. "
              "Raw database errors are suppressed.".format(type(error).__name__), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
