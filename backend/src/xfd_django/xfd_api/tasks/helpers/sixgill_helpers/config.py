"""Tasks for creating cybersix token for cybersixgill scan."""

# Standard Python Libraries
import logging
import os
import time

# Third-Party Libraries
import requests


def cybersix_token():
    """Retrieve bearer token from Cybersixgill using environment variables."""
    client_id = os.getenv("SIXGILL_CLIENT_ID")
    client_secret = os.getenv("SIXGILL_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise Exception("Cybersixgill credentials not found in environment variables.")

    url = "https://api.cybersixgill.com/auth/token/"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }

    for attempt in range(1, 15):
        try:
            resp = requests.post(url, headers=headers, data=payload, timeout=10)
            resp.raise_for_status()
            return resp.json()["access_token"]
        except Exception as e:
            logging.warning(f"Token request failed (attempt {attempt}): {e}")
            time.sleep(10)

    raise Exception("Failed to retrieve Cybersixgill token after multiple attempts.")
