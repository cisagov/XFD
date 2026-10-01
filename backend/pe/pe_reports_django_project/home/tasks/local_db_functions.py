"""Install SQL functions required by the local PE database."""

# Standard Python Libraries
from pathlib import Path

# Third-Party Libraries
from django.db import connections, transaction

DATABASE = "default"
FUNCTIONS_SQL_PATH = Path(__file__).resolve().parent / "sql" / "local_db_functions.sql"


def ensure_local_db_functions(database=DATABASE, stdout=None):
    """Create or replace SQL functions required by the local PE database."""
    if not FUNCTIONS_SQL_PATH.exists():
        raise FileNotFoundError(
            "Missing local database functions file: {}".format(FUNCTIONS_SQL_PATH)
        )

    function_sql = FUNCTIONS_SQL_PATH.read_text(encoding="utf-8")

    if stdout is not None:
        stdout.write("Installing local database functions...")

    with transaction.atomic(using=database):
        with connections[database].cursor() as cursor:
            cursor.execute(function_sql)
