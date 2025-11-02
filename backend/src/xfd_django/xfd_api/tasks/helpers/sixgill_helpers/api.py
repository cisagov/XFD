"""Cybersixgill API calls."""
# Standard Python Libraries
import json
import logging
import time

# Third-Party Libraries
import pandas as pd
import requests

from .config import cybersix_token

LOGGER = logging.getLogger(__name__)


def alerts_list(auth, organization_id, fetch_size, offset):
    """Get actionable alerts by ID using organization_id with optional filters."""
    # Call Cybersixgill's /actionable-alert endpoint
    url = "https://api.cybersixgill.com/alerts/actionable-alert"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    payload = {
        "organization_id": organization_id,
        "fetch_size": fetch_size,
        "offset": offset,
    }
    resp = requests.get(url, headers=headers, params=payload, timeout=10)

    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        if resp.status_code == 401:
            # Catch 401 token expired code
            LOGGER.warning(
                "Refreshing Cybersixgill API auth token due to 401 error code..."
            )
            # Tokens expire after 30m, refresh
            auth = cybersix_token()
        if resp.status_code == 400:
            # Log additional output if 400 code encountered
            LOGGER.error(
                "Received error code 400 from Cybersixgill's /actionable-alert endpoint"
            )
            LOGGER.error(resp.content)
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d) for chunk at offset %d, attempt %d of %d",
            endpoint_name,
            resp.status_code,
            offset,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, params=payload, timeout=10)
        retry_count += 1
    # Return result
    resp = resp.json()
    return [resp, auth]


def alerts_count(organization_id):
    """Get the total read and unread actionable alerts by organization."""
    # Call Cybersixgill's /count endpoint
    url = "https://api.cybersixgill.com/alerts/actionable_alert/count"
    auth = cybersix_token()
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    payload = {"organization_id": organization_id}
    resp = requests.get(url, headers=headers, params=payload, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            endpoint_name,
            resp.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, params=payload, timeout=10)
        retry_count += 1
    resp = resp.json()
    # Return result
    return resp


def intel_post(auth, query, frm, scroll, result_size):
    """Get intel items - advanced variation."""
    # Call Cybersixgill's /intel_items endpoint
    url = "https://api.cybersixgill.com/intel/intel_items"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    payload = {
        "query": query,
        "partial_content": False,
        "results_size": result_size,
        "scroll": scroll,
        "from": frm,
        "sort": "date",
        "sort_type": "desc",
        "highlight": False,
        "recent_items": False,
        "safe_content_size": True,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        if resp.status_code == 401:
            # Catch 401 token expired code
            LOGGER.warning(
                "Refreshing Cybersixgill API auth token due to 401 error code..."
            )
            # Tokens expire after 30m, refresh
            auth = cybersix_token()
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            endpoint_name,
            resp.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        retry_count += 1
    # Return result
    resp = resp.json()
    return [resp, auth]


def intel_post_next(auth, scroll_id):
    """Get intel_items based on specified scroll_id."""
    url = "https://api.cybersixgill.com/intel/intel_items/next"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    payload = {
        "scroll_id": scroll_id,
        "recent_items": False,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        if resp.status_code == 401:
            # Catch 401 token expired code
            LOGGER.warning(
                "Refreshing Cybersixgill API auth token due to 401 error code..."
            )
            # Tokens expire after 30m, refresh
            auth = cybersix_token()
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            resp.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        retry_count += 1
    # Return result
    resp = resp.json()
    return [resp, auth]


def credential_auth(auth, params):
    """Get data about a specific CVE."""
    # Call Cybersixgill's /leaks endpoint
    url = "https://api.cybersixgill.com/credentials/leaks"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        if resp.status_code == 401:
            # Catch 401 token expired code
            LOGGER.warning(
                "Refreshing Cybersixgill API auth token due to 401 error code..."
            )
            # Tokens expire after 30m, refresh
            auth = cybersix_token()
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            endpoint_name,
            resp.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        retry_count += 1
    resp = resp.json()
    # Return result
    return [resp, auth]


def dve_top_cves():
    """Retrieve the top 10 CVEs for this report period."""
    # Call Cybersixgill's /enrich endpoint
    url = "https://api.cybersixgill.com/dve_enrich/enrich"
    auth = cybersix_token()
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    data = json.dumps(
        {
            "filters": {
                "sixgill_rating_range": {"from": 6, "to": 10},
            },
            "results_size": 10,
            "enriched": True,
            "from_index": 0,
        }
    )
    resp = requests.post(url, headers=headers, data=data, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            endpoint_name,
            resp.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        retry_count += 1
    resp = resp.json()
    # Sort and clean top CVE data
    result_list = resp.get("objects")
    clean_top_10_cves = []
    for result in result_list:
        cve_id = result.get("name")
        dynamic_rating = result.get("x_sixgill_info").get("rating").get("current")
        if result.get("x_sixgill_info").get("nvd").get("v3") is None:
            nvd_v3_score = None
        else:
            nvd_v3_score = (
                result.get("x_sixgill_info").get("nvd").get("v3").get("current")
            )
        nvd_base_score = "{'v2': None, 'v3': " + str(nvd_v3_score) + "}"
        summary = result.get("description").strip()
        clean_cve = {
            "cve_id": cve_id,
            "dynamic_rating": dynamic_rating,
            "nvd_base_score": nvd_base_score,
            "summary": summary,
        }
        clean_top_10_cves.append(clean_cve)
    clean_top_10_cves = sorted(
        clean_top_10_cves, key=lambda d: d["dynamic_rating"], reverse=True
    )
    # Return result
    return clean_top_10_cves


def get_sixgill_organizations():
    """Get the list of organizations."""
    # Call Cybersixgill's /organization endpoint
    url = "https://api.cybersixgill.com/multi-tenant/organization"
    auth = cybersix_token()
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    orgs = requests.get(url, headers=headers, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while orgs.status_code != 200 and retry_count < max_retries:
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            endpoint_name,
            orgs.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        orgs = requests.get(url, headers=headers, timeout=10)
        retry_count += 1
    orgs = orgs.json()
    df_orgs = pd.DataFrame(orgs)
    df_orgs = df_orgs[["name", "organization_id"]]
    sixgill_dict = df_orgs.set_index("name").agg(list, axis=1).to_dict()
    # Return results
    return sixgill_dict


def org_assets(org_id):
    """Get organization assets."""
    # Call Cybersixgill's /assets endpoint
    url = f"https://api.cybersixgill.com/multi-tenant/organization/{org_id}/assets"
    auth = cybersix_token()
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Authorization": "Bearer " + auth,
    }
    payload = {"organization_id": org_id}
    resp = requests.get(url, headers=headers, params=payload, timeout=10)
    # Retry clause in case Cybersixgill's API falters
    retry_count, max_retries, time_delay = 0, 10, 5
    while resp.status_code != 200 and retry_count < max_retries:
        endpoint_name = url.split("/")[-1]
        LOGGER.warning(
            "Retrying Cybersixgill /%s endpoint (code %d), attempt %d of %d",
            endpoint_name,
            resp.status_code,
            retry_count + 1,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, params=payload, timeout=10)
        retry_count += 1
    resp = resp.json()
    # Return result
    return resp
