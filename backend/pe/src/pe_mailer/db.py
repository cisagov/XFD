"""PE database helpers used by pe_mailer.

Organization metadata (report_on/demo flags, cyhy_db_name, name) is
retrieved through ``pe_source.data.db_query_source.get_orgs()``, which
already goes through the PE API and is shared with the scan workers.

Contact email addresses have no API equivalent yet, so this module reads
them directly from the existing ``vw_orgs_contact_info`` database view
(see pe_reports_django_project/home/models.py:VwOrgsContactInfo) using the
same env-var-based connection parameters as the rest of the migrated
project (pe_reports.data.config.config()).
"""

# Standard Python Libraries
import logging
import sys

# Third-Party Libraries
from pe_reports.data.config import config
import psycopg2
from psycopg2 import OperationalError

LOGGER = logging.getLogger(__name__)

CONN_PARAMS_DIC = config()


def connect():
    """Connect to the PE PostgreSQL database."""
    try:
        return psycopg2.connect(**CONN_PARAMS_DIC)
    except OperationalError as err:
        err_type, err_obj, traceback = sys.exc_info()
        LOGGER.error(
            "Database connection error: %s on line number: %s",
            err,
            traceback.tb_lineno,
        )
        return None


def get_org_contacts(conn, cyhy_db_name):
    """Return the DISTRO/TECHNICAL contact emails for one organization.

    Parameters
    ----------
    conn : psycopg2 connection
        An open connection to the PE database.

    cyhy_db_name : str
        The organization's cyhy_db_name.

    Returns
    -------
    dict: {"DISTRO": [str, ...], "TECHNICAL": [str, ...]}

    """
    contact_dict = {"DISTRO": [], "TECHNICAL": []}
    query = """
        SELECT email, contact_type
        FROM vw_orgs_contact_info
        WHERE cyhy_db_name = %s AND email IS NOT NULL
    """
    with conn.cursor() as cursor:
        cursor.execute(query, (cyhy_db_name,))
        for email, contact_type in cursor.fetchall():
            if contact_type == "DISTRO":
                contact_dict["DISTRO"].append(email)
            elif contact_type == "TECHNICAL":
                contact_dict["TECHNICAL"].append(email)

    return contact_dict
