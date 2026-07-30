"""Frequently used helper and API functions for Flare scripts."""

# Standard Python Libraries
import logging
import os
import re
import time

# Third-Party Libraries
from pe_source.flare_events.flare_config import get_params
import requests
from requests.auth import HTTPBasicAuth

# Setup logging
LOGGER = logging.getLogger(__name__)


def _flare_tenant_id() -> str:
    """Return Flare tenant id from the environment (fresh each call)."""
    return os.environ.get("FLARE_TENANT_ID", "")


def _flare_api_auth() -> HTTPBasicAuth | None:
    """Return HTTPBasicAuth for the single key assigned to this worker."""
    api_key = os.environ.get("FLARE_API_KEY", "").strip()
    if not api_key:
        # Legacy fallback for local configs that still set numbered keys.
        params = dict(get_params("flare"))
        api_key = str(params.get("api_key") or "").strip()
    if not api_key:
        return None
    return HTTPBasicAuth("", api_key)


def get_flare_token(api_key: str | None = None, tenant_id: str | None = None):
    """Get Flare API authentication token.

    When api_key is provided, validate/generate a token with that key (used by
    peScanController). Otherwise use the worker's assigned FLARE_API_KEY.
    """
    api_auth: HTTPBasicAuth | None
    if api_key is not None:
        api_auth = HTTPBasicAuth("", str(api_key).strip())
    else:
        api_auth = _flare_api_auth()
    if api_auth is None:
        LOGGER.error("Error: No Flare API key configured (FLARE_API_KEY)")
        return None

    resolved_tenant = tenant_id if tenant_id is not None else _flare_tenant_id()
    if not resolved_tenant:
        LOGGER.error("Error: FLARE_TENANT_ID is not set")
        return None

    # Get API token
    token_url = "https://api.flare.io/tokens/generate"  # nosec
    headers = {
        "Content-Type": "application/json",
    }
    data = f'{{"tenant_id": {resolved_tenant}}}'
    resp = requests.post(
        token_url, data=data, headers=headers, auth=api_auth, timeout=60
    )
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            "\tRetrying Flare token API endpoint (code %s), attempt %s of %s",
            resp.status_code,
            retry_count,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.post(
            token_url, data=data, headers=headers, auth=api_auth, timeout=60
        )
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error("Error: Failed to retrieve Flare auth token")
        return None

    payload = resp.json()
    return payload.get("token")


def validate_flare_api_key(api_key: str, tenant_id: str | None = None) -> bool:
    """Return True when the Flare API accepts the key and returns a token."""
    token = get_flare_token(api_key=api_key, tenant_id=tenant_id)
    return bool(token)


