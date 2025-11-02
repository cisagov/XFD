"""DMZ Sync helper functions."""
# Standard Python Libraries
import hashlib
import json
import logging
import os
import time

# Third-Party Libraries
import requests

SALT = os.getenv("CHECKSUM_SALT", "default_salt")
LOGGER = logging.getLogger(__name__)


def query_api(url_route, acronym, last_seen_after, page_size=50, page_number=1):
    """Pull dmz sync data from the DMZ."""
    url = os.getenv("DMZ_SYNC_ENDPOINT") + url_route

    payload = json.dumps(
        {
            "page": page_number,
            "page_size": page_size,
            "acronym": acronym,
            "since_date": last_seen_after,
        }
    )
    headers = {
        "X-API-KEY": os.environ.get("DMZ_API_KEY"),
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, headers=headers, data=payload, timeout=29)
    retry_count, max_retries, time_delay = 1, 10, 5
    while response.status_code != 200 and retry_count <= max_retries:
        if response.status_code:
            LOGGER.info(
                "Retrying MDL DMZ_sync endpoint (code %d), attempt %d of %d (url: %s)",
                response.status_code,
                retry_count,
                max_retries,
                url,
            )
        time.sleep(time_delay)
        response = requests.request(
            "POST", url, headers=headers, data=payload, timeout=29
        )
        retry_count += 1
        if retry_count > max_retries:
            LOGGER.warning("Failed to retrieve page %s", page_number)
            return None

    # Validate checksum by passing the response object
    is_valid = validate_response_checksum(response)

    if is_valid:
        LOGGER.info("✅ Checksum is valid!")
        return response
    else:
        LOGGER.warning("❌ Checksum validation failed!")
        return None


def validate_response_checksum(response):
    """Validate the checksum from an API response."""
    try:
        # Extract response JSON
        response_data = response.json()

        # Extract checksum from response headers
        received_checksum = response.headers.get("X-Salted-Checksum")
        if not received_checksum:
            LOGGER.warning("❌ No checksum found in headers!")
            return False

        # Recompute the checksum
        response_serialized = json.dumps(response_data, default=str, sort_keys=True)
        calculated_checksum = hashlib.sha256(
            (SALT + response_serialized).encode()
        ).hexdigest()

        return received_checksum == calculated_checksum

    except Exception as e:
        LOGGER.error("Error validating checksum: %s", e)
        return False
