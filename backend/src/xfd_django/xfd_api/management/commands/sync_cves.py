"""Get CVEs from FastAPI endpoint and sync to local DB."""
# Third-Party Libraries
from django.core.management.base import BaseCommand
from xfd_api.tasks.nist_lz_sync import handler


class Command(BaseCommand):
    """Sync CVEs from FastAPI endpoint to local DB."""

    help = "Fetch CVEs from the FastAPI endpoint and sync to local DB"

    def handle(self, *args, **options):
        """Handle the command."""
        result = handler()
        self.stdout.write(str(result))
