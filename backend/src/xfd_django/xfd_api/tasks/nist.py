"""Update CVE data using the NIST API."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import logging
import os
import sys
import time

# Third-Party Libraries
import django
from nested_lookup import nested_lookup
import requests

from ..helpers.nist_helpers import api_cve_insert, get_cve_and_products

api_key = os.getenv("NIST_API_KEY")
# Global variables
nist_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# Setup logging
LOGGER = logging.getLogger(__name__)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()


def handler(event):
    """Retrieve and save NIST update alerts from the DMZ."""
    try:
        main()
        return {
            "statusCode": 200,
            "body": "DMZ NIST update completed successfully.",
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}


def initial_fill(start_index=0):
    """Fill the database with CVE data for the first time."""
    payload = {}
    headers = {"apiKey": api_key}
    response = requests.request(
        "GET", nist_url, timeout=10, headers=headers, data=payload
    )

    result = response.json()
    start_index += result["resultsPerPage"]
    for vuln in result["vulnerabilities"]:
        cve_dict = format_vulnerability(vuln)
        api_cve_insert(cve_dict)
    error_count = 0
    while start_index < result["totalResults"]:
        try:
            params = "?startIndex=" + str(start_index)
            response = requests.request(
                "GET", nist_url + params, timeout=10, headers=headers, data=payload
            )
            result = response.json()

        except Exception:
            LOGGER.error("Issue while querying. Trying again in 5 seconds")
            time.sleep(5)
            error_count += 1
            if error_count < 5:
                continue

        start_index += result["resultsPerPage"]
        for vuln in result["vulnerabilities"]:
            cve_dict = format_vulnerability(vuln)
            api_cve_insert(cve_dict)
    LOGGER.info("CVEs have been filled.")


def update_cves(hours_back=12):
    """Update the database."""
    start_index = 0
    now = datetime.now()
    last_mod_start_date = (now - timedelta(hours=hours_back)).isoformat()
    last_mod_end_date = now.isoformat()

    params = (
        "?startIndex="
        + str(start_index)
        + "&lastModStartDate="
        + last_mod_start_date
        + "&lastModEndDate="
        + last_mod_end_date
    )

    payload = {}
    headers = {"apiKey": api_key}
    response = requests.request(
        "GET", nist_url + params, timeout=10, headers=headers, data=payload
    )

    result = response.json()
    logging.info(result)
    start_index += result["resultsPerPage"]
    for vuln in result["vulnerabilities"]:
        cve_dict = format_vulnerability(vuln)
        api_cve_insert(cve_dict)
    while start_index < result["totalResults"]:
        params = (
            "?startIndex="
            + str(start_index)
            + "&lastModStartDate="
            + last_mod_start_date
            + "&lastModEndDate="
            + last_mod_end_date
        )
        response = requests.request(
            "GET", nist_url + params, timeout=10, headers=headers, data=payload
        )

        result = response.json()
        start_index += result["resultsPerPage"]
        for vuln in result["vulnerabilities"]:
            cve_dict = format_vulnerability(vuln)
            api_cve_insert(cve_dict)

    LOGGER.info("CVEs have been filled.")


def format_vulnerability(vuln):
    """Format the returned vuln into database readable format."""
    cve = {
        "cve_name": vuln["cve"]["id"],
        "published_date": vuln["cve"]["published"],
        "last_modified_date": datetime.fromisoformat(
            vuln["cve"]["lastModified"]
        ).replace(tzinfo=timezone.utc),
        "vuln_status": vuln["cve"]["vulnStatus"],
        "description": None,
        "cvss_v2_source": None,
        "cvss_v2_type": None,
        "cvss_v2_version": None,
        "cvss_v2_vector_string": None,
        "cvss_v2_base_score": None,
        "cvss_v2_base_severity": None,
        "cvss_v2_exploitability_score": None,
        "cvss_v2_impact_score": None,
        "cvss_v3_source": None,
        "cvss_v3_type": None,
        "cvss_v3_version": None,
        "cvss_v3_vector_string": None,
        "cvss_v3_base_score": None,
        "cvss_v3_base_severity": None,
        "cvss_v3_exploitability_score": None,
        "cvss_v3_impact_score": None,
        "cvss_v4_source": None,
        "cvss_v4_type": None,
        "cvss_v4_version": None,
        "cvss_v4_vector_string": None,
        "cvss_v4_base_score": None,
        "cvss_v4_base_severity": None,
        "cvss_v4_exploitability_score": None,
        "cvss_v4_impact_score": None,
        "weaknesses": [],
        "reference_urls": [],
        "cpe_list": [],
    }
    for weakness in vuln["cve"].get("weaknesses", []):
        cve["weaknesses"] += nested_lookup("value", weakness)

    for reference in vuln["cve"].get("references", []):
        cve["reference_urls"] += nested_lookup("url", reference)

    for cpe in vuln["cve"].get("configurations", []):
        cve["cpe_list"] += nested_lookup("criteria", cpe)

    for description in vuln["cve"]["descriptions"]:
        if description["lang"] == "en":
            cve["description"] = description["value"]

    cvss_v2 = nested_lookup(
        key="cvssMetricV2", document=vuln["cve"].get("metrics", {}), wild=True
    )
    if len(cvss_v2) > 0:
        cve["cvss_v2_source"] = cvss_v2[0][0]["source"]
        cve["cvss_v2_type"] = cvss_v2[0][0]["type"]
        cve["cvss_v2_version"] = cvss_v2[0][0]["cvssData"]["version"]
        cve["cvss_v2_vector_string"] = cvss_v2[0][0]["cvssData"]["vectorString"]
        cve["cvss_v2_base_score"] = cvss_v2[0][0]["cvssData"]["baseScore"]
        cve["cvss_v2_base_severity"] = cvss_v2[0][0]["baseSeverity"]
        cve["cvss_v2_exploitability_score"] = cvss_v2[0][0]["exploitabilityScore"]
        cve["cvss_v2_impact_score"] = cvss_v2[0][0]["impactScore"]

    cvss_v3 = nested_lookup(
        key="cvssMetricV3", document=vuln["cve"].get("metrics", {}), wild=True
    )
    if len(cvss_v3) > 0:
        cve["cvss_v3_source"] = cvss_v3[0][0]["source"]
        cve["cvss_v3_type"] = cvss_v3[0][0]["type"]
        cve["cvss_v3_version"] = cvss_v3[0][0]["cvssData"]["version"]
        cve["cvss_v3_vector_string"] = cvss_v3[0][0]["cvssData"]["vectorString"]
        cve["cvss_v3_base_score"] = cvss_v3[0][0]["cvssData"]["baseScore"]
        cve["cvss_v3_base_severity"] = cvss_v3[0][0]["cvssData"]["baseSeverity"]
        cve["cvss_v3_exploitability_score"] = cvss_v3[0][0]["exploitabilityScore"]
        cve["cvss_v3_impact_score"] = cvss_v3[0][0]["impactScore"]

    cvss_v4 = nested_lookup(
        key="cvssMetricV4", document=vuln["cve"].get("metrics", {}), wild=True
    )
    if len(cvss_v4) > 0:
        # TODO verify these are correct once v4 comes out
        cve["cvss_v4_source"] = cvss_v4[0][0]["source"]
        cve["cvss_v4_type"] = cvss_v4[0][0]["type"]
        cve["cvss_v4_version"] = cvss_v4[0][0]["cvssData"]["version"]
        cve["cvss_v4_vector_string"] = cvss_v4[0][0]["cvssData"]["vectorString"]
        cve["cvss_v4_base_score"] = cvss_v4[0][0]["cvssData"]["baseScore"]
        cve["cvss_v4_base_severity"] = cvss_v4[0][0]["cvssData"]["baseSeverity"]
        cve["cvss_v4_exploitability_score"] = cvss_v4[0][0]["exploitabilityScore"]
        cve["cvss_v4_impact_score"] = cvss_v4[0][0]["impactScore"]

    cpes_t = list({tuple(cpe.split(":")[3:6]) for cpe in cve["cpe_list"]})

    # Transform it into nested dictionary
    cpes = {}
    for vendor, product, version in cpes_t:
        if vendor not in cpes:
            cpes[vendor] = []
        cpes[vendor].append((product, version))

    cve["vender_product"] = cpes
    return cve


def query_cve(cve_name):
    """Get CVE and product info from the database through the API."""
    cve_data = get_cve_and_products(cve_name)
    LOGGER.info(cve_data)
    return cve_data


def check_cve_is_synced():
    """Pull the last modified CVE from NIST and make sure it is in the database."""
    days = 1
    start_index = 0
    hours_back = 24
    now = datetime.now()
    while True:
        last_mod_start_date = (now - timedelta(hours=hours_back)).isoformat()
        last_mod_end_date = now.isoformat()

        params = (
            "?startIndex="
            + str(start_index)
            + "&lastModStartDate="
            + last_mod_start_date
            + "&lastModEndDate="
            + last_mod_end_date
        )

        payload = {}
        headers = {"apiKey": api_key}
        response = requests.request(
            "GET", nist_url + params, timeout=10, headers=headers, data=payload
        )

        result = response.json()
        start_index += result["resultsPerPage"]
        if len(result["vulnerabilities"]) == 0:
            LOGGER.info(
                "No CVEs modified in the last %s hours to compare against. Going further back",
                str(hours_back),
            )
            hours_back += 24
            days += 1
        else:
            break

        if days > 5:
            LOGGER.info("No update in the last 5 days. Exiting test.")
            return 0

    last_vuln = result["vulnerabilities"][-1]
    live_mod_date = datetime.fromisoformat(last_vuln["cve"]["lastModified"]).replace(
        tzinfo=timezone.utc
    )
    cve_name = last_vuln["cve"]["id"]

    cve_from_db = query_cve(cve_name)

    if cve_from_db:
        db_mod_date = datetime.fromisoformat(
            cve_from_db["cve_data"]["last_modified_date"]
        ).replace(tzinfo=timezone.utc)
        if db_mod_date == live_mod_date:
            LOGGER.info(db_mod_date)
            LOGGER.info(live_mod_date)
            LOGGER.info("Last Modified Date is synced for most recently updated CVE.")
        else:
            LOGGER.info(db_mod_date)
            LOGGER.info(live_mod_date)
            LOGGER.warning(
                "Last Modified Date does not match between database and NIST for the last updated CVE."
            )
    else:
        LOGGER.warning("Most recent update NIST CVE is not in the database.")

    return 0


def main():
    """Update CVE, CPE, and Vender tables using the NIST API."""
    # initial_fill()
    update_cves(24 * 5)
    # query_cve('CVE-2023-53465')
    # check_cve_is_synced()

    # cves = query_all_cves()
    # LOGGER.info(cves)


if __name__ == "__main__":
    sys.exit(main())
