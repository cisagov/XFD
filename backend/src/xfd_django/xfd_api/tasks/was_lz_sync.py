"""
WAS Findings LZ sync scan hitting the FastAPI endpoint.

Mirrors the conventions used in nist_lz_sync.py.
"""

# Standard Python Libraries
# --- Standard Libraries ---
from datetime import date, datetime
import hashlib
import json
import logging
import os
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin

# Third-Party Libraries
# --- Third-Party Libraries ---
import django
from django.db import transaction
import requests

# --- Django setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
# --- Project Imports ---
from xfd_api.helpers.date_time_helpers import calculate_days_back
from xfd_mini_dl.models import WasFindings

# --- Constants & Logging ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)

SALT = os.getenv("CHECKSUM_SALT", "default_salt")
HEADERS = {
    "X-API-KEY": os.getenv("DMZ_API_KEY"),
    "Content-Type": "application/json",
}

# e.g. “https://api.staging-cd.crossfeed.cyber.dhs.gov/sync”
base_url = os.getenv("DMZ_SYNC_ENDPOINT", "").rstrip("/")

if base_url.endswith("/sync"):
    # drop “/sync” and append “/was_findings”
    WAS_API_URL = base_url.rsplit("/", 1)[0] + "/dmz_sync/was_findings"
else:
    # fallback: join “/was_findings” onto whatever they provided
    WAS_API_URL = urljoin(base_url + "/", "dmz_sync/was_findings")


def validate_response_checksum(response: requests.Response) -> bool:
    """
    Validate the checksum from the API.

    Args:
        response: HTTP response returned by the WAS findings endpoint.

    Returns:
        True if checksum matches; otherwise False.
    """
    try:
        response_data = response.json()
        received_checksum = response.headers.get("X-Salted-Checksum")
        if not received_checksum:
            LOGGER.warning("No checksum header")
            return False

        serialized = json.dumps(response_data, default=str, sort_keys=True)
        calculated = hashlib.sha256((SALT + serialized).encode()).hexdigest()
        return received_checksum == calculated
    except Exception as error:
        LOGGER.error("Error validating checksum: %s", error)
        return False


def _parse_date_string(value: Optional[str]) -> Optional[date]:
    """
    Parse an ISO-8601 date string into a date object.

    Args:
        value: ISO date string (YYYY-MM-DD) or None.

    Returns:
        A date instance or None if parsing fails.
    """
    if not value:
        return None
    try:
        # Supports 'YYYY-MM-DD' directly; if a datetime is sent, take the date part.
        parsed = datetime.fromisoformat(value)
        return parsed.date()
    except Exception:
        return None


@transaction.atomic
def save_was_findings_to_db(finding_list: Iterable[Dict[str, Any]]) -> None:
    """
    Upsert each WAS finding dict into the local DB.

    Args:
        finding_list: Iterable of dictionaries representing WAS findings.
    """
    for item in finding_list:
        finding_uid = item.get("finding_uid")
        if not finding_uid:
            LOGGER.warning("Skipping WAS record with missing finding_uid")
            continue

        defaults = {
            "finding_type": item.get("finding_type"),
            "webapp_id": item.get("webapp_id"),
            "was_org_id": item.get("was_org_id"),
            "owasp_category": item.get("owasp_category"),
            "severity": item.get("severity"),
            "times_detected": item.get("times_detected"),
            "base_score": item.get("base_score"),
            "temporal_score": item.get("temporal_score"),
            "fstatus": item.get("fstatus"),
            "last_detected": _parse_date_string(item.get("last_detected")),
            "first_detected": _parse_date_string(item.get("first_detected")),
            "is_remediated": item.get("is_remediated"),
            "potential": item.get("potential"),
            "webapp_url": item.get("webapp_url"),
            "webapp_name": item.get("webapp_name"),
            "name": item.get("name"),
            "cvss_v3_attack_vector": item.get("cvss_v3_attack_vector"),
            "cwe_list": item.get("cwe_list"),
            "wasc_list": item.get("wasc_list"),
            "last_tested": _parse_date_string(item.get("last_tested")),
            "fixed_date": _parse_date_string(item.get("fixed_date")),
            "is_ignored": item.get("is_ignored"),
            "url": item.get("url"),
            "qid": item.get("qid"),
            "response": item.get("response"),
            # Foreign keys (nullable) — expect API to provide UUID strings if present
            "cve_id": item.get("cve_id"),
            "sub_domain_id": item.get("sub_domain_id"),
        }

        try:
            WasFindings.objects.update_or_create(
                finding_uid=finding_uid, defaults=defaults
            )
        except Exception as error:
            LOGGER.warning(
                "Error saving WAS finding %s: %s", finding_uid, error, exc_info=True
            )


def handler(command_options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fetch all WAS findings and save them locally.

    Features:
    - Paginates with 'page' and 'page_size'
    - Sends JSON payload
    - Validates salted checksum header
    - Upserts records
    """
    days_back_default = 15
    if command_options and isinstance(command_options.get("days_back"), int):
        days_back_default = max(0, command_options["days_back"])

    since_date = calculate_days_back(days_back_default)

    try:
        LOGGER.info("Starting WAS findings sync…")
        page = 1
        per_page = 200
        done = False
        total_imported = 0

        while not done:
            payload = {
                "page": page,
                "page_size": per_page,
                "since_date": since_date,
            }

            response = requests.post(
                WAS_API_URL, headers=HEADERS, json=payload, timeout=60
            )
            response.raise_for_status()

            if not validate_response_checksum(response):
                LOGGER.error("Checksum mismatch!")
                return {"statusCode": 500, "body": "Checksum mismatch"}

            body = response.json()
            if body.get("status") != "ok":
                LOGGER.error("API returned bad status: %s", body)
                return {"statusCode": 500, "body": "Bad status"}

            # NOTE: read paging info from the BODY (not the Response object)
            total_pages = body.get("total_pages", 1)
            current_page = body.get("current_page", page)

            records = body.get("payload", [])
            LOGGER.info("Fetched %s WAS findings", len(records))
            save_was_findings_to_db(records)
            total_imported += len(records)

            if current_page >= total_pages:
                done = True
            else:
                page += 1

        LOGGER.info(
            "WAS findings sync completed successfully; total_imported=%s",
            total_imported,
        )
        return {
            "statusCode": 200,
            "body": f"WAS findings sync completed successfully. total_imported={total_imported}",
        }

    except Exception as error:
        LOGGER.error("Sync error: %s", error, exc_info=True)
        return {"statusCode": 500, "body": str(error)}
