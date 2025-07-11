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
    Ip,
    IpsSubs,
    Organization,
    SubDomains,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
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
        flag_cidr_changes()

        organization_id = event.get("organizationId")

        orgs_to_sync = Organization.objects.filter(id__in=[organization_id])
        for org in orgs_to_sync:
            LOGGER.info("Running ASM Sync on organization %s", org.name)
        # orgs_to_sync = Organization.objects.filter(acronym__in=event.organization.id)
        enumerate_subs(orgs_to_sync)

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
    except Exception as e:
        LOGGER.warning("Error running ASM %s", e)
    # quit()


def flag_asset_changes():
    """Mark Ips and Subdomains that are were not seen in the last scan as not current."""
    cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=15
    )

    SubDomains.objects.filter(Q(last_seen__lt=cutoff_date)).exclude(
        Q(is_root_domain=True) & (Q(identified=False) | Q(identified__isnull=True))
    ).update(current=False)

    IpsSubs.objects.filter(last_seen__lt=cutoff_date).update(current=False)

    Ip.objects.filter(last_seen_timestamp__lt=cutoff_date).update(current=False)

    # Ip.objects.filter(
    #     (Q(sub_domains__current=False) | Q(sub_domains__isnull=True)) &  # No current subdomains or no subdomains at all
    #     Q(origin_cidr__current=False)  # The associated origin_cidr is not current
    # ).update(current=False)


def flag_cidr_changes():
    """Mark Cidrs that are were not seen in the last scan as not current."""
    # Get all CidrOrgs where the last_seen date is older than 3 days
    cutoff_date = timezone.now().date() - datetime.timedelta(days=3)

    CidrOrgs.objects.filter(last_seen__lt=cutoff_date).update(current=False)
    CidrOrgs.objects.filter(last_seen__gte=cutoff_date).update(current=True)
    # Step 1: Get all Cidr objects that:
    # - Have no associated CidrOrgs at all, or
    # - Have associated CidrOrgs, but all of them have current=False or current is null
    cidrs_to_retire = Cidr.objects.filter(
        Q(cidrorgs__isnull=True)
        | Q(cidrorgs__current=False)  # No CidrOrgs associated
        | Q(cidrorgs__current__isnull=True)  # Associated CidrOrgs are not current
    ).distinct()

    # Step 2: Update the retired field to True for those Cidr objects
    cidrs_to_retire.update(retired=True)

    Cidr.objects.filter(Q(cidrorgs__current=True)).distinct().update(retired=False)


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
