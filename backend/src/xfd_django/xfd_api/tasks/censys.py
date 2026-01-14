"""Censys scan."""
# Standard Python Libraries
import datetime
import logging
import os
import re
import time

# Third-Party Libraries
from django.utils import timezone
import requests
from xfd_api.tasks.helpers.get_root_domains import get_root_domains
from xfd_mini_dl.models import DataSource, Organization, SubDomains

# Constants controlling pagination and rate limiting
RESULT_LIMIT = 1000
RESULTS_PER_PAGE = 100

# Configure logging
LOGGER = logging.getLogger(__name__)


def fetch_page(root_domain, next_token=None):
    """
    Fetch a single page of certificate search results from Censys.

    Uses basic auth from environment variables and POSTs JSON data.
    """
    url = "https://search.censys.io/api/v2/certificates/search"
    auth = (
        os.environ.get("CENSYS_API_ID"),
        os.environ.get("CENSYS_API_SECRET"),
    )
    headers = {"Content-Type": "application/json"}
    payload = {
        "q": root_domain,
        "per_page": RESULTS_PER_PAGE,
        "fields": ["names"],
    }
    if next_token:
        payload["cursor"] = next_token

    response = requests.post(url, json=payload, headers=headers, auth=auth, timeout=10)
    response.raise_for_status()  # raises an exception for HTTP errors
    return response.json()


def fetch_censys_data(root_domain):
    """
    Fetch certificate data for a given root domain, handling pagination.

    Logs the total number of certificates found and only retrieves up to RESULT_LIMIT.
    """
    LOGGER.info("Fetching certificates for %s", root_domain)
    data = fetch_page(root_domain)
    total = data.get("result", {}).get("total", 0)
    LOGGER.info(
        "Censys found %d certificates for %s. Fetching %d of them...",
        total,
        root_domain,
        min(total, RESULT_LIMIT),
    )
    result_count = 0
    next_token = data.get("result", {}).get("links", {}).get("next")
    while next_token and result_count < RESULT_LIMIT:
        next_page = fetch_page(root_domain, next_token)
        hits = next_page.get("result", {}).get("hits", [])
        data["result"]["hits"].extend(hits)
        next_token = next_page.get("result", {}).get("links", {}).get("next")
        result_count += RESULTS_PER_PAGE
    return data


def handler(command_options):
    """
    Run the Censys scan.

      - Retrieves root domains for the given organization (from SubDomains where is_root_domain is True).
      - For each root domain, fetches certificate data from Censys.
      - Normalizes found subdomain names (removing leading "*." and "www.").
      - Deduplicates subdomains.
      - Creates or updates SubDomains records.
    """
    organization_name = command_options.get("organizationName")
    organization_id = command_options.get("organizationId")
    if not organization_name:
        return {"status_code": 400, "body": "Organization name not provided."}

    orgs_to_sync = Organization.objects.filter(id=organization_id)
    if not orgs_to_sync.exists():
        return {"status_code": 500, "body": "Organization not found."}
    organization = orgs_to_sync.first()
    organization_id = organization.id

    LOGGER.info("Running Censys on organization: %s", organization_name)

    # Fetch or create the Censys data source record.
    censys_datasource, _ = DataSource.objects.get_or_create(
        name="Censys",
        defaults={
            "description": "The Leading Internet Intelligence Platform for Threat Hunting and Attack Surface Management.",
            "last_run": timezone.now().date(),
        },
    )

    # Retrieve root domains from SubDomains where is_root_domain is True.
    root_domains = get_root_domains(organization_id)

    unique_names = set()
    subdomains_created = 0

    for root_domain in root_domains:
        data = fetch_censys_data(root_domain)
        hits = data.get("result", {}).get("hits", [])
        for hit in hits:
            names = hit.get("names")
            if not names:
                continue
            for name in names:
                # Normalize: remove any leading "*." and "www."
                normalized_name = re.sub(r"\*\.", "", name)
                normalized_name = re.sub(r"^www\.", "", normalized_name)
                if (
                    normalized_name.endswith(root_domain)
                    and normalized_name not in unique_names
                ):
                    unique_names.add(normalized_name)
                    obj, created = SubDomains.objects.get_or_create(
                        organization=organization,
                        sub_domain=normalized_name.lower(),
                        defaults={
                            "last_seen": datetime.datetime.now(datetime.timezone.utc),
                            "current": True,
                            "from_root_domain": root_domain,
                            "enumerate_subs": False,
                            "subdomain_source": "censys",
                            "data_source": censys_datasource,
                            "identified": False,
                        },
                    )
                    if created:
                        subdomains_created += 1
        time.sleep(1)  # Respect rate limits

    LOGGER.info(
        "Censys saved or updated %d subdomains for organization %s",
        subdomains_created,
        organization_name,
    )

    return {"status_code": 200, "body": "Success running censys."}
