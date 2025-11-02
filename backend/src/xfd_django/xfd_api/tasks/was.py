"""
Process WAS scans from Qualys API and insert findings.

Retrieve API credentials from configuration and encode them for authentication.
Query Qualys for recently completed scans, then iterate over each scan ID.
Fetch corresponding findings, convert timestamps to standardized date strings,
and insert each finding via the helper function.
Retry API calls upon failure and handle exceptions appropriately.
Expose a Lambda-compatible handler for event-driven execution.
"""

# Standard Python Libraries
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import logging
import os
import sys

from ..helpers.was_helpers import (
    check_qualys_alive,
    fetch_for,
    populate_was_scan_summaries,
    qualys_post_call,
)

# from dateutil.relativedelta import relativedelta
# import re
# from io import BytesIO
# import qualys_redact
# from pdfrw import PdfReader, PdfWriter, PageMerge
# import pe_reports


username = os.environ.get("QUALYS_USERNAME")
password = os.environ.get("QUALYS_PASSWORD")
credentials = f"{username}:{password}"
auth_string = "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

LOGGER = logging.getLogger(__name__)

logging.info("Here are your login creds %s", credentials)


def handler(event):
    """Identify credential breaches associated with stakeholder's root domains."""
    try:
        is_dmz = os.getenv("IS_DMZ", "0") == "1"
        is_local = os.getenv("IS_LOCAL", "1") == "1"
        if not is_dmz and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exiting now.")
            return {
                "statusCode": 200,
                "body": "WAS insert finding cannot run outside the DMZ.",
            }
        main()
        return {
            "statusCode": 200,
            "body": "WAS insert finding completed successfully.",
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}


class InvalidQualysCall(Exception):
    """Raise When qualys returns an error."""


class InvalidApiCall(Exception):
    """Raise when the API call is invalid or no data is returned."""


def get_recently_completed_scans(days_back=2):
    """
    Retrieve scans completed within the last `days_back` days from Qualys.

    Args:
        days_back (int): Number of days back to look for completed scans.

    Returns:
        dict: A dictionary mapping scan IDs to their last launch dates.
    """
    header = {
        "Content-Type": "application/json",
        "accept": "application/json",
        "Authorization": auth_string,
    }
    LOGGER.info(header)
    status_url = (
        "https://qualysapi.qg3.apps.qualys.com/qps/rest/3.0/search/was/wasscanschedule"
    )

    now = datetime.now(timezone.utc)

    # Calculate the date for two days ago
    two_days_ago = now - timedelta(days=days_back)

    # Set the time to the start of the day (00:00:00) and make sure it's in UTC
    start_of_day_two_days_ago = two_days_ago.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Format the date as a string in ISO 8601 format with Z for UTC
    date_string = start_of_day_two_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "ServiceRequest": {
            "preferences": {"limitResults": 1000},
            "filters": {
                "Criteria": [
                    {
                        "field": "lastScan.status",
                        "operator": "EQUALS",
                        "value": "FINISHED",
                    },
                    {
                        "field": "lastScan.launchedDate",
                        "operator": "GREATER",
                        "value": date_string,
                    },
                ]
            },
        }
    }
    id_scan_date_dict = {}
    LOGGER.info(payload)
    status_response = qualys_post_call(status_url, header, payload)
    has_more_records = True
    while has_more_records is True:
        for scan in status_response.get("ServiceResponse", {}).get("data", []):
            id_scan_date_dict[
                scan.get("WasScanSchedule", {})
                .get("target", {})
                .get("tags", {})
                .get("included", {})
                .get("tagList", {})
                .get("list", [{}])[0]
                .get("Tag", {})
                .get("name", None)
            ] = (
                scan.get("WasScanSchedule", {})
                .get("lastScan", {})
                .get("launchedDate", None)
            )

        has_more_records = (
            status_response.get("ServiceResponse", {}).get("hasMoreRecords", False)
            == "true"
        )

        if has_more_records:
            payload["ServiceRequest"]["filters"]["Criteria"].append(
                {
                    "field": "id",
                    "operator": "GREATER",
                    "value": status_response.get("ServiceResponse", {}).get("lastId"),
                }
            )

            status_response = qualys_post_call(status_url, header, payload)

    return id_scan_date_dict


def convert_timestamp_to_date(timestamp: str) -> str:
    """Convert an ISO 8601 timestamp to a date string in YYYY-MM-DD format."""
    date_object = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    formatted_date = date_object.strftime("%Y-%m-%d")
    return formatted_date


def main():
    """
    Process recent WAS scans and insert findings.

     Retrieve recent scans, fetch findings for each scan ID,
      and insert the results.
    """
    recently_scanned = get_recently_completed_scans(2)

    acronym_list = list(recently_scanned.keys())
    LOGGER.info(acronym_list)
    LOGGER.info(len(acronym_list))
    if check_qualys_alive(username, password):
        # spin up a small pool of workers
        with ThreadPoolExecutor(max_workers=5) as pool:
            # schedule all the fetches
            futures = {pool.submit(fetch_for, acr): acr for acr in acronym_list}
            LOGGER.info("Waiting for all futures to complete... \n")
            # as each one finishes, log the result
            for fut in as_completed(futures):
                acronym, count, elapsed, error = fut.result()
                if error:
                    LOGGER.error(
                        "Error ingesting findings for %s after %.2fs",
                        acronym,
                        elapsed,
                        exc_info=error,
                    )
                else:
                    LOGGER.info(
                        "Saved %d findings for %s in %.2fs", count, acronym, elapsed
                    )
    else:
        LOGGER.error("Qualys WAS API health‐check failed. Skipping ingestion.")

    LOGGER.info("All acronyms processed, starting WAS scan")
    # Populate WAS scan summaries, comment out if troubleshooting the qualys api call
    try:
        populate_was_scan_summaries(days_back=365)
    except Exception as exc:
        LOGGER.exception("Error populating WAS scan summaries: %s", exc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.info("\nUser has forced a close. Goodbye.")
        sys.exit()
