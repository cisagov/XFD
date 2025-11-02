"""Sync elasticsearch indexes."""
# Standard Python Libraries
from itertools import islice
import logging

# Third-Party Libraries
from xfd_api.tasks.es_client import ESClient
from xfd_mini_dl.models import Organization

# Elasticsearch client
es_client = ESClient()

# Constants
ORGANIZATION_CHUNK_SIZE = 50

LOGGER = logging.getLogger(__name__)


def manage_elasticsearch_indices(dangerouslyforce):
    """Handle Elasticsearch index setup and teardown."""
    try:
        if dangerouslyforce:
            es_client.delete_all()
        es_client.sync_organizations_index()
        es_client.sync_domains_index()
        LOGGER.info("Elasticsearch indices synchronized.")
    except Exception as e:
        LOGGER.error("Error managing Elasticsearch indices: %s", e)


def chunked_iterable(iterable, size):
    """Yield successive chunks of size `size` from `iterable`."""
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            break
        yield chunk


def update_organization_chunk(es_client, organizations):
    """Update a chunk of organizations."""
    es_client.update_organizations(organizations)


def sync_es_organizations():
    """Sync elastic search organizations."""
    try:
        # Fetch all organization IDs
        organization_ids = list(Organization.objects.values_list("id", flat=True))
        LOGGER.info("Found %d organizations to sync.", len(organization_ids))

        if organization_ids:
            # Split IDs into chunks
            for organization_chunk in chunked_iterable(
                organization_ids, ORGANIZATION_CHUNK_SIZE
            ):
                # Fetch full organization data for the current chunk
                organizations = list(
                    Organization.objects.filter(id__in=organization_chunk).values(
                        "id",
                        "name",
                        "country",
                        "state",
                        "region_id",
                        "tags",
                    )
                )
                LOGGER.info("Syncing %d organizations...", len(organizations))

                # Attempt to update Elasticsearch
                update_organization_chunk(es_client, organizations)

            LOGGER.info("Organization sync complete.")
        else:
            LOGGER.info("No organizations to sync.")

    except Exception as e:
        LOGGER.exception("Error syncing organizations: %s", e)
        raise e
