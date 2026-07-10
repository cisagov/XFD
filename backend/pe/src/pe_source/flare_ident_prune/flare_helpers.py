"""Frequently used helper and API functions for Flare scripts."""

# Standard Python Libraries
import logging
import os
import time

# Third-Party Libraries
import requests
from requests.auth import HTTPBasicAuth

# Setup logging
LOGGER = logging.getLogger(__name__)


def get_flare_token():
    """Get Flare API authentication token."""
    # Use the API key specified by env variable
    key_num = os.getenv("FLARE_KEY_NUM", "1")
    api_key = os.environ.get(f"FLARE_API_KEY_{key_num}")
    tenant_id = os.environ.get("FLARE_TENANT_ID")

    if not api_key:
        LOGGER.error("FLARE_API_KEY_%s environment variable is not set", key_num)
        return None
    if not tenant_id:
        LOGGER.error("FLARE_TENANT_ID environment variable is not set")
        return None

    api_auth = HTTPBasicAuth("", api_key)
    # Get API token
    token_url = "https://api.flare.io/tokens/generate"  # nosec
    headers = {
        "Content-Type": "application/json",
    }
    data = f'{{"tenant_id": {tenant_id}}}'
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
