"""Frequently used helper and API functions for Flare scripts."""

# Standard Python Libraries
import logging
import os
import re
import time

# Third-Party Libraries
import requests
from requests.auth import HTTPBasicAuth

# cisagov Libraries
from flare_events.flare_config import get_params 

# Setup logging
LOGGER = logging.getLogger(__name__)

# Retrieve available Flare API credentials
param_dict = dict(get_params("flare"))
TENANT_ID = param_dict.get("tenant_id")
# Convert keys to HTTPBasicAuth objects
for key in param_dict.keys():
    if "api_key" in key:
        param_dict[key] = HTTPBasicAuth("", str(param_dict.get(key)))
PARAM_DICT = param_dict

def get_flare_token():
    """Get Flare API authentication token."""
    # Use the API key specified by env variable
    key_num = os.getenv("FLARE_KEY_NUM")
    api_auth = PARAM_DICT.get(f"api_key_{key_num}")
    # Get API token
    token_url = "https://api.flare.io/tokens/generate"  # nosec
    headers = {
        "Content-Type": "application/json",
    }
    data = f'{{"tenant_id": {TENANT_ID}}}'
    resp = requests.post(
        token_url, data=data, headers=headers, auth=api_auth, timeout=60
    )
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            f"\tRetrying Flare token API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
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
    else:
        resp = resp.json()
        return resp.get("token")
    

def get_all_ident_by_group_id(ident_group_id):
    """Retrieve all identifiers belonging to the specified identifier group (organization)."""
    print(f"Retrieving all identifiers for the identifier group: {ident_group_id}")
    flare_token = get_flare_token()
    results_list = []
    more_data = False
    curr_next = ""
    # chunk_size = 10  # max size is 10
    # Make initial data feed call
    print("Working on group identifiers chunk 1")
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
            print("REFRESHING FLARE AUTH TOKEN")
            flare_token = get_flare_token()
        print(f"Working on group identifiers chunk {retrieve_ct}")
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
    print(f"Total number of identifiers retrieved for this group: {len(results_list)}")
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


def get_ident_by_group_id_chunk(flare_token, params):
    """Retrieve chunk of identifiers for the specified group ID."""
    url = "https://api.flare.io/firework/v3/identifiers/"
    headers = {"Authorization": f"Bearer {flare_token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    # Retry clause in case API falters
    retry_count, max_retries, time_delay = 1, 5, 3
    while resp.status_code != 200 and retry_count <= max_retries:
        LOGGER.warning(
            f"\tRetrying Flare identifiers by group ID API endpoint (code {resp.status_code}), attempt {retry_count} of {max_retries}"
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
        print(f"\tChunk retrieved, contained {num_items} items")
        print(f"\tIs there another chunk to retrieve? {more_data} (next = {next_val})")
        # Return results
        return {
            "ident_list": ident_list,
            "next_val": next_val,
        }

