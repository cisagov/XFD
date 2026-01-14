"""Link sub-domains and IPs from IP lookups."""
# Standard Python Libraries
import datetime
import ipaddress
import logging
import os
import threading
import time

# Third-Party Libraries
from django.utils import timezone
import requests

LOGGER = logging.getLogger(__name__)
WHOIS_KEY = os.getenv("WHOIS_XML_KEY")
thread_count = os.getenv("WHOIS_XML_THREAD_COUNT")
if thread_count:
    THREAD_COUNT = int(thread_count)
else:
    THREAD_COUNT = 1
DATE = datetime.datetime.today().date()

# Third-Party Libraries
from xfd_api.helpers.asset_inserts import create_or_update_ip
from xfd_mini_dl.models import Cidr, DataSource, IpsSubs, Organization, SubDomains

whois_datasource, created = DataSource.objects.get_or_create(
    name="WhoisXML",
    defaults={
        "description": "Enterprise Grade solution to search for and monitor domain data.",
        "last_run": timezone.now().date(),  # Sets the current date and time
    },
)


def process_ips(thread_id, org, cidr, ip_list):
    """Process IPs through WhoisXML and save them to DB."""
    count = 0
    failed_ips = []
    chunk_start = time.time()
    for ip in ip_list:
        count += 1
        try:
            domain_list, failed_ips = search_whois_for_domains(ip, failed_ips)
        except Exception as e:
            LOGGER.error(
                "Thread %d: Error identifying domains for %s: %s", thread_id, ip, e
            )
            failed_ips.append(ip)
            continue

        if domain_list:
            LOGGER.info("Found %d domains associated with %s", len(domain_list), ip)
            save_and_link_ip_and_subdomain(ip, cidr, org, domain_list)

    LOGGER.info(
        "Thread %d completed. Processed %d IPs in %.2f seconds.",
        thread_id,
        count,
        time.time() - chunk_start,
    )

    if failed_ips:
        LOGGER.warning(
            "%d IPs failed to process in thread %d", len(failed_ips), thread_id
        )


def split_into_balanced_chunks(items, num_chunks):
    """Split `items` into `num_chunks` parts, distributing remainder fairly."""
    n = len(items)
    base_chunk_size = n // num_chunks
    remainder = n % num_chunks

    chunks = []
    start = 0
    for i in range(num_chunks):
        # Give one extra item to the first `remainder` chunks
        end = start + base_chunk_size + (1 if i < remainder else 0)
        chunks.append(items[start:end])
        start = end
    return chunks


def process_cidr(cidr, org):
    """Process a given CIDR using stored live IPs."""
    if not cidr.live_ips:
        LOGGER.warning("No live IPs for CIDR: %s", cidr.network)
        return

    ip_list = list(cidr.live_ips)
    if not ip_list:
        return

    chunks = split_into_balanced_chunks(ip_list, THREAD_COUNT)

    threads = []
    for i, chunk in enumerate(chunks):
        if chunk:  # Only create a thread if the chunk has work
            thread = threading.Thread(
                target=process_ips, args=(i + 1, org, cidr, chunk)
            )
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()


def search_whois_for_domains(ip, failed_ips):
    """Lookup domains associated with the ip."""
    url = "https://dns-history.whoisxmlapi.com/api/v1?apiKey={key}&ip={ip}".format(
        key=WHOIS_KEY, ip=ip
    )
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload, timeout=20)

    # Retry clause
    retry_count, max_retries, time_delay = 1, 3, 3
    while response.status_code != 200 and retry_count <= max_retries:
        if response.status_code:
            LOGGER.warning(
                "Retrying WhoisXML API endpoint (code %d), attempt %d of %s (url: %s)",
                response.status_code,
                retry_count,
                max_retries,
                url,
            )
        time.sleep(time_delay)
        response = requests.request(
            "GET", url, headers=headers, data=payload, timeout=20
        )
        retry_count += 1
    # If API call still unsuccessful
    if response.status_code != 200:
        LOGGER.error("Max retries reached for %s, labeling as failed", ip)
        failed_ips.append(ip)
    response = response.json()
    try:
        # If there is a response, save domain
        domains = []
        if response["size"] > 0:
            fifteen_days_back = time.time() - (15 * 24 * 60 * 60)
            for domain in response["result"]:
                if domain["last_visit"] >= fifteen_days_back:
                    domains.append(domain["name"])
            return domains, failed_ips
        else:
            return [], failed_ips
    except Exception as e:
        LOGGER.error("Failed to return WHOIsXML response")
        LOGGER.error(response)
        LOGGER.error(e)
        response = []
    return response, failed_ips


