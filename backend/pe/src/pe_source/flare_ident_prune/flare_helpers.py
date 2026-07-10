"""Frequently used helper and API functions for Flare scripts."""

# Standard Python Libraries
import logging
import os
import time

# Third-Party Libraries
import requests
from requests.auth import HTTPBasicAuth

# cisagov Libraries
from pe_source.data.pe_db.config import get_params

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
