"""WasSync scan."""
# Standard Python Libraries
import datetime
import logging
import os
import time
from typing import Optional

# Third-Party Libraries
import django
from django.conf import settings
import requests
from xfd_api.helpers.date_time_helpers import calculate_days_back
from xfd_mini_dl.models import Organization, WasFindings

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

LOGGER = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3  # Max retries for failed tasks
TIMEOUT = 60  # Timeout in seconds for waiting on task completion

headers = settings.DMZ_API_HEADER


def handler(event):
    """Retrieve and save WAS Findings from the DMZ."""
    try:
        main()
        return {
            "status_code": 200,
            "body": "DMZ WAS Finding sync completed successfully.",
        }
    except Exception as e:
        return {"status_code": 500, "body": str(e)}


def main():
    """Fetch and save DMZ WAS Findings."""
    try:
        all_orgs = Organization.objects.all()
        # all_orgs = Organization.objects.filter(acronym__in=['USAGM', 'DHS'])

        since_timestamp_str = calculate_days_back(5)

        for org in all_orgs:
            LOGGER.info("Processing organization: %s, %s", org.acronym, org.name)
            done = False
            page = 1
            total_pages = 2
            per_page = 200
            retry_count = 0

            while not done:
                data = fetch_dmz_was_findings_task(
                    org.acronym, page, per_page, since_timestamp_str
                )
                if not data or data.get("status") != "Processing":
                    LOGGER.warning(
                        "Failed to start Was Finding sync task for org: %s, %s",
                        org.acronym,
                        org.name,
                    )

                    retry_count += 1

                    if retry_count >= MAX_RETRIES:
                        LOGGER.warning(
                            "Max retries reached for org: %s. Moving to next organization.",
                            org.acronym,
                        )
                        break  # Skip to next organization

                    time.sleep(5)
                    continue

                response = fetch_dmz_was_finding_data(data.get("task_id", None))
                while response and response.get("status") == "Pending":
                    time.sleep(1)
                    response = fetch_dmz_was_finding_data(data.get("task_id", None))

                if response and response.get("status") == "Completed":
                    was_finding_array = response.get("result", {}).get("data", [])
                    total_pages = response.get("result", {}).get("total_pages", 1)
                    current_page = response.get("result", {}).get("current_page", 1)
                    LOGGER.info("findings: %s", was_finding_array)
                    save_findings_to_db(was_finding_array, org)

                    if current_page >= total_pages:
                        done = True
                    page += 1
                else:
                    raise Exception(
                        "Task error: {error} - Status: {status}".format(
                            error=response.get("error"), status=response.get("status")
                        )
                    )
    except Exception as e:
        LOGGER.error("Failed to in main: %s", e)


def fetch_dmz_was_findings_task(org_acronym, page, per_page, since_timestamp):
    """Fetch Was Finding task id."""
    LOGGER.info("Fetching WAS finding task for organization: %s", org_acronym)

    data = {
        "org_acronym": org_acronym,
        "page": page,
        "per_page": per_page,
        "since_timestamp": since_timestamp,
    }

    try:
        response = requests.post(
            "https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/get_mdl_was_findings",
            headers=headers,
            json=data,
            timeout=20,  # Timeout in seconds
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Error fetching DMZ task: %s", e)
        return None


def fetch_dmz_was_finding_data(task_id):
    """Fetch DMZ WAS Finding data for a task."""
    url = "https://api.staging-cd.crossfeed.cyber.dhs.gov/pe/apiv1/get_mdl_was_findings/task/{t_id}".format(
        t_id=task_id
    )

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Error fetching DMZ Was Finding data: %s", e)
        return None


def convert_timestamp_to_date(timestamp: str) -> Optional[str]:
    """Convert an ISO 8601 timestamp to a date string in YYYY-MM-DD format."""
    try:
        date_object = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
        formatted_date = date_object.strftime("%Y-%m-%d")
    except Exception:
        formatted_date = None
    return formatted_date


def save_findings_to_db(was_finding_array, org):
    """Save WAS finding data to the mini datalake using Django ORM."""
    if was_finding_array:
        for asset in was_finding_array:
            try:
                (
                    was_finding_object,
                    created,
                ) = WasFindings.objects.update_or_create(
                    finding_uid=asset.get("finding_uid"),
                    defaults={
                        "finding_type": asset.get("finding_type"),
                        "webapp_id": asset.get("webapp_id"),
                        "webapp_url": asset.get("webapp_url"),
                        "webapp_name": asset.get("webapp_name"),
                        "was_org_id": asset.get("was_org_id"),
                        "name": asset.get("name"),
                        "owasp_category": asset.get("owasp_category"),
                        "severity": asset.get("severity"),
                        "times_detected": asset.get("times_detected"),
                        "cvss_v3_attack_vector": asset.get("cvss_v3_attack_vector"),
                        "base_score": asset.get("base_score"),
                        "temporal_score": asset.get("temporal_score"),
                        "fstatus": asset.get("fstatus"),
                        "last_detected": convert_timestamp_to_date(
                            asset.get("last_detected")
                        ),
                        "first_detected": convert_timestamp_to_date(
                            asset.get("first_detected")
                        ),
                        "potential": asset.get("potential"),
                        "cwe_list": asset.get("cwe_list"),
                        "wasc_list": asset.get("wasc_list"),
                        "last_tested": convert_timestamp_to_date(
                            asset.get("last_tested")
                        ),
                        "fixed_date": convert_timestamp_to_date(
                            asset.get("fixed_date")
                        ),
                        "is_ignored": asset.get("is_ignored"),
                        "is_remediated": asset.get("is_remediated"),
                        "url": asset.get("url"),
                        "qid": asset.get("qid"),
                        "response": asset.get("response"),
                    },
                )

            except Exception as e:
                LOGGER.error("Error saving Was Finding: %s", e)
