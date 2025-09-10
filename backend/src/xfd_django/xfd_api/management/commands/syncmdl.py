"""Populate command."""
# Standard Python Libraries
import os

# Third-Party Libraries
from django.core.management.base import BaseCommand
from django.db import connections
from xfd_api.tasks.helpers.syncdb_helpers.adjust_columns import adjust_column_types
from xfd_api.tasks.helpers.syncdb_helpers.create_sample_data import (
    populate_sample_data,
    populate_scan_results,
)
from xfd_api.tasks.helpers.syncdb_helpers.es_sync import (
    manage_elasticsearch_indices,
    sync_es_organizations,
)
from xfd_api.tasks.helpers.syncdb_helpers.fill_static_tables import (
    fill_nmi_service_group_table,
    fill_risky_service_lookup_table,
)
from xfd_api.tasks.searchSync import handler as sync_es_domains
from xfd_api.tasks.syncdb_task import drop_all_tables, synchronize


class Command(BaseCommand):
    """Syncmdl command."""

    help = "Synchronizes the MDL with optional sample data, and manages Elasticsearch indices."

    def add_arguments(self, parser):
        """Add arguments."""
        parser.add_argument(
            "-d",
            "--dangerouslyforce",
            action="store_true",
            help="Force drop and recreate the database.",
        )
        parser.add_argument(
            "-p",
            "--populate",
            action="store_true",
            help="Populate the database with sample data.",
        )
        parser.add_argument(
            "-m",
            "--metrics",
            action="store_true",
            help="Populate scan_results table with sample data using existing ids from scan and organization tables.",
        )

    def handle(self, *args, **options):  # pylint: disable=R0915
        """Handle method."""
        dangerouslyforce = options["dangerouslyforce"]
        populate = options["populate"]
        metrics = options["metrics"]

        mdl_username = os.getenv("MDL_USERNAME")
        mdl_password = os.getenv("MDL_PASSWORD")
        mdl_name = os.getenv("MDL_NAME")
        # TODO: Uncomment when IS_LOCAL is needed
        # is_local = os.getenv("IS_LOCAL")

        if not (mdl_username and mdl_password and mdl_name):
            self.stderr.write(
                "Error: MDL_USERNAME, MDL_PASSWORD, and MDL_NAME must be set in the environment."
            )
            return

        connection = connections["default"]

        # Step 1: Database User and Database Setup
        self.stdout.write("Setting up the MDL database and user...")

        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "CREATE USER {} WITH PASSWORD '{}';".format(
                        mdl_username, mdl_password
                    )
                )
            except Exception as e:
                self.stdout.write(
                    "User creation failed (likely already exists): {}".format(e)
                )

            try:
                cursor.execute(
                    "GRANT {} TO {};".format(mdl_username, os.getenv("DB_USERNAME"))
                )
            except Exception as e:
                self.stdout.write("Granting role failed: {}".format(e))

            try:
                cursor.execute(
                    "CREATE DATABASE {} OWNER {};".format(mdl_name, mdl_username)
                )
            except Exception as e:
                self.stdout.write(
                    "Database creation failed (likely already exists): {}".format(e)
                )

            try:
                cursor.execute(
                    "GRANT ALL PRIVILEGES ON DATABASE {} TO {};".format(
                        mdl_name, mdl_username
                    )
                )
            except Exception as e:
                self.stdout.write("Granting privileges failed: {}".format(e))

        # 👉 Step 1.5: Enable btree_gist extension
        self.stdout.write("Enabling btree_gist extension for GiST indexing...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")
                self.stdout.write("btree_gist extension enabled.")
        except Exception as e:
            self.stdout.write(f"Failed to enable btree_gist extension: {e}")

        # Step 2: Synchronize or Reset the Database
        self.stdout.write("Synchronizing the MDL database schema...")
        if dangerouslyforce:
            self.stdout.write("Dropping and recreating the database...")
            drop_all_tables(app_label="xfd_mini_dl")
        synchronize(target_app_label="xfd_mini_dl")
        fill_risky_service_lookup_table()
        fill_nmi_service_group_table()

        self.stdout.write("Running Phase 2 column type adjustments …")
        adjust_column_types(target_app_label="xfd_mini_dl")

        self.stdout.write("Database synchronization complete.")

        # Step 3: Elasticsearch Index Management
        manage_elasticsearch_indices(dangerouslyforce)

        # Step 4: Populate Sample Data
        if populate:
            self.stdout.write("Populating the database with sample data...")
            populate_sample_data()

            self.stdout.write("Sample data population complete.")

            # Step 4.1: Sync domains in ES
            sync_es_domains({})

        # Step 5: Sync organizations in ES
        sync_es_organizations()

        # Step 6: Populate Scan Results
        if metrics:
            self.stdout.write("Generating scan results...")
            populate_scan_results()
            self.stdout.write("Scan results population complete.")
