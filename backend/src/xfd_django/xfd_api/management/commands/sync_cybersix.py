from django.core.management.base import BaseCommand
from xfd_api.tasks.dmz_sync_cybersix import handler as run_cybersix_sync


class Command(BaseCommand):
    """Sync Cybersix data from the DMZ sync endpoint into the local DB."""

    help = "Fetch Cybersixgill data via DMZ and upsert into the mini datalake models"

    def handle(self, *args, **options):
        result = run_cybersix_sync()
        # If your handler() returns a dict like {"statusCode": ..., "body": ...}
        # you can pretty-print it here
        self.stdout.write(self.style.SUCCESS(f"{result}"))