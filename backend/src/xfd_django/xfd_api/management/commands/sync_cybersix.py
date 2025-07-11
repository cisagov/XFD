"""Cybersix Sync Command."""
# Third-Party Libraries
from django.core.management.base import BaseCommand
from xfd_api.tasks.cybersix_lz_sync import handler as run_cybersix_sync


class Command(BaseCommand):
    """Sync Cybersix data from the DMZ sync endpoint into the local DB."""

    help = "Fetch Cybersixgill data via DMZ and upsert into the mini datalake models"

    def handle(self, *args, **options):
        """Handle the command."""
        result = run_cybersix_sync(event={})
        # If your handler() returns a dict like {"statusCode": ..., "body": ...}
        # you can pretty-print it here
        self.stdout.write(self.style.SUCCESS(f"{result}"))
