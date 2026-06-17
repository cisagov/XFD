"""File for managing parameters and authentication for pe_source."""

# Standard Python Libraries
from configparser import ConfigParser
import os

# Third-Party Libraries
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Central .ini file
curr_dir = os.path.dirname(os.path.abspath(__file__))
ini_path = os.path.join(curr_dir, "..", "pe_reports", "parameters.ini")
INI_FILE = os.path.normpath(ini_path)


def get_params(section):
    """Retrieve parameters from the specified section of the central ini file."""
    # Verify .ini file found
    if os.path.isfile(INI_FILE):
        parser = ConfigParser()
        parser.read(INI_FILE, encoding="utf-8")
        # Verify specified section exists in .ini file
        if parser.has_section(section):
            params = dict(parser.items(section))
        else:
            raise Exception(
                'Section "{}" not found in the "{}" file'.format(section, INI_FILE)
            )
    else:
        raise Exception('File not found at this path: "{}"'.format(INI_FILE))
    return params


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
