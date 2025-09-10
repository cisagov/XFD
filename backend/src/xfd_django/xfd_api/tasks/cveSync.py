"""CVE sync scan."""
# Standard Python Libraries
from datetime import datetime
import logging
import os
import time

# Third-Party Libraries
import django
import requests
from xfd_mini_dl.models import Cpe, Cve

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

LOGGER = logging.getLogger(__name__)


def handler(event, context):
    """Lambda handler for syncing CVE data."""
    try:
        main()
        return {"status_code": 200, "body": "CVE sync completed successfully."}
    except Exception as e:
        return {"status_code": 500, "body": str(e)}


def main():
    """Sync CVE data."""
    done = False
    page = 1
    total_pages = 2

    while not done:
        task_request = fetch_cve_data(page)
        if not task_request or task_request.get("status") != "Processing":
            raise Exception(
                "Error: {} - Status: {}".format(
                    task_request.get("error"), task_request.get("status")
                )
            )

        while task_request.get("status") == "Processing":
            time.sleep(1)
            task_request = fetch_cve_data_task(task_request["task_id"])

        if task_request.get("status") == "Completed":
            cve_array = task_request.get("result", {}).get("data", [])
            total_pages = task_request.get("result", {}).get("total_pages", 1)
            current_page = task_request.get("result", {}).get("current_page", 1)

            save_to_db(cve_array)

            if current_page >= total_pages:
                done = True
            page += 1
        else:
            raise Exception(
                "Task error: {} - Status: {}".format(
                    task_request.get("error"), task_request.get("status")
                )
            )


def fetch_cve_data(page):
    """Fetch CVE data for a specific page."""
    LOGGER.info("Fetching CVE data for page %d", page)
    headers = {
        "X-API-KEY": os.getenv("CF_API_KEY"),
        "access_token": os.getenv("PE_API_KEY"),
        "Content-Type": "",
    }
    data = {"page": page, "per_page": 100}

    try:
        response = requests.post(
            "https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/cves_by_modified_date",
            headers=headers,
            json=data,
            timeout=20,  # Timeout in seconds
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Error fetching CVE data: %s", e)
        return None


def fetch_cve_data_task(task_id):
    """Fetch task result for CVE data."""
    url = "https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/cves_by_modified_date/task/{}".format(
        task_id
    )
    headers = {
        "X-API-KEY": os.getenv("CF_API_KEY"),
        "access_token": os.getenv("PE_API_KEY"),
        "Content-Type": "",
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Error fetching CVE task data: %s", e)
        return None


# TODO DRY the following three functions (save_to_db,
# save_cpes_to_db,
# save_cve_to_db), all save functions. Try to make a single function that can
# be used for all save functions.
def save_to_db(cve_array):
    """Save CVE and associated CPE data to the database using Django ORM."""
    for cve in cve_array:
        cpe_objects = []
        for vendor, products in cve.get("vender_product", {}).items():
            for product in products:
                cpe_objects.append(
                    Cpe(
                        name=product["cpe_product_name"],
                        version=product["version_number"],
                        vendor=vendor,
                        lastSeenAt=datetime.now(),
                    )
                )

        # Save CPEs and get their IDs
        cpe_ids = save_cpes_to_db(cpe_objects)

        # Save CVE and associate with CPEs
        save_cve_to_db(cve, cpe_ids)


def save_cpes_to_db(cpes):
    """Save CPE entries to the database using Django ORM."""
    cpe_ids = []
    for cpe in cpes:
        try:
            cpe_obj = Cpe.objects.update_or_create(
                name=cpe.name,
                version=cpe.version,
                vendor=cpe.vendor,
                defaults={"lastSeenAt": cpe.lastSeenAt},
            )
            cpe_ids.append(cpe_obj.id)
        except Exception as e:
            LOGGER.error("Error saving CPE: %s", e)
    return cpe_ids


def save_cve_to_db(cve, cpe_ids):
    """Save CVE entry to the database and associate with CPEs using Django ORM."""
    try:
        cve_obj = Cve.objects.update_or_create(
            name=cve["cve_name"],
            defaults={
                "publishedAt": cve.get("published_date"),
                "modifiedAt": cve.get("last_modified_date"),
                "status": cve.get("vuln_status"),
                "description": cve.get("description"),
                "cvssV2BaseScore": cve.get("cvss_v2_base_score"),
                "cvssV3BaseScore": cve.get("cvss_v3_base_score"),
                "cvssV4BaseScore": cve.get("cvss_v4_base_score"),
                "weaknesses": cve.get("weaknesses"),
                "references": cve.get("reference_urls"),
            },
        )
        # Add the CPEs to the CVE
        cve_obj.cpes.add(*cpe_ids)
        cve_obj.save()
    except Exception as e:
        LOGGER.error("Error saving CVE: %s", e)
