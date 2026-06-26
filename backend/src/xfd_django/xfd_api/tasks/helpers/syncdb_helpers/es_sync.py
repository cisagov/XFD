"""Sync elasticsearch indexes."""
# Standard Python Libraries
from itertools import islice
import logging

# Third-Party Libraries
from xfd_api.tasks.es_client import ESClient
from xfd_mini_dl.models import Cve as CveModel
from xfd_mini_dl.models import Organization, Vulnerability

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
        es_client.sync_cves_index()
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
                        "id", "name", "country", "state", "region_id", "tags", "acronym"
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


def sync_es_cves():
    """Sync elastic search CVEs."""
    try:
        # Fetch all CVEs with their affected organizations
        cves_with_orgs = {}

        # Get unique CVE-Organization pairs from vulnerabilities
        vulns = (
            Vulnerability.objects.filter(cve__isnull=False)
            .values("cve", "organization_id")
            .distinct()
        )

        for vuln in vulns:
            cve_name = vuln["cve"]
            org_id = vuln["organization_id"]
            if cve_name not in cves_with_orgs:
                cves_with_orgs[cve_name] = []
            if org_id:
                cves_with_orgs[cve_name].append(str(org_id))

        # Fetch all CVEs
        cves = list(
            CveModel.objects.all().values(
                "id",
                "name",
                "published_at",
                "modified_at",
                "status",
                "description",
            )
        )

        # Add organization IDs to each CVE
        for cve in cves:
            cve["organization_ids"] = cves_with_orgs.get(cve["name"], [])

        LOGGER.info("Found %d CVEs to sync.", len(cves))

        if cves:
            # Update Elasticsearch with CVEs
            es_client.update_cves(cves)
            LOGGER.info("CVE sync complete.")
        else:
            LOGGER.info("No CVEs to sync.")
    except Exception as e:
        LOGGER.exception("Error syncing CVEs: %s", e)
        raise e
