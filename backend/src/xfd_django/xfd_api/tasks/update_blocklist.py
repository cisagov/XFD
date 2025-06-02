"""Update the blocklist with the latest data from blocklist.de."""
# Standard Python Libraries
import ipaddress
import logging

# Third-Party Libraries
from django.utils import timezone
import requests
from xfd_mini_dl.models import Blocklist

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
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
    ).content
    response = str(response)
    # LOGGER.info("Queried blocklist API for IP: %s", ip_str)
    # LOGGER.info("Blocklist API response: %s", response)
    malicious = False
    attacks = int(str(response).split("attacks: ")[1].split("<")[0])
    reports = int(str(response).split("reports: ")[1].split("<")[0])
    if attacks > 0 or reports > 0:
        malicious = True
    return malicious, attacks, reports


def create_new_blocklist_records(blocklist):
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
        except Exception as e:
            LOGGER.warning("Failed to create blocklist record for IP %s: %s", ip_str, e)
            continue


def main():
    """Download blocklist data and query the blocklist API."""
    blocklist = download_blocklist_as_dict()
    if len(blocklist) == 0:
        LOGGER.warning("No blocklist data downloaded.")
        return
    LOGGER.info("Blocklist downloaded successfully with %d entries.", len(blocklist))
    blocklist_records = Blocklist.objects.all()
    # Prune blocklist records that are not in the downloaded blocklist data
    for ip_record in blocklist_records:
        ip_str = str(ipaddress.ip_interface(ip_record.ip).ip)
        if ip_str in blocklist:
            LOGGER.info("Updating blocklist record for IP: %s", ip_str)
            # If the IP is in the blocklist, update the record
            malicious, attacks, reports = query_blocklist_api(ip_str)
            if attacks > 0:
                ip_record.attacks = attacks
            if reports > 0:
                ip_record.reports = reports
            ip_record.malicious = malicious
            ip_record.updated_at = timezone.now()
            # Remove the IP from blocklist to improve performance
            del blocklist[ip_str]
        else:
            ip_record.delete()
            LOGGER.info("Blocklist record deleted for IP: %s", ip_str)
    # Add new blocklist records based on the downloaded data
    create_new_blocklist_records(blocklist)


def handler(_):
    """Begin the blocklist update process."""
    try:
        main()
    except Exception as e:
        LOGGER.info("Error starting update blocklist task: %s", e)
