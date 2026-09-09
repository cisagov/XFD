"""Sync elasticsearch indexes."""

# Standard Python Libraries
from itertools import islice
import logging
import time

# Third-Party Libraries
from xfd_api.tasks.es_client import ESClient
from xfd_mini_dl.models import Cve as CveModel
from xfd_mini_dl.models import Organization, Vulnerability

# Elasticsearch client
es_client = ESClient()

# Constants
ORGANIZATION_CHUNK_SIZE = 50

LOGGER = logging.getLogger(__name__)


def run_logged_step(step_name, func, *args, **kwargs):
    """
    Run a single sync step with isolated logging.

    Logs the start, success, duration, and full exception traceback for the
    specific step. Exceptions are re-raised so upstream callers see the real
    failure instead of a generalized or swallowed error.
    """
    LOGGER.info("START: %s", step_name)
    start_time = time.monotonic()

    try:
        result = func(*args, **kwargs)
    except Exception:
        elapsed = time.monotonic() - start_time
        LOGGER.exception("FAILED: %s after %.2f seconds", step_name, elapsed)
        raise

    elapsed = time.monotonic() - start_time
    LOGGER.info("SUCCESS: %s completed in %.2f seconds", step_name, elapsed)

    return result


def manage_elasticsearch_indices(dangerouslyforce):
    """
    Handle Elasticsearch index setup and teardown.

    Preserves the original behavior:
    - if dangerouslyforce is true, delete all indexes
    - sync organizations index
    - sync domains index
    - sync CVEs index

    This version only changes logging/error isolation. It does not add document
    sync operations here.
    """
    LOGGER.info(
        "Beginning Elasticsearch index management. dangerouslyforce=%s",
        dangerouslyforce,
    )

    if dangerouslyforce:
        run_logged_step(
            "manage_elasticsearch_indices.delete_all",
            es_client.delete_all,
        )

    run_logged_step(
        "manage_elasticsearch_indices.sync_organizations_index",
        es_client.sync_organizations_index,
    )

    run_logged_step(
        "manage_elasticsearch_indices.sync_domains_index",
        es_client.sync_domains_index,
    )

    run_logged_step(
        "manage_elasticsearch_indices.sync_cves_index",
        es_client.sync_cves_index,
    )

    LOGGER.info("Elasticsearch indices synchronized.")


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
    """
    Sync elastic search organizations.

    Preserves the original behavior:
    - fetch retired organizations
    - delete retired organizations from ES
    - fetch active organizations
    - sync active organizations in chunks

    This version isolates each major step and each chunk for clearer logs.
    """
    LOGGER.info("Beginning Elasticsearch organization sync.")

    retired_ids = run_logged_step(
        "sync_es_organizations.fetch_retired_organization_ids",
        fetch_retired_organization_ids,
    )

    if retired_ids:
        run_logged_step(
            "sync_es_organizations.delete_retired_organizations",
            delete_retired_organizations,
            retired_ids,
        )
    else:
        LOGGER.info("No retired organizations to remove from ES.")

    organization_ids = run_logged_step(
        "sync_es_organizations.fetch_active_organization_ids",
        fetch_active_organization_ids,
    )

    LOGGER.info("Found %d organizations to sync.", len(organization_ids))

    if organization_ids:
        total_chunks = (
            len(organization_ids) + ORGANIZATION_CHUNK_SIZE - 1
        ) // ORGANIZATION_CHUNK_SIZE

        for chunk_number, organization_chunk in enumerate(
            chunked_iterable(organization_ids, ORGANIZATION_CHUNK_SIZE),
            start=1,
        ):
            run_logged_step(
                f"sync_es_organizations.sync_chunk_{chunk_number}_of_{total_chunks}",
                sync_organization_chunk,
                organization_chunk,
                chunk_number,
                total_chunks,
            )

        LOGGER.info("Organization sync complete.")
    else:
        LOGGER.info("No organizations to sync.")


