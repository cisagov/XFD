"""Update the blocklist with the latest data from blocklist.de."""
# Standard Python Libraries
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import logging

# Third-Party Libraries
from django.utils import timezone
import requests
from xfd_mini_dl.models import Blocklist

LOGGER = logging.getLogger(__name__)


def download_blocklist_as_dict(
    url: str = "https://lists.blocklist.de/lists/all.txt",
) -> dict:
    """Download a blocklist from the given URL and returns a dictionary."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()  # Raises an HTTPError if the response was unsuccessful
        lines = response.text.splitlines()
        blocklist_dict = {line.strip(): True for line in lines if line.strip()}
        return blocklist_dict
    except requests.RequestException as e:
        LOGGER.warning("Failed to download blocklist: %s", e)
        return {}


def query_blocklist_api(ip_str):
    """Query the blocklist API for the given IP address and returns."""
    response = requests.get(
        "http://api.blocklist.de/api.php?ip=" + ip_str,
        timeout=60,
    )
    response.raise_for_status()  # Raise exception for HTTP errors (including 429 rate limits)
    response_text = str(response.content)
    # LOGGER.info("Queried blocklist API for IP: %s", ip_str)
    # LOGGER.info("Blocklist API response: %s", response_text)
    malicious = False
    attacks = int(response_text.split("attacks: ")[1].split("<")[0])
    reports = int(response_text.split("reports: ")[1].split("<")[0])
    if attacks > 0 or reports > 0:
        malicious = True
    return malicious, attacks, reports


def create_new_blocklist_records(blocklist, created_count):
    """Create new blocklist records in the database for each IP address."""
    for ip_str in blocklist:
        try:
            malicious, attacks, reports = query_blocklist_api(ip_str)
            Blocklist.objects.create(
                ip=ip_str,
                created_at=timezone.now(),
                updated_at=timezone.now(),
                malicious=malicious,
                attacks=attacks,
                reports=reports,
            )
            created_count += 1
        except Exception as e:
            LOGGER.warning("Failed to create blocklist record for IP %s: %s", ip_str, e)
            continue


def main():
    """Handle the blocklist update process."""
    blocklist = download_blocklist_as_dict()
    if len(blocklist) == 0:
        LOGGER.warning("No blocklist data downloaded.")
        return
    blocklist_ips = list(blocklist.keys())
    blocklist_records = Blocklist.objects.all()
    blocklist_record_ips = [
        str(ipaddress.ip_interface(x.ip).ip) for x in blocklist_records
    ]
    ips_to_create = list(filter(lambda x: x not in blocklist_record_ips, blocklist_ips))
    ips_to_update = list(filter(lambda x: x in blocklist_ips, blocklist_record_ips))
    ips_to_delete = list(filter(lambda x: x not in blocklist_ips, blocklist_record_ips))

    # Create new blocklist records with API queries for accurate counts
    # First, collect all API data for the IPs using parallel requests
    def fetch_ip_data(ip_str):
        """Fetch blocklist data for a single IP."""
        try:
            malicious, attacks, reports = query_blocklist_api(ip_str)
            return ip_str, {
                "malicious": malicious,
                "attacks": attacks,
                "reports": reports,
            }
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                LOGGER.warning("Rate limit hit for IP %s: %s", ip_str, e)
            else:
                LOGGER.warning(
                    "HTTP error querying blocklist API for IP %s (status %d): %s",
                    ip_str,
                    e.response.status_code,
                    e,
                )
            return ip_str, None
        except Exception as e:
            LOGGER.warning("Failed to query blocklist API for IP %s: %s", ip_str, e)
            return ip_str, None

    ip_data = {}
    total_ips = len(ips_to_create)
    completed = 0

    # Use ThreadPoolExecutor for parallel API requests
    max_workers = 50
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ip = {
            executor.submit(fetch_ip_data, ip_str): ip_str for ip_str in ips_to_create
        }

        # Process results as they complete
        for future in as_completed(future_to_ip):
            completed += 1
            ip_str, data = future.result()
            if data is not None:
                ip_data[ip_str] = data
            if completed % max_workers == 0 or completed == total_ips:
                LOGGER.info("API query progress: %d/%d completed", completed, total_ips)

    # Batch create all records in a single database transaction
    now = timezone.now()
    records_to_create = [
        Blocklist(
            ip=ip_str,
            created_at=now,
            updated_at=now,
            malicious=data["malicious"],
            attacks=data["attacks"],
            reports=data["reports"],
        )
        for ip_str, data in ip_data.items()
    ]

    if records_to_create:
        try:
            Blocklist.objects.bulk_create(records_to_create)
        except Exception as e:
            LOGGER.warning("Failed to bulk create blocklist records: %s", e)

    # Update existing records - just update timestamp and malicious flag
    try:
        updated_count = Blocklist.objects.filter(ip__in=ips_to_update).update(
            updated_at=timezone.now(), malicious=True
        )
        LOGGER.info("Updated %d existing blocklist records.", updated_count)
    except Exception as e:
        LOGGER.warning("Failed to update blocklist records: %s", e)

    # Delete records no longer in the blocklist
    try:
        deleted_count, _ = Blocklist.objects.filter(ip__in=ips_to_delete).delete()
        LOGGER.info("Deleted %d blocklist records no longer in source.", deleted_count)
    except Exception as e:
        LOGGER.warning("Failed to delete old blocklist records: %s", e)


def handler(_):
    """Begin the blocklist update process."""
    try:
        main()
    except Exception as e:
        LOGGER.info("Error starting update blocklist task: %s", e)
