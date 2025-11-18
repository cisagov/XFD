"""Import test users into the database from a JSON file."""
# Standard Python Libraries
import os

# Third-Party Libraries
from django.core.management.base import BaseCommand
from xfd_api.tasks.helpers.syncdb_helpers.add_test_users import (
    import_test_users_from_json,
)


class Command(BaseCommand):
    """Simple command to import test users into the User table."""

    help = "Imports test users from a JSON file into the User table."

    def add_arguments(self, parser):
        """Add arguments to command."""
        parser.add_argument(
            "json_path", type=str, help="Path to a JSON file containing user data."
        )

    def handle(self, *args, **options):
        """Handle command."""
        json_path = options["json_path"]

        if not os.path.exists(json_path):
            self.stderr.write(self.style.ERROR(f"File not found: {json_path}"))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"📥 Importing test users from {json_path}...")
        )
        import_test_users_from_json(json_path)
        self.stdout.write(self.style.SUCCESS("✅ Test users successfully imported."))
