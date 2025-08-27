"""Search sync."""
# Standard Python Libraries
from itertools import islice
import logging
import os

# Third-Party Libraries
from django.db.models import F, Q
from django.utils.timezone import now
from xfd_mini_dl.models import Domain, Ip, SubDomains

from .es_client import ESClient
from .helpers.syncdb_helpers.es_sync import sync_es_organizations

# Set up logging
LOGGER = logging.getLogger(__name__)

# Constants
DOMAIN_CHUNK_SIZE = int(os.getenv("DOMAIN_CHUNK_SIZE", "50"))  # Adjust if needed


def chunked_queryset(queryset, chunk_size):
    """Chunk a queryset into smaller pieces."""
    it = iter(queryset.values_list("id", flat=True))  # Extract only IDs
    for first in it:
        yield [first] + list(islice(it, chunk_size - 1))


def handler(command_options):
    """Handle the synchronization of domains with Elasticsearch."""
    organization_id = command_options.get("organizationId")
    domain_id = command_options.get("domainId")

    LOGGER.info("Running searchSync...")
    client = ESClient()

    # Query to find domains that need to be synced
    domain_queryset = Domain.objects.annotate(
        should_sync=(
            Q(synced_at__isnull=True)
            | Q(updated_at__gt=F("synced_at"))
            | Q(organization__updated_at__gt=F("synced_at"))
            | Q(vulnerabilities__updated_at__gt=F("synced_at"))
            | Q(services__updated_at__gt=F("synced_at"))
        )
    ).filter(should_sync=True)

    # Additional filters for testing
    if organization_id:
        domain_queryset = domain_queryset.filter(organization_id=organization_id)
    if domain_id:
        domain_queryset = domain_queryset.filter(id=domain_id)

    LOGGER.info("Found %d domains to sync.", domain_queryset.count())

    # Chunk domains for processing
    for domain_chunk in chunked_queryset(domain_queryset, DOMAIN_CHUNK_SIZE):
        domains = list(
            Domain.objects.filter(id__in=domain_chunk)
            .select_related("organization")
            .prefetch_related("vulnerabilities", "services")
        )
        LOGGER.info("Syncing %d domains...", len(domains))

        # Update Elasticsearch
        try:
            client.update_domains(
                [
                    {
                        "id": str(domain.id),
                        "created_at": domain.created_at,
                        "updated_at": domain.updated_at,
                        "name": domain.name,
                        "reverse_name": domain.reverse_name,
                        "ip": domain.ip,
                        "from_root_domain": domain.from_root_domain,
                        "subdomain_source": domain.subdomain_source,
                        "ip_only": domain.ip_only,
                        "screenshot": domain.screenshot,
                        "country": domain.country,
                        "asn": domain.asn,
                        "cloud_hosted": domain.cloud_hosted,
                        "synced_at": domain.synced_at.isoformat()
                        if domain.synced_at
                        else None,
                        "ssl": domain.ssl,
                        "censys_certificates_results": domain.censys_certificates_results,
                        "trustymail_results": domain.trustymail_results,
                        "organization": {
                            "id": str(domain.organization.id),
                            "name": domain.organization.name,
                            "acronym": domain.organization.acronym,
                            "root_domains": domain.organization.root_domains,
                            "ip_blocks": domain.organization.ip_blocks,
                            "is_passive": domain.organization.is_passive,
                            "country": domain.organization.country,
                            "state": domain.organization.state,
                            "region_id": domain.organization.region_id,
                            "state_fips": domain.organization.state_fips,
                            "state_name": domain.organization.state_name,
                            "county": domain.organization.county,
                            "county_fips": domain.organization.county_fips,
                            "type": domain.organization.type,
                            "parent": {
                                "id": str(domain.organization.parent.id)
                                if domain.organization.parent
                                else None,
                                "name": domain.organization.parent.name
                                if domain.organization.parent
                                else None,
                            }
                            if domain.organization.parent
                            else None,
                        },
                        "discovered_by": {
                            "id": str(domain.discovered_by.id)
                            if domain.discovered_by
                            else None,
                            "name": domain.discovered_by.name
                            if domain.discovered_by
                            else None,
                            "arguments": domain.discovered_by.arguments
                            if domain.discovered_by
                            else None,
                        }
                        if domain.discovered_by
                        else None,
                        "services": [
                            {
                                "id": str(service.id),
                                "port": service.port,
                                "service": service.service,
                                "last_seen": service.last_seen.isoformat()
                                if service.last_seen
                                else None,
                                "products": service.products,
                                "censys_metadata": service.censys_metadata,
                            }
                            for service in domain.services.all()
                        ],
                        "vulnerabilities": [
                            {
                                "id": str(vulnerability.id),
                                "title": vulnerability.title,
                                "cvss": vulnerability.cvss,
                                "severity": vulnerability.severity,
                                "cve": vulnerability.cve,
                                "state": vulnerability.state,
                                "substate": vulnerability.substate,
                                "description": vulnerability.description,
                                "last_seen": vulnerability.last_seen.isoformat()
                                if vulnerability.last_seen
                                else None,
                                "references": vulnerability.references,
                            }
                            for vulnerability in domain.vulnerabilities.all()
                        ],
                    }
                    for domain in domains
                ]
            )
        except Exception as e:
            LOGGER.error("Error syncing domains to Elasticsearch: %s", e)
            continue

        # Mark domains as synced
        subdomain_ids = [d.id for d in domains if d.source == "subdomain"]
        ip_ids = [d.id for d in domains if d.source == "ip"]

        if subdomain_ids:
            SubDomains.objects.filter(sub_domain_uid__in=subdomain_ids).update(
                synced_at=now()
            )

        if ip_ids:
            Ip.objects.filter(id__in=ip_ids).update(synced_at=now())

    LOGGER.info("Domain sync complete.")

    LOGGER.info("Syncing organizations..")
    sync_es_organizations()
    LOGGER.info("Organization sync complete.")
