"""Minimal PE database queries needed by the report-encryption helpers.

The original ``pe_reports.data.db_query`` module in atc-framework is a
~4000-line file covering scorecard/dashboard queries that belong to report
generation, which has not been migrated to XFD yet (see
pe_mailer/s3_reports.py). Only the two queries the encryption helpers
need are ported here.
"""

# Third-Party Libraries
from pe_reports.data.config import config
import psycopg2


def connect():
    """Connect directly to the PE PostgreSQL database.

    Lambda runs inside the same VPC as the database, so the SSH-tunneled
    ``connect_to_staging()`` path used by the original EC2 accessor script
    is not needed here.
    """
    return psycopg2.connect(**config())


def close(conn):
    """Close a database connection."""
    if conn is not None:
        conn.close()


def get_orgs(conn):
    """Return cyhy_db_name for every organization we report on."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cyhy_db_name FROM organizations "
                "WHERE report_on = true ORDER BY cyhy_db_name"
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        close(conn)


def get_orgs_pass(conn, password_key):
    """Return (cyhy_db_name, decrypted_password) for every report_on org."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT cyhy_db_name, PGP_SYM_DECRYPT(password::bytea, %s) "
                "FROM organizations WHERE report_on",
                (password_key,),
            )
            return cur.fetchall()
    finally:
        close(conn)
