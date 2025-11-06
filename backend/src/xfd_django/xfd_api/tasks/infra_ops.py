"""Run infra ops."""
# Standard Python Libraries
import logging
import os

# Third-Party Libraries
import django

# Set the Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

# Initialize Django
django.setup()

# Third-Party Libraries
from xfd_api.helpers.infra_helpers import (
    create_matomo_scan_user,
    create_readonly_user,
    create_scan_user,
)

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Trigger infra ops."""
    try:
        # Create the XFD db scanning user if doesn't exist
        create_scan_user()

        # Create the Matomo db scanning user if doesn't exist
        create_matomo_scan_user()

        # Create a read-only user for both the default and mini_data_lake databases
        user = os.getenv("READ_ONLY_DB_USER")
        password = os.getenv("READ_ONLY_DB_PASSWORD")
        if not user or not password:
            LOGGER.warning("READ_ONLY_DB_USER or READ_ONLY_DB_PASSWORD is not set.")
        create_readonly_user(user, password)

        # Create a read-only user for Coginiti
        user = os.getenv("COGINITI_DB_USER")
        password = os.getenv("COGINITI_DB_PASSWORD")
        if not user or not password:
            LOGGER.warning("COGINITI_DB_USER or COGINITI_DB_PASSWORD is not set.")
        create_readonly_user(user, password)

        return {
            "status_code": 200,
            "body": "Database synchronization completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error during syncdb: %s", e)
        return {
            "status_code": 500,
            "body": "Database synchronization failed: {}".format(str(e)),
        }
