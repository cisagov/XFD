"""File for managing parameters and authentication for pe_source."""

# Standard Python Libraries
import logging
import os

# Third-Party Libraries
import requests
from requests.adapters import HTTPAdapter
import shodan
from urllib3.util.retry import Retry

# Setup Logging
LOGGER = logging.getLogger(__name__)


def create_retry_session(
    retries=5, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504)
):
    """Create a requests Session with automatic retry and backoff logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,  # Max retries across all failure types
        read=retries,  # Max retries for read errors
        connect=retries,  # Max retries for connection errors
        backoff_factor=backoff_factor,  # Delay grows exponentially: <backoff_factor> x 2^(<num_total_retries> - 1))
        status_forcelist=status_forcelist,  # Retry on these specific status codes
        allowed_methods=["GET", "POST", "PUT"],  # Methods to retry
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_dnsmonitor_token():
    """Retreive the DNSMonitor auth token."""
    # Setup API call
    session = create_retry_session()
    url = "https://argosecure.com/dhs/connect/token"
    payload = {
        "client_id": os.environ.get("DNSMONITOR_CLIENT_ID"),
        "client_secret": os.environ.get("DNSMONITOR_CLIENT_SECRET"),
        "grant_type": "client_credentials",
        "scope": "DNSMonitorAPI",
    }
    headers = {}
    files = []
    # Make API Call
    try:
        resp = session.post(url, headers=headers, data=payload, files=files, timeout=60)
        resp.raise_for_status()
        resp = resp.json()
        return resp.get("access_token")
    except requests.exceptions.HTTPError as http_err:
        LOGGER.error(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        LOGGER.error(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        LOGGER.error(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as err:
        LOGGER.error(f"Unexpected error occurred: {err}")
    return None


def shodan_api_init():
    """Connect to Shodan API using the single key assigned to this worker."""
    api_key = os.environ.get("PE_SHODAN_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "PE_SHODAN_API_KEY is not set; peScanController assigns one key per worker"
        )

    # Key is validated in peScanController; skip api.info() (1 rps Shodan limit).
    LOGGER.info("Initialized Shodan API with PE_SHODAN_API_KEY")
    return [shodan.Shodan(api_key)]
