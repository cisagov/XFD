#!/usr/bin/env python
"""
dmz_sync_cybersix.py

Fetch paginated Sixgill data from the DMZ sync endpoint
and upsert into the local database.
"""

import os
import json
import hashlib
import logging
from urllib.parse import urljoin
import datetime

import django
import requests

# --- Django setup ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# --- Models ---
from xfd_mini_dl.models import (
    SixgillAlerts,
    Mentions,
    CredentialBreaches,
    SubDomains,
    CredentialExposures,
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


def save_cybersix_payload(payload):
    """
    Upsert each Sixgill table from the payload JSON.

    payload = {
      "alerts": [...],
      "mentions": [...],
      "breaches": [...],
      "subdomains": [...],
      "exposures": [...],
      "topcves": [...],
    }
    """
    # 1) Alerts
    for rec in payload.get("alerts", []):
        SixgillAlerts.objects.update_or_create(
            sixgill_id=rec["sixgill_id"],
            defaults={
                "alert_name":      rec.get("alert_name"),
                "content":         rec.get("content", "")[:2000],
                "date":            _parse_dt(rec.get("date")),
                "read":            rec.get("read"),
                "severity":        rec.get("severity"),
                "site":            rec.get("site"),
                "threat_level":    rec.get("threat_level"),
                "threats":         rec.get("threats"),
                "title":           rec.get("title"),
                "user_id":         rec.get("user_id"),
                "category":        rec.get("category"),
                "lang":            rec.get("lang"),
                "content_snip":    rec.get("content_snip"),
                "asset_mentioned": rec.get("asset_mentioned"),
                "asset_type":      rec.get("asset_type"),

            },
        )

    # 2) Mentions
    for rec in payload.get("mentions", []):
        Mentions.objects.update_or_create(
            sixgill_mention_id=rec["sixgill_mention_id"],
            defaults={
                "category":           rec.get("category"),
                "collection_date":    _parse_dt(rec.get("collection_date")),
                "content":            rec.get("content"),
                "creator":            rec.get("creator"),
                "date":               _parse_dt(rec.get("date")),
                "post_id":            rec.get("post_id"),
                "lang":               rec.get("lang"),
                "rep_grade":          rec.get("rep_grade"),
                "site":               rec.get("site"),
                "site_grade":         rec.get("site_grade"),
                "title":              rec.get("title"),
                "type":               rec.get("type"),
                "url":                rec.get("url"),
                "comments_count":     rec.get("comments_count"),
                "sub_category":       rec.get("sub_category", "NaN"),
                "tags":               rec.get("tags"),
                "title_translated":   rec.get("title_translated"),
                "content_translated": rec.get("content_translated"),
                "detected_lang":      rec.get("detected_lang"),
                "organization_id":    rec.get("organization_id"),
                "data_source_id":     rec.get("data_source_id"),
            },
        )

    # 3) Breaches
    for rec in payload.get("breaches", []):
        CredentialBreaches.objects.update_or_create(
            breach_name=rec["breach_name"],
            defaults={
                "exposed_cred_count": rec.get("exposed_cred_count"),
                "breach_date":        _parse_dt(rec.get("breach_date")),
                "added_date":         _parse_dt(rec.get("added_date")),
                "modified_date":      _parse_dt(rec.get("modified_date")),
                "password_included":  rec.get("password_included"),
                "data_source_id":     rec.get("data_source_id"),
            },
        )

    # 4) SubDomains
    for rec in payload.get("subdomains", []):
        SubDomains.objects.update_or_create(
            id=rec["id"],  # or use another unique key
            defaults={
                "organization_id":  rec.get("organization_id"),
                "sub_domain":       rec.get("sub_domain"),
                "is_root_domain":   rec.get("is_root_domain", False),
                "first_seen":       _parse_dt(rec.get("first_seen")),
                "last_seen":        _parse_dt(rec.get("last_seen")),
                "from_root_domain": rec.get("from_root_domain"),
                "identified":       rec.get("identified", False),
                "current":          rec.get("current", False),
                "subdomain_source": rec.get("subdomain_source"),
                "data_source_id":   rec.get("data_source_id"),
            },
        )

    # 5) CredentialExposures
    for rec in payload.get("exposures", []):
        CredentialExposures.objects.update_or_create(
            email=rec["email"],
            breach_name=rec["breach_name"],
            defaults={
                "organization_id":      rec.get("organization_id"),
                "root_domain":          rec.get("root_domain"),
                "sub_domain_string":    rec.get("sub_domain"),
                "sub_domain_id":        rec.get("sub_domain_id"),
                "credential_breach_id": rec.get("credential_breach_id"),
                "modified_date":        _parse_dt(rec.get("modified_date")),
                "created_at":           _parse_dt(rec.get("created_at")),
                "data_source_id":       rec.get("data_source_id"),
                "password":             rec.get("password"),
                "hash_type":            rec.get("hash_type"),
                "intelx_system_id":     rec.get("intelx_system_id", ""),
            },
        )

    # 6) TopCves
    for rec in payload.get("topcves", []):
        TopCves.objects.update_or_create(
            cve_id=rec["cve_id"],
            date=_parse_dt(rec["date"]),
            defaults={
                "summary":        rec.get("summary"),
                "dynamic_rating": rec.get("dynamic_rating"),
                "nvd_base_score": rec.get("nvd_base_score"),
                "data_source_id": rec.get("data_source_id"),
            },
        )


def validate_response_checksum(response) -> bool:
    """
    Recompute SHA-256(SALT + stable_json) and compare to X-Salted-Checksum header.
    """
    try:
        data = response.json()
        received = response.headers.get("X-Salted-Checksum")
        if not received:
            LOGGER.warning("No checksum header")
            return False

        stable = json.dumps(data, default=str, sort_keys=True)
        calc = hashlib.sha256((SALT + stable).encode()).hexdigest()
        return received == calc
    except Exception as e:
        LOGGER.error("Error validating checksum: %s", e)
        return False


def handler():
    """
    Loop through all pages of the cybersix endpoint and upsert every table
    via save_cybersix_payload().
    """
    try:
        page = 1
        page_size = int(os.getenv("SYNC_PAGE_SIZE", "200"))

        while True:
            LOGGER.info("Fetching page %s …", page)
            resp = requests.post(
                API_URL,
                headers=HEADERS,
                json={"page": page, "page_size": page_size},
                timeout=60,
            )
            resp.raise_for_status()

            if not validate_response_checksum(resp):
                LOGGER.error("Checksum mismatch on page %s", page)
                return {"statusCode": 500, "body": "Checksum mismatch"}

            body = resp.json()
            if body.get("status") != "ok":
                LOGGER.error("Bad status on page %s: %s", page, body)
                return {"statusCode": 500, "body": "Bad status"}

            payload = body["payload"]
            current = payload["current_page"]
            total = payload["total_pages"]
            data = payload["data"]

            LOGGER.info(
                "Page %s/%s: alerts=%s, mentions=%s, breaches=%s, "
                "subdomains=%s, exposures=%s, topcves=%s",
                current,
                total,
                len(data["alerts"]),
                len(data["mentions"]),
                len(data["breaches"]),
                len(data["subdomains"]),
                len(data["exposures"]),
                len(data["topcves"]),
            )

            # Upsert all tables in one pass
            save_cybersix_payload(data)

            if current >= total:
                break
            page += 1

        LOGGER.info("Cybersixgill sync completed successfully.")
        return {"statusCode": 200, "body": "Sync successful"}

    except Exception as e:
        LOGGER.error("Sync error: %s", e)
        return {"statusCode": 500, "body": str(e)}


if __name__ == "__main__":
    result = handler()
    LOGGER.info("Result: %s", result)
    print(result)
