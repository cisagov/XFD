"""ASMsync scan."""
# Standard Python Libraries
import datetime
import json
import logging
import os
import time

# Third-Party Libraries
import django
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import requests
from xfd_api.helpers.link_ips_from_subs import connect_ips_from_subs
from xfd_api.helpers.link_subs_from_ips import connect_subs_from_ips
from xfd_api.helpers.shodan_dedupe import dedupe
from xfd_mini_dl.models import (
    Cidr,
    CidrOrgs,
    DataSource,
    IpsSubs,
    Organization,
    SubDomains,
)

LOGGER = logging.getLogger(__name__)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()
# Constants
MAX_RETRIES = 3  # Max retries for failed tasks
TIMEOUT = 60  # Timeout in seconds for waiting on task completion

headers = settings.DMZ_API_HEADER


def handler(event):
    """Enumerate and identify assets belonging to each stakeholder."""
    try:
        is_dmz = os.getenv("IS_DMZ")
        is_local = os.getenv("IS_LOCAL")
        if str(is_dmz).lower() not in {"true", "1"} and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exitting now.")
            return {
                "status_code": 200,
                "body": "DMZ Shodan Vulnerabilities and Asset cannot run outside the DMZ.",
            }
        main(event)
        return {
            "statusCode": 200,
            "body": "DMZ Shodan Vulnerabilities and Asset sync completed successfully.",
        }
    except Exception as e:
        return {"status_code": 500, "body": str(e)}


def main(event):
    """Identify assets owned by each stakeholder."""
    try:
        organization_id = event.get("organizationId")
        subdomain_found = False
        cidr_found = False
        orgs_to_sync = Organization.objects.filter(id__in=[organization_id])
        for org in orgs_to_sync:
            LOGGER.info(
                "Running ASM Sync on organization %s (%s)", org.name, org.acronym
            )

        # Process CIDRs
        try:
            flag_cidr_changes()
            cidr_found = Cidr.objects.filter(
                cidrorgs__organization__in=orgs_to_sync, cidrorgs__current=True
            ).exists()
        except Exception as e:
            message = "Error processing CIDRs: {}".format(e)
            LOGGER.warning(message)

        # Process subdomains
        try:
            enumerate_subs(orgs_to_sync)
            subdomain_found = SubDomains.objects.filter(
                organization__in=orgs_to_sync, current=True
            ).exists()
        except Exception as e:
            message = "Error processing subdomains: {}".format(e)
            LOGGER.warning(message)

        LOGGER.info("Identifying subdomains from ips...")
        connect_subs_from_ips(orgs_to_sync)
        LOGGER.info("Identifying ips from subdomains...")
        connect_ips_from_subs(orgs_to_sync)

        LOGGER.info("Identifying asset changes...")
        flag_asset_changes()
        LOGGER.info("Finished identifying asset changes")

        # Run shodan dedupe
        LOGGER.info("Running Shodan dedupe...")
        dedupe(orgs_to_sync)
        LOGGER.info("Finished running Shodan dedupe")
        if cidr_found or subdomain_found:
            LOGGER.info("ASM Sync completed successfully.")
            return {"status_code": 200, "body": "ASM Sync completed successfully."}
        else:
            return {
                "status_code": 204,
                "body": "ASM Sync finished without finding new CIDR blocks and subdomains.",
            }

    except Exception as e:
        LOGGER.warning("Error running ASM Sync %s", e)
        return {"status_code": 500, "body": "Error running ASM Sync: {}".format(e)}


def flag_asset_changes():
    """Mark Ips and Subdomains that are were not seen in the last scan as not current."""
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=90
    )

    SubDomains.objects.filter(Q(last_seen__lt=cutoff_date)).exclude(
        Q(is_root_domain=True) & (Q(identified=False) | Q(identified__isnull=True))
    ).update(current=False)

    IpsSubs.objects.filter(last_seen__lt=cutoff_date).update(current=False)

    # Ip.objects.filter(last_seen_timestamp__lt=cutoff_date).update(current=False)


def flag_cidr_changes():
    """Mark Cidrs that were not seen in the last scan as not current.

    return (organization_id, cidr_id) for cidrorgs that were closed.
    """
    cutoff_date = timezone.now().date() - datetime.timedelta(days=3)

    # Find CidrOrgs that will be closed
    cidrorgs_to_close = CidrOrgs.objects.filter(last_seen__lt=cutoff_date)

    # Capture their (org_id, cidr_id) before updating
    closed_pairs = cidrorgs_to_close.values_list(
        "organization_id", "cidr_id"
    ).distinct()

    # Mark them as not current
    cidrorgs_to_close.update(current=False)

    # Keep others marked current
    CidrOrgs.objects.filter(last_seen__gte=cutoff_date).update(current=True)

    # Retire cidrs that no longer have current orgs
    cidrs_to_retire = Cidr.objects.filter(
        Q(cidrorgs__isnull=True)
        | Q(cidrorgs__current=False)
        | Q(cidrorgs__current__isnull=True)
    ).distinct()
    cidrs_to_retire.update(retired=True)

    # Unretire cidrs that still have current orgs
    Cidr.objects.filter(cidrorgs__current=True).distinct().update(retired=False)

    return list(closed_pairs)


def enumerate_subs(org_list=None):
    """Query roots and identify related subdomains."""
    if not org_list:
        roots = SubDomains.objects.filter(is_root_domain=True).filter(
            Q(enumerate_subs=True) | Q(enumerate_subs=None)
        )
    else:
        org_ids = [org.id for org in org_list]
        roots = SubDomains.objects.filter(
            is_root_domain=True, organization__id__in=org_ids
        ).filter(Q(enumerate_subs=True) | Q(enumerate_subs=None))

    for root in roots:
        enumerate_roots(root)


def enumerate_roots(root_domain):
    """Identify subdomains for a given root via WHOis."""
    url = "https://domains-subdomains-discovery.whoisxmlapi.com/api/v1"
    API_WHOIS = os.getenv("WHOIS_XML_KEY")
    payload = json.dumps(
        {
            "apiKey": API_WHOIS,
            "domains": {"include": [root_domain.sub_domain]},
            "subdomains": {"include": ["*"], "exclude": []},
        }
    )
    headers = {"Content-Type": "application/json"}
    response = requests.request("POST", url, headers=headers, data=payload, timeout=20)

    retry_count, max_retries, time_delay = 1, 10, 5
    while response.status_code != 200 and retry_count <= max_retries:
        if response.status_code:
            LOGGER.info(
                "Retrying WhoisXML API endpoint (code %d), attempt %d of %d (url: %s)",
                response.status_code,
                retry_count,
                max_retries,
                url,
            )
        time.sleep(time_delay)
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=20
        )
        retry_count += 1

    data = response.json()
    sub_domains = data["domainsList"]

    whois_datasource, created = DataSource.objects.get_or_create(
        name="WhoisXML",
        defaults={
            "description": "Enterprise Grade solution to search for and monitor domain data.",
            "last_run": timezone.now().date(),  # Sets the current date and time
        },
    )
    for sub in sub_domains:
        if (
            sub != "www.{root}".format(root=root_domain.sub_domain)
            and sub != root_domain.sub_domain
        ):
            SubDomains.objects.get_or_create(
                organization=root_domain.organization,
                sub_domain=sub,
                defaults={
                    "root_domain": root_domain,
                    "last_seen": datetime.datetime.now(datetime.timezone.utc),
                    "current": True,
                    "from_root_domain": root_domain.sub_domain,
                    "enumerate_subs": False,
                    "subdomain_source": "WhoisXML",
                    "data_source": whois_datasource,
                    "identified": False,
                },
            )