def fetch_retired_organization_ids():
    """Fetch retired organization IDs."""
    retired_ids = list(
        Organization.objects.filter(retired=True).values_list("id", flat=True)
    )

    LOGGER.info("Found %d retired organizations.", len(retired_ids))

    return retired_ids


def delete_retired_organizations(retired_ids):
    """Delete retired organizations from Elasticsearch."""
    LOGGER.info("Removing %d retired organizations from ES.", len(retired_ids))
    es_client.delete_organizations(retired_ids)
    LOGGER.info("Removed %d retired organizations from ES.", len(retired_ids))


def fetch_active_organization_ids():
    """Fetch active organization IDs."""
    organization_ids = list(
        Organization.objects.filter(retired=False).values_list("id", flat=True)
    )

    LOGGER.info("Found %d active organizations.", len(organization_ids))

    return organization_ids


def sync_organization_chunk(organization_chunk, chunk_number, total_chunks):
    """Fetch and update one chunk of organizations."""
    LOGGER.info(
        "Fetching organization chunk %d of %d. Requested ID count=%d.",
        chunk_number,
        total_chunks,
        len(organization_chunk),
    )

    organizations = list(
        Organization.objects.filter(id__in=organization_chunk).values(
            "id",
            "name",
            "country",
            "state",
            "region_id",
            "tags",
            "acronym",
            "retired",
        )
    )

    LOGGER.info(
        "Syncing %d organizations for chunk %d of %d.",
        len(organizations),
        chunk_number,
        total_chunks,
    )

    update_organization_chunk(es_client, organizations)

    LOGGER.info(
        "Synced %d organizations for chunk %d of %d.",
        len(organizations),
        chunk_number,
        total_chunks,
    )


def sync_es_cves():
    """
    Sync elastic search CVEs.

    Preserves the original behavior:
    - build CVE to organization map from vulnerabilities
    - fetch all CVEs
    - attach organization_ids to each CVE
    - update CVEs in ES

    This version isolates each major step for clearer logs.
    """
    LOGGER.info("Beginning Elasticsearch CVE sync.")

    cves_with_orgs = run_logged_step(
        "sync_es_cves.build_cve_organization_map",
        build_cve_organization_map,
    )

    cves = run_logged_step(
        "sync_es_cves.fetch_cves",
        fetch_cves,
    )

    run_logged_step(
        "sync_es_cves.attach_organization_ids",
        attach_organization_ids_to_cves,
        cves,
        cves_with_orgs,
    )

    LOGGER.info("Found %d CVEs to sync.", len(cves))

    if cves:
        run_logged_step(
            "sync_es_cves.update_cves",
            update_cves,
            cves,
        )
        LOGGER.info("CVE sync complete.")
    else:
        LOGGER.info("No CVEs to sync.")


def build_cve_organization_map():
    """Build a mapping of CVE names to affected organization IDs."""
    cves_with_orgs = {}

    vulns = (
        Vulnerability.objects.filter(cve__isnull=False)
        .values("cve", "organization_id")
        .distinct()
    )

    vuln_count = 0

    for vuln in vulns:
        vuln_count += 1

        cve_name = vuln["cve"]
        org_id = vuln["organization_id"]

        if cve_name not in cves_with_orgs:
            cves_with_orgs[cve_name] = []

        if org_id:
            cves_with_orgs[cve_name].append(str(org_id))

    LOGGER.info(
        "Built CVE organization map from %d vulnerability records. Unique CVEs=%d.",
        vuln_count,
        len(cves_with_orgs),
    )

    return cves_with_orgs


def fetch_cves():
    """Fetch all CVEs."""
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

    LOGGER.info("Fetched %d CVEs from database.", len(cves))

    return cves


def attach_organization_ids_to_cves(cves, cves_with_orgs):
    """Attach organization IDs to each CVE."""
    for cve in cves:
        cve["organization_ids"] = cves_with_orgs.get(cve["name"], [])

    LOGGER.info("Attached organization IDs to %d CVEs.", len(cves))


def update_cves(cves):
    """Update CVEs in Elasticsearch."""
    es_client.update_cves(cves)
