"""dmz_sync_cybersix.py.

Fetch paginated Sixgill data from the DMZ sync endpoint
and upsert into the local database.
"""

# Standard Python Libraries
import datetime
import hashlib
import json
import logging
import os
from urllib.parse import urljoin

# Third-Party Libraries
import django
import requests

# --- Django setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
# --- Models ---
from xfd_mini_dl.models import (
    CredentialBreaches,
    CredentialExposures,
    Mentions,
    SixgillAlerts,
    SubDomains,
    TopCves,
)

# --- Constants & Logging ---
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)

SALT = os.getenv("CHECKSUM_SALT", "default_salt")
HEADERS = {
    "X-API-KEY": os.getenv("DMZ_API_KEY"),
    "Content-Type": "application/json",
}

# Build the endpoint URL (/sync → /dmz_sync/cybersix_sync)
base = os.getenv("DMZ_SYNC_ENDPOINT", "").rstrip("/")
if base.endswith("/sync"):
    API_URL = base.rsplit("/", 1)[0] + "/dmz_sync/cybersix_sync"
else:
    API_URL = urljoin(base + "/", "dmz_sync/cybersix_sync")


def _parse_dt(val):
    """Parse ISO8601 string (or return as-is if already a datetime)."""
    if isinstance(val, datetime.datetime):
        return val
    if not val:
        return None
    try:
        return datetime.datetime.fromisoformat(val)
    except Exception:
        return None


def handler(event):
    """Retrieve and save Sixgill data for each organization."""
    try:
        main()
        return {
            "status_code": 200,
            "body": "DMZ Sixgill sync completed successfully.",
        }
    except Exception as error:
        LOGGER.error("Sync error: %s", error)
        return {"status_code": 500, "body": str(error)}


def main():
    """Fetch and save DMZ Sixgill data, paging through each org."""
    # Ensure our DataSource record exists
    sixgill_source, _ = DataSource.objects.get_or_create(
        name="Sixgill",
        defaults={
            "description": "Darkweb monitoring via Sixgill",
            "last_run": timezone.now().date(),
        },
    )

    # Loop over every organization
    for organization in Organization.objects.all():
        LOGGER.info(
            "Processing organization: %s (%s)",
            organization.acronym,
            organization.name,
        )

        current_page = 1
        total_pages = 2  # dummy to enter loop

        while current_page <= total_pages:
            since_timestamp_str = calculate_days_back(15)
            response = fetch_sixgill_page(
                organization_acronym=organization.acronym,
                page_number=current_page,
                page_size=PAGE_SIZE,

            )
            if not response:
                LOGGER.error("Failed to fetch page %d for %s", current_page, organization.acronym)
                break

            if not validate_response_checksum(response):
                raise RuntimeError(f"Checksum mismatch on page {current_page}")

            wrapper = response.json()
            if wrapper.get("status") != "ok":
                raise RuntimeError(f"Bad status on page {current_page}: {wrapper}")

            payload = wrapper["payload"]
            total_pages = payload["total_pages"]
            fetched_page = payload["current_page"]
            data = payload["data"]

            LOGGER.info(
                "Org %s page %d/%d: alerts=%d, mentions=%d, breaches=%d, subdomains=%d, exposures=%d, topcves=%d",
                organization.acronym,
                fetched_page,
                total_pages,
                len(data["alerts"]),
                len(data["mentions"]),
                len(data["breaches"]),
                len(data["subdomains"]),
                len(data["exposures"]),
                len(data["topcves"]),
            )

            save_sixgill_payload(
                payload=data,
                organization=organization,
                data_source=sixgill_source,
            )

            if fetched_page >= total_pages:
                break

            current_page += 1
            time.sleep(1)  # throttle between pages


def fetch_sixgill_page(organization_acronym: str, page_number: int, page_size: int, since_timestamp: str):
    """Fetch a single page of Sixgill data for the given org."""
    request_body = {
        "org_acronym": organization_acronym,
        "page": page_number,
        "page_size": page_size,
        "since_timestamp": since_timestamp,
    }
    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json=request_body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response
    except requests.RequestException as error:
        LOGGER.error(
            "Error fetching Sixgill page %d for %s: %s",
            page_number,
            organization_acronym,
            error,
        )
        return None


def validate_response_checksum(response) -> bool:
    """Recompute SHA-256(SALT + stable_json) and compare to X-Salted-Checksum."""
    try:
        data = response.json()
        received_checksum = response.headers.get("X-Salted-Checksum")
        if not received_checksum:
            LOGGER.warning("No X-Salted-Checksum header on response")
            return False

        stable = json.dumps(data, default=str, sort_keys=True)
        calculated = hashlib.sha256((SALT + stable).encode()).hexdigest()
        return received_checksum == calculated
    except Exception as error:
        LOGGER.error("Checksum validation error: %s", error)
        return False


def save_sixgill_payload(payload: dict, organization, data_source):
    """
    Upsert each Sixgill table from the payload JSON, scoped to org & data_source.
    """
    # Alerts
    for record in payload.get("alerts", []):
        SixgillAlerts.objects.update_or_create(
            sixgill_id=record["sixgill_id"],
            organization=organization,
            defaults={
                "alert_name": record.get("alert_name"),
                "content": record.get("content", "")[:2000],
                "date": _parse_dt(record.get("date")),
                "read": record.get("read"),
                "severity": record.get("severity"),
                "site": record.get("site"),
                "threat_level": record.get("threat_level"),
                "threats": record.get("threats"),
                "title": record.get("title"),
                "category": record.get("category"),
                "lang": record.get("lang"),
                "content_snip": record.get("content_snip"),
                "asset_mentioned": record.get("asset_mentioned"),
                "asset_type": record.get("asset_type"),
                "data_source": data_source,
            },
        )

    # Mentions
    for record in payload.get("mentions", []):
        Mentions.objects.update_or_create(
            sixgill_mention_id=record["sixgill_mention_id"],
            organization=organization,
            defaults={
                "category": record.get("category"),
                "collection_date": _parse_dt(record.get("collection_date")),
                "content": record.get("content"),
                "creator": record.get("creator"),
                "date": _parse_dt(record.get("date")),
                "post_id": record.get("post_id"),
                "lang": record.get("lang"),
                "rep_grade": record.get("rep_grade"),
                "site": record.get("site"),
                "site_grade": record.get("site_grade"),
                "title": record.get("title"),
                "type": record.get("type"),
                "url": record.get("url"),
                "comments_count": record.get("comments_count"),
                "sub_category": record.get("sub_category", "NaN"),
                "tags": record.get("tags"),
                "title_translated": record.get("title_translated"),
                "content_translated": record.get("content_translated"),
                "detected_lang": record.get("detected_lang"),
                "data_source": data_source,
            },
        )

    # Top CVEs
    for record in payload.get("topcves", []):
        TopCves.objects.update_or_create(
            cve_id=record["cve_id"],
            date=_parse_dt(record.get("date")),
            organization=organization,
            defaults={
                "summary": record.get("summary"),
                "dynamic_rating": record.get("dynamic_rating"),
                "nvd_base_score": record.get("nvd_base_score"),
                "data_source": data_source,
            },
        )