def get_ident_group_info(org_name):
    """Retrieve identifier group info for the specified organization."""
    flare_token = get_flare_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {flare_token}",
    }
    # PE&T parent group id
    group_id = 191286
    # Get the group id for the specified organization
    orgs_url = "https://api.flare.io/firework/v2/assets/groups/"
    orgs_resp = requests.get(orgs_url, headers=headers, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 10, 5
    while orgs_resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            "\tRetrying Flare identifier group info API endpoint (code %s), attempt %s of %s",
            orgs_resp.status_code,
            retry_count,
            max_retries,
        )
        time.sleep(time_delay)
        orgs_resp = requests.get(orgs_url, headers=headers, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error("Error: Failed to retrieve Flare identifier group info")
        return None
    else:
        orgs_resp = orgs_resp.json()
        orgs_list = orgs_resp.get("assets_groups")
        org_id = [
            o
            for o in orgs_list
            if o["name"] == org_name and o["parent_group_id"] == group_id
        ][0].get("id")
        # Return results
        return {
            "name": org_name,
            "id": org_id,
        }


def get_ident_by_group_id(ident_group_id):
    """Retrieve all identifiers for the specified group ID."""
    flare_token = get_flare_token()
    url = "https://api.flare.io/firework/v3/identifiers/"
    params = {
        "parent_group_id": ident_group_id,
    }
    headers = {"Authorization": f"Bearer {flare_token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            "\tRetrying Flare identifiers by group ID API endpoint (code %s), attempt %s of %s",
            resp.status_code,
            retry_count,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error("Error: Failed to retrieve Flare identifiers by group ID")
        return None
    else:
        resp = resp.json()
        # Format identifier info
        ident_list = []
        for ident in resp.get("items"):
            ident_id = ident.get("id")
            ident_value = ident.get("name")
            ident_type = ident.get("type")
            ident_dict = {"id": ident_id, "value": ident_value, "type": ident_type}
            ident_list.append(ident_dict)
        # Return results
        if len(ident_list) == 0:
            return [
                {
                    "id": None,
                    "value": None,
                    "type": None,
                }
            ]
        else:
            return ident_list


def get_ident_by_group_id_chunk(flare_token, params):
    """Retrieve chunk of identifiers for the specified group ID."""
    url = "https://api.flare.io/firework/v3/identifiers/"
    headers = {"Authorization": f"Bearer {flare_token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            "\tRetrying Flare identifiers by group ID API endpoint (code %s), attempt %s of %s",
            resp.status_code,
            retry_count,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error("Error: Failed to retrieve Flare identifiers by group ID")
        return None
    else:
        resp = resp.json()
        next_val = resp.get("next")
        # Format identifier info
        ident_list = []
        for ident in resp.get("items"):
            ident_id = ident.get("id")
            ident_value = ident.get("name")
            ident_type = ident.get("type")
            ident_dict = {"id": ident_id, "value": ident_value, "type": ident_type}
            ident_list.append(ident_dict)
        # Log info
        num_items = len(ident_list)
        more_data = False
        if resp.get("next"):
            more_data = True
        LOGGER.info("\tChunk retrieved, contained %s items", num_items)
        LOGGER.info(
            "\tIs there another chunk to retrieve? %s (next = %s)",
            more_data,
            next_val,
        )
        # Return results
        return {
            "ident_list": ident_list,
            "next_val": next_val,
        }


def get_all_ident_by_group_id(ident_group_id):
    """Retrieve all identifiers belonging to the specified identifier group (organization)."""
    LOGGER.info(
        "Retrieving all identifiers for the identifier group: %s", ident_group_id
    )
    flare_token = get_flare_token()
    results_list = []
    more_data = False
    curr_next = ""
    # Make initial data feed call
    LOGGER.info("Working on group identifiers chunk 1")
    ini_params = {
        "parent_group_id": ident_group_id,
    }
    ini_resp = get_ident_by_group_id_chunk(flare_token, ini_params)
    results_list += ini_resp.get("ident_list")
    # Check if there's any more data to retrieve
    if ini_resp.get("next_val"):
        more_data = True
        curr_next = ini_resp.get("next_val")
    # If there's a "next" value, continue fetching data
    retrieve_ct = 2
    while more_data:
        # Rate control delay
        time.sleep(1)
        # Refresh auth token every ~30 min (avg event retrieval api call ~= 1.5s)
        if retrieve_ct % 500 == 0:  # default 1200
            LOGGER.warning("Refreshing Flare API auth token for intial event retrieval")
            LOGGER.info("REFRESHING FLARE AUTH TOKEN")
            flare_token = get_flare_token()
        LOGGER.info("Working on group identifiers chunk %s", retrieve_ct)
        # Make API call for current chunk
        curr_params = {
            "parent_group_id": ident_group_id,
            "from": curr_next,
        }
        curr_resp = get_ident_by_group_id_chunk(flare_token, curr_params)
        # Handle edge case where no results found for this chunk
        if len(curr_resp.get("ident_list")) != 0:
            # Append results
            results_list += curr_resp.get("ident_list")
        # Check if there's anymore data to retrieve
        if curr_resp.get("next_val"):
            # If there's more data, update next value
            curr_next = curr_resp.get("next_val")
        else:
            # If no next value, there's no more data to retrieve
            more_data = False
        retrieve_ct += 1
    # Once all data has been retrieved, format and return results
    LOGGER.info(
        "Total number of identifiers retrieved for this group: %s", len(results_list)
    )
    if len(results_list) == 0:
        return [
            {
                "id": None,
                "value": None,
                "type": None,
            }
        ]
    else:
        return results_list


def get_event_details(event_uid, token):
    """Get additional details for the specified Flare event uid."""
    event_detail_url = f"https://api.flare.io/firework/v2/activities/{event_uid}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    resp = requests.get(event_detail_url, headers=headers, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 10, 5
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            "\tRetrying Flare event detail API endpoint (code %s), attempt %s of %s",
            resp.status_code,
            retry_count,
            max_retries,
        )
        time.sleep(time_delay)
        resp = requests.get(event_detail_url, headers=headers, timeout=60)
        retry_count += 1
    # Return results
    if retry_count == max_retries + 1:
        LOGGER.error("Error: Failed to retrieve Flare event details for %s", event_uid)
        return None
    else:
        return resp.json()


def remove_emoji(txt):
    """Remove emoji characters from a given string."""
    # Regex pattern to match various emoji Unicode ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub(r"", txt)