def generate_ips(cidr_network):
    """Create ip generator based on a cidr."""
    network = ipaddress.IPv4Network(cidr_network)
    yield from network.hosts()


def connect_subs_from_ips(orgs: list[Organization]):
    """For each org find all domains that are associated to an ip and create link in the ip_subs table."""
    for org in orgs:
        # Query IPs
        org_uid = org.id
        # ips_df = query_ips(org_uid, conn)
        cidrs = query_cidrs_by_org(org_uid)
        LOGGER.info("identified %d cidrs for %s", len(cidrs), org.acronym)

        for cidr_row in cidrs:
            LOGGER.info("Running %s", cidr_row.network)
            process_cidr(cidr_row, org)


def query_cidrs_by_org(org_id):
    """Get CIDRs by org."""
    cidrs = Cidr.objects.filter(
        cidrorgs__organization_id=org_id,  # Filter by the organization ID in the through table
        cidrorgs__current=True,  # Filter by the current status
    )
    return cidrs


def save_and_link_ip_and_subdomain(ip, cidr, org, domains):
    """Save an IP and associated Subdomains."""
    LOGGER.info("linking %s to %s", domains, ip)
    ip_object = create_or_update_ip(
        {
            "ip": ip,
            "organization": org,
            "origin_cidr": cidr,
            "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
            "last_reverse_lookup": datetime.datetime.now(datetime.timezone.utc),
            "current": True,
            "from_cidr": True,
        },
        {
            "origin_cidr": cidr,
            "last_seen_timestamp": datetime.datetime.now(datetime.timezone.utc),
            "last_reverse_lookup": datetime.datetime.now(datetime.timezone.utc),
            "current": True,
            "from_cidr": True,
        },
    )

    for domain in domains:
        try:
            root_domain, created = SubDomains.objects.get_or_create(
                sub_domain=".".join(domain.rsplit(".")[-2:]),
                organization=org,
                defaults={
                    "data_source": whois_datasource,
                    "enumerate_subs": False,
                    "is_root_domain": True,
                    "current": True,
                    "identified": True,
                    "subdomain_source": "WhoisXML",
                    "first_seen": datetime.datetime.now(datetime.timezone.utc),
                    "last_seen": datetime.datetime.now(datetime.timezone.utc),
                },
            )
            if not created:
                root_domain.last_seen = datetime.datetime.now(datetime.timezone.utc)
                root_domain.current = True
                root_domain.save()

            if domain != root_domain.sub_domain:
                sub_domain, created = SubDomains.objects.get_or_create(
                    sub_domain=domain,
                    organization=org,
                    defaults={
                        "data_source": whois_datasource,
                        "current": True,
                        "identified": True,
                        "subdomain_source": "WhoisXML",
                        "first_seen": datetime.datetime.now(datetime.timezone.utc),
                        "last_seen": datetime.datetime.now(datetime.timezone.utc),
                        "root_domain": root_domain,
                        "from_root_domain": root_domain.sub_domain,
                        "ip_address": ip,
                        "is_root_domain": False,
                    },
                )

            if not created:
                sub_domain.last_seen = datetime.datetime.now(datetime.timezone.utc)
                sub_domain.ip_address = ip
                sub_domain.current = True
                sub_domain.save()

            IpsSubs.objects.update_or_create(
                ip=ip_object,
                sub_domain=sub_domain,
                defaults={
                    "last_seen": datetime.datetime.now(datetime.timezone.utc),
                    "current": True,
                },
            )

        except KeyError as ke:
            LOGGER.error("Key error: %s", ke)
            continue
        except Exception as e:
            LOGGER.error("Unknown error: %s", error=e)
            continue
