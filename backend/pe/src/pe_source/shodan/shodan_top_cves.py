"""Scripts to collect the top 10 CVEs for the report period, ranked by Shodan."""

# Standard Python Libraries
import datetime
import logging
import time

# Third-Party Libraries
import pandas as pd
import requests

# cisagov Libraries
from pe_source.data.db_query_source import (
    insert_shodan_top_cves,
    query_all_shodan_cves,
)

# Set up logging
LOGGER = logging.getLogger(__name__)

TODAY = datetime.date.today()


def get_shodan_cve_info(cve):
    """Retrieve info about the specified CVE from Shodan's API."""
    url = f"https://cvedb.shodan.io/cve/{cve}"
    resp = requests.get(url, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 10, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            f"\tRetrying Shodan CVE info API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
        )
        time.sleep(time_delay)
        resp = requests.get(url, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error(f"Error: Failed to retrieve Shodan CVE info for {cve}")
        return None
    else:
        return resp.json()


def get_cve_details(cve_list):
    """Retrieve details for the specified list of CVEs."""
    cve_detail_list = []
    for idx, cve in enumerate(cve_list):
        # Call shodan API to get CVE info
        LOGGER.info(f"Retrieving CVE details for {cve} ({idx+1} of {len(cve_list)})")
        cve_details = get_shodan_cve_info(cve)
        epss = round(cve_details.get("epss") * 100, 2)
        cvss_v2 = cve_details.get("cvss_v2")
        cvss_v3 = cve_details.get("cvss_v3")
        summary = cve_details.get("summary")
        # Parse relevant details
        cve_detail_dict = {
            "cve_id": cve,
            "epss": epss,
            "nvd_base_score": f"{{'v2': {cvss_v2}, 'v3': {cvss_v3}}}",
            "date": TODAY.strftime("%Y-%m-%d"),
            "summary": summary,
            "data_source_uid": "8cca4335-a64e-4c33-bd92-5ab9e74a6f99",
        }
        # Append CVE details
        cve_detail_list.append(cve_detail_dict)
    # Return as dataframe
    return pd.DataFrame(cve_detail_list)


def run_top_cves_shodan():
    """Get the top 10 CVEs by EPSS score amongst all distinct CVEs detected across all stakeholders for the report period."""
    # Retrieve list of all distinct CVEs detected in the past report period across all organizations
    end_date = TODAY.strftime("%Y-%m-%d")
    report_period_back = datetime.timedelta(days=16)
    start_date = (TODAY - report_period_back).strftime("%Y-%m-%d")
    all_cves = query_all_shodan_cves(start_date, end_date)
    LOGGER.info(
        "Retrieved list of all distinct CVEs detected by Shodan across all stakeholders for the past report period"
    )
    # Get further details for each CVE using shodan's API
    all_cve_details = get_cve_details(list(all_cves["cve"]))
    LOGGER.info("Retrieved details for all distinct CVEs")
    # Sort CVEs by EPSS score
    all_cve_details = all_cve_details.sort_values(
        by="epss", ascending=False
    ).reset_index(drop=True)
    # Grab the top 10 CVEs with the highest EPSS score
    top_epss_cves = all_cve_details[:10]
    # Insert top 10 CVEs into the P&E database
    insert_shodan_top_cves(top_epss_cves)
    LOGGER.info("Recorded top 10 CVEs with the highest EPSS score in the P&E database")