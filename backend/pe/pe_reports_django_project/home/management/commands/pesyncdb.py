"""Synchronize and populate the local PE database (mirrors Crossfeed syncdb)."""

# Standard Python Libraries
import os

# Third-Party Libraries
from django.core.management.base import BaseCommand
from django.db import connections
from home.tasks.helpers.create_sample_data import populate_sample_data
from home.tasks.syncdb_task import drop_all_tables, synchronize


def setup_pe_database(stdout):
    """Create the PE database role and database using the Crossfeed admin connection."""
    pe_username = os.getenv("PE_DB_USERNAME")
    pe_password = os.getenv("PE_DB_PASSWORD")
    pe_name = os.getenv("PE_DB_NAME")
    admin_username = os.getenv("DB_USERNAME")

    if not (pe_username and pe_password and pe_name and admin_username):
        raise ValueError(
            "PE_DB_USERNAME, PE_DB_PASSWORD, PE_DB_NAME, and DB_USERNAME must be set."
        )

    stdout.write("Setting up the PE database and user...")
    with connections["admin"].cursor() as cursor:
        try:
            cursor.execute(
                "CREATE USER {} WITH PASSWORD '{}';".format(pe_username, pe_password)
            )
        except Exception as exc:
            stdout.write(f"User creation failed (likely already exists): {exc}")

        try:
            cursor.execute("GRANT {} TO {};".format(pe_username, admin_username))
        except Exception as exc:
            stdout.write(f"Granting role failed: {exc}")

        try:
            cursor.execute("CREATE DATABASE {} OWNER {};".format(pe_name, pe_username))
        except Exception as exc:
            stdout.write(f"Database creation failed (likely already exists): {exc}")

        try:
            cursor.execute(
                "GRANT ALL PRIVILEGES ON DATABASE {} TO {};".format(
                    pe_name, pe_username
                )
            )
        except Exception as exc:
            stdout.write(f"Granting privileges failed: {exc}")


class Command(BaseCommand):
    """Sync PE schema from models and optionally load dnstwist sample data."""

    help = (
        "Synchronize the local PE database schema from all home table models "
        "(excluding SQL views) and optionally populate sample data."
    )

    def add_arguments(self, parser):
        """Register pesyncdb CLI flags."""
        parser.add_argument(
            "-d",
            "--dangerouslyforce",
            action="store_true",
            help="Drop and recreate all PE tables before syncing.",
        )
        parser.add_argument(
            "-p",
            "--populate",
            action="store_true",
            help="Populate sample organizations and root domains for dnstwist.",
        )

    def handle(self, *args, **options):
        """Create the PE database, sync schema, and optionally load sample data."""
        dangerouslyforce = options["dangerouslyforce"]
        populate = options["populate"]

        setup_pe_database(self.stdout)

        if dangerouslyforce:
            self.stdout.write("Dropping and recreating PE tables...")
            drop_all_tables()
        else:
            self.stdout.write("Applying PE schema from models...")

        synchronize()

        if populate:
            self.stdout.write("Populating PE sample data...")
            result = populate_sample_data()
            self.stdout.write(
                "Sample data loaded: orgs=%s, data_sources=%s, shodan_samples=%s"
                % (
                    result["organizations"],
                    result["data_sources"],
                    result.get("shodan_samples"),
                )
            )

        self.stdout.write("PE database sync complete.")
