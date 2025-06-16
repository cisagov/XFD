"""Sync elasticsearch indexes."""
# Standard Python Libraries
from itertools import islice

# Third-Party Libraries
from xfd_api.tasks.es_client import ESClient
from xfd_mini_dl.models import Organization

# Elasticsearch client
es_client = ESClient()

# Constants
ORGANIZATION_CHUNK_SIZE = 50


def manage_elasticsearch_indices(dangerouslyforce):
    """Handle Elasticsearch index setup and teardown."""
    try:
        if dangerouslyforce:
            es_client.delete_all()
        es_client.sync_organizations_index()
        es_client.sync_domains_index()
        print("Elasticsearch indices synchronized.")
    except Exception as e:
        print("Error managing Elasticsearch indices: {}".format(e))


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
        print("Found {} organizations to sync.".format(len(organization_ids)))

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
                print("Syncing {} organizations...".format(len(organizations)))

                # Attempt to update Elasticsearch
                update_organization_chunk(es_client, organizations)

            print("Organization sync complete.")
        else:
            print("No organizations to sync.")

    except Exception as e:
        print("Error syncing organizations: {}".format(e))
        raise e
