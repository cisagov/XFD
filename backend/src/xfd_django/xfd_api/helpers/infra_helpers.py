"""Infra Ops helpers."""
# Standard Python Libraries
import logging
import os

# Third-Party Libraries
from django.conf import settings
from django.db import connections
import pymysql  # type: ignore

# Configure logging
LOGGER = logging.getLogger(__name__)


def create_readonly_user(user, password):
    """Create a read-only user for both the default and mini_data_lake databases."""
    # Skip user creation if running in the DMZ
    is_dmz = os.getenv("IS_DMZ", "0") == "1"
    if is_dmz:
        LOGGER.info("IS_DMZ is set to 1. Skipping creation of the scanning user.")
        return

    # Loop through both database aliases
    for alias in ["default", "mini_data_lake"]:
        db_name = settings.DATABASES[alias]["NAME"]
        with connections[alias].cursor() as cursor:
            try:
                # Check if the user already exists
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [user])
                user_exists = cursor.fetchone() is not None

                if not user_exists:
                    # Create the role if it doesn't exist
                    cursor.execute(
                        "CREATE ROLE {} LOGIN PASSWORD %s;".format(user), [password]
                    )
                    LOGGER.info(
                        "User %s created successfully in %s database.", user, alias
                    )
                else:
                    LOGGER.info(
                        "User %s already exists in %s database. Skipping creation.",
                        user,
                        alias,
                    )

                # Grant read-only privileges on the specific database
                cursor.execute(
                    "GRANT CONNECT ON DATABASE {} TO {};".format(db_name, user)
                )
                cursor.execute("GRANT USAGE ON SCHEMA public TO {};".format(user))
                cursor.execute(
                    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO {};".format(user)
                )
                cursor.execute(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {};".format(
                        user
                    )
                )
                LOGGER.info(
                    "User %s configured successfully for %s database.", user, alias
                )
            except Exception as e:
                LOGGER.error(
                    "Error creating or configuring scan user for %s database: %s",
                    alias,
                    e,
                )


def create_scan_user():
    """Create and configure the XFD scanning user if it does not already exist."""
    # Only create if not in the DMZ
    is_dmz = os.getenv("IS_DMZ", "0") == "1"

    if is_dmz:
        LOGGER.info("IS_DMZ is set to 1. Skipping creation of the scanning user.")
        return

    user = os.getenv("POSTGRES_SCAN_USER")
    password = os.getenv("POSTGRES_SCAN_PASSWORD")
    if not user or not password:
        LOGGER.warning("POSTGRES_SCAN_USER or POSTGRES_SCAN_PASSWORD is not set.")
        return

    db_name = settings.DATABASES["default"]["NAME"]

    with connections["default"].cursor() as cursor:
        try:
            # Check if the user already exists
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s;", [user])
            user_exists = cursor.fetchone() is not None

            if not user_exists:
                # Create the user
                cursor.execute(
                    "CREATE ROLE {} LOGIN PASSWORD %s;".format(user), [password]
                )
                LOGGER.info("User '%s' created successfully.", user)
            else:
                LOGGER.info("User '%s' already exists. Skipping creation.", user)

            # Grant privileges (idempotent as well)
            cursor.execute("GRANT CONNECT ON DATABASE {} TO {};".format(db_name, user))
            cursor.execute("GRANT USAGE ON SCHEMA public TO {};".format(user))
            cursor.execute(
                "GRANT SELECT ON ALL TABLES IN SCHEMA public TO {};".format(user)
            )
            cursor.execute(
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {};".format(
                    user
                )
            )

            LOGGER.info("User '%s' configured successfully.", user)
        except Exception as e:
            LOGGER.error("Error creating or configuring scan user: %s", e)


def create_matomo_scan_user():
    """Create and configure the Matomo scanning user if it does not already exist."""
    # Only create if not in the DMZ
    is_dmz = os.getenv("IS_DMZ", "0") == "1"
    if is_dmz:
        LOGGER.info("IS_DMZ is set to 1. Skipping creation of the scanning user.")
        return

    # Database connection settings
    db_host = os.getenv("MATOMO_DB_HOST")
    db_name = "matomo"
    db_user = "matomo"
    db_password = os.getenv("MATOMO_DB_PASSWORD")

    scan_user = os.getenv("POSTGRES_SCAN_USER")
    scan_password = os.getenv("POSTGRES_SCAN_PASSWORD")

    if not all([db_host, db_user, db_password, scan_user, scan_password]):
        LOGGER.warning(
            "Database connection credentials or scan user details are missing."
        )
        return

    try:
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor,
        )

        with conn.cursor() as cursor:
            # Check if any record exists for the given username (regardless of host)
            cursor.execute(
                "SELECT User, Host FROM mysql.user WHERE User = %s;", (scan_user,)
            )
            rows = cursor.fetchall()

            # Check if a record exists with host '%'
            user_exists = any(row["Host"] == "%" for row in rows)

            if not user_exists:
                # Create the scan user for host '%'
                # Use the connection's escape() to properly quote values.
                esc_user = conn.escape(scan_user)
                esc_password = conn.escape(scan_password)  # e.g. returns "'password'"
                # Build the SQL manually
                create_user_query = "CREATE USER {}@'%' IDENTIFIED BY {};".format(
                    esc_user, esc_password
                )
                cursor.execute(create_user_query)
                LOGGER.info(
                    "User '%s' created successfully in Matomo database.", scan_user
                )
            else:
                LOGGER.info(
                    "User '%s' already exists in Matomo database. Skipping creation.",
                    scan_user,
                )

            # Now grant permissions using the same escaped values.
            esc_user = conn.escape(scan_user)
            grant_queries = [
                "GRANT USAGE ON *.* TO {}@'%';".format(esc_user),
                "GRANT SELECT ON *.* TO {}@'%';".format(esc_user),
                "GRANT PROCESS, REPLICATION CLIENT ON *.* TO {}@'%';".format(esc_user),
                "GRANT SHOW DATABASES ON *.* TO {}@'%';".format(esc_user),
                "GRANT SHOW VIEW ON *.* TO {}@'%';".format(esc_user),
            ]
            for query in grant_queries:
                cursor.execute(query)
            cursor.execute("FLUSH PRIVILEGES;")

            # Query the grants for the user.
            # Construct the user identifier exactly as stored.
            show_grants_query = "SHOW GRANTS FOR {}@'%';".format(esc_user)
            cursor.execute(show_grants_query)
            grants = cursor.fetchall()

            # Print the grants to verify the user's permissions
            for grant in grants:
                LOGGER.info(grant)

            LOGGER.info(
                "User '%s' configured successfully in Matomo database.", esc_user
            )

        conn.commit()
        conn.close()

    except Exception as e:
        LOGGER.error(
            "Error creating or configuring scan user for Matomo database: %s", e
        )
