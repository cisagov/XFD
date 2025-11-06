"""Sync CVE/SSVC from Redshift (AE feed) into MDL."""
# Standard Python Libraries
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

# Third-Party Libraries
import django
from django.db import transaction
from xfd_mini_dl.models import Cve as CveModel
from xfd_mini_dl.models import CveSsvc

from ..helpers.redshift_helpers import (
    extract_cvss,
    extract_references,
    extract_ssvc,
    extract_weaknesses_from_problem_types,
    newdata_set,
    parse_iso8601,
    pick_english_description,
)
from .utils.query_redshift import fetch_from_redshift_with_params

# Setup logging
LOGGER = logging.getLogger(__name__)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()


def handler(event):
    """Sync CVE/SSVC from Redshift (AE feed) into MDL."""
    try:
        main()
        return {
            "statusCode": 200,
            "body": "Redshift scan update completed successfully.",
        }
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}


def parse_json(value):
    """Parse json strings into json objects."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value  # fallback to raw if invalid JSON
    return value


def parse_redshift_row(row: dict[str, Any]) -> dict[str, Any]:
    """Parse a Redshift row (dict) into a structured dict for CveModel."""
    return {
        "cve_name": row.get("cve_id"),
        "assigner_short_name": row.get("assigner"),
        "cna_title": row.get("title"),
        "descriptions_json": row.get("descriptions"),
        "affected_json": row.get("affected"),
        "metrics_json": row.get("metrics"),
        "problem_types_json": row.get("problem_types"),
        "references_json": row.get("references"),
        "source_json": row.get("source"),
        "adp_json": row.get("adp"),
        "published_at": row.get("published_at"),
        "modified_at": row.get("modified_at"),
        "state": row.get("state"),
        "date_reserved": row.get("date_reserved"),
        "assigner_org_id": row.get("assigner_org_id"),
        "cna_provider_org_id": row.get("cna_provider_org_id"),
        "cna_provider_short_name": row.get("cna_provider_short_name"),
        "cna_provider_date_updated": row.get("cna_provider_date_updated"),
    }


def create_or_update_cve(parsed: dict) -> CveModel:
    """Create or minimally patch a CveModel record (supports CVSS v3 + v4)."""
    weaknesses_list = extract_weaknesses_from_problem_types(
        parse_json(parsed["problem_types_json"])
    )

    description_text = pick_english_description(parse_json(parsed["descriptions_json"]))
    reference_urls_list = extract_references(parse_json(parsed["references_json"]))

    # NEW: dict result with both versions possible
    cvss_results: dict[str, dict[str, Optional[Any]]] = extract_cvss(
        parse_json(parsed["metrics_json"])
    )
    v3 = cvss_results.get("v3", {}) or {}
    v4 = cvss_results.get("v4", {}) or {}

    defaults = {
        "description": description_text,
        "title": parsed["cna_title"],
        "assigner": parsed["assigner_short_name"],
        "source_attribution": "AE/Redshift",
        "published_at": parsed["published_at"],
        "modified_at": parsed["modified_at"],
        "reference_urls": reference_urls_list or None,
        "cna_source_json": parsed["source_json"]
        if isinstance(parsed["source_json"], (dict, list))
        else None,
        "cna_affected_json": parsed["affected_json"]
        if isinstance(parsed["affected_json"], (dict, list))
        else None,
        "cna_problem_types_json": parsed["problem_types_json"] or None,
        "weaknesses": weaknesses_list or None,
        # Store both CVSS versions if present
        "cvss_v3_version": v3.get("version"),
        "cvss_v3_vector_string": v3.get("vector"),
        "cvss_v3_base_score": v3.get("base_score"),
        "cvss_v3_base_severity": v3.get("base_severity"),
        "cvss_v4_version": v4.get("version"),
        "cvss_v4_vector_string": v4.get("vector"),
        "cvss_v4_base_score": v4.get("base_score"),
        "cvss_v4_base_severity": v4.get("base_severity"),
    }

    cve_object, _ = CveModel.objects.get_or_create(
        name=parsed["cve_name"], defaults=defaults
    )

    # Patch minimal non-CVSS fields only if currently empty
    patch_minimal_fields(
        cve_object, parsed, description_text, reference_urls_list, weaknesses_list
    )

    # NEW: pass the dict so both v3 and v4 can be patched independently
    patch_cvss(cve_object, cvss_results)

    return cve_object


def patch_minimal_fields(
    cve_object, parsed, description_text, reference_urls_list, weaknesses_list
):
    """Patch JSON and text fields if empty."""
    updated_fields = []
    field_map = {
        "title": parsed["cna_title"],
        "assigner": parsed["assigner_short_name"],
        "description": description_text,
        "reference_urls": reference_urls_list,
        "published_at": parsed["published_at"],
        "modified_at": parsed["modified_at"],
        "cna_source_json": parsed["source_json"],
        "cna_affected_json": parsed["affected_json"],
        "cna_problem_types_json": parsed["problem_types_json"],
        "weaknesses": weaknesses_list,
    }
    for field, value in field_map.items():
        if value and not getattr(cve_object, field):
            setattr(cve_object, field, value)
            updated_fields.append(field)
    if updated_fields:
        cve_object.save(update_fields=updated_fields)


def patch_cvss(cve_object, cvss_results: dict[str, dict[str, Optional[Any]]]) -> None:
    """
    Patch CVSS v3 and v4 fields with newer data if available.

    Expects cvss_results in the form returned by extract_cvss().
    """
    fields_to_update: list[str] = []

    mapping = {
        "v3": [
            ("cvss_v3_version", cvss_results["v3"].get("version")),
            ("cvss_v3_vector_string", cvss_results["v3"].get("vector")),
            ("cvss_v3_base_score", cvss_results["v3"].get("base_score")),
            ("cvss_v3_base_severity", cvss_results["v3"].get("base_severity")),
        ],
        "v4": [
            ("cvss_v4_version", cvss_results["v4"].get("version")),
            ("cvss_v4_vector_string", cvss_results["v4"].get("vector")),
            ("cvss_v4_base_score", cvss_results["v4"].get("base_score")),
            ("cvss_v4_base_severity", cvss_results["v4"].get("base_severity")),
        ],
    }

    for version_key, field_mappings in mapping.items():
        for field, value in field_mappings:
            if newdata_set(cve_object, field, value):
                fields_to_update.append(field)

    if fields_to_update:
        cve_object.save(update_fields=fields_to_update)


def upsert_ssvc(cve_object, adp_json):
    """Upsert SSVC data into CveSsvc model."""
    ssvc = extract_ssvc(parse_json(adp_json))
    exploitation = (ssvc.get("exploitation") or "").lower() or None
    automatable = (ssvc.get("automatable") or "").lower() or None
    technical_impact = (ssvc.get("technical_impact") or "").lower() or None

    CveSsvc.objects.update_or_create(
        cve=cve_object,
        defaults={
            "exploitation": exploitation,
            "automatable": automatable,
            "technical_impact": technical_impact,
            "adp_provider": ssvc.get("adp_provider"),
            "adp_title": ssvc.get("adp_title"),
            "ssvc_version": ssvc.get("ssvc_version"),
            "ssvc_timestamp": parse_iso8601(ssvc.get("ssvc_timestamp")),
            "adp_date_updated": parse_iso8601(ssvc.get("adp_date_updated")),
        },
    )


def upsert_cve_from_redshift_row(row: Dict[str, Any]) -> None:
    """Parse a Redshift result row (dict), upsert the CVE, then upsert SSVC."""
    parsed = parse_redshift_row(
        parse_json(row)
    )  # parse_redshift_row should accept a dict now
    if not parsed.get("cve_name"):
        return
    with transaction.atomic():
        cve_object = create_or_update_cve(parsed)
        upsert_ssvc(cve_object, parsed.get("adp_json"))


def build_redshift_sql() -> str:
    """Build the Redshift SQL query for CVE data with keyset pagination."""
    return """
           SELECT
               datatype,
               dataversion,
               cvemetadata_cve_id                              AS cve_id,
               cvemetadata_assigner_org_id                     AS assigner_org_id,
               cvemetadata_state                               AS state,
               cvemetadata_assigner_short_name                 AS assigner,
               cvemetadata_date_reserved                       AS date_reserved,
               cvemetadata_date_published                      AS published_at,
               cvemetadata_date_updated                        AS modified_at,
               containers_cna_title                            AS title,
               containers_cna_provider_metadata_org_id         AS cna_provider_org_id,
               containers_cna_provider_metadata_short_name     AS cna_provider_short_name,
               containers_cna_provider_metadata_date_updated   AS cna_provider_date_updated,
               containers_cna_descriptions                     AS descriptions,
               containers_cna_affected                         AS affected,
               containers_cna_metrics                          AS metrics,
               containers_cna_problem_types                    AS problem_types,
               containers_cna_references                       AS references,
               containers_cna_source                           AS source,
               containers_adp                                  AS adp,
               last_load_timestamp
           FROM cve.cve_org_data
           WHERE containers_adp IS NOT NULL
             AND cvemetadata_date_updated >= CURRENT_DATE - INTERVAL '1 year'
             AND (%s = '' OR cvemetadata_cve_id > %s)   -- keyset pagination only
           ORDER BY cvemetadata_cve_id;
           """


def sync_cve_from_redshift(max_batches: int = 100) -> int:
    """
    Fetch CVE rows from Redshift (parameterized, keyset-paginated), then upsert into local models.

    Returns total rows processed.
    """
    sql = build_redshift_sql()
    total_processed = 0
    last_key = ""
    batches = 0

    while True:
        params: Tuple[Any, Any] = (last_key, last_key)  # keyset pagination guard
        LOGGER.debug("Fetching Redshift rows with last_key=%r", last_key)
        rows: List[Dict[str, Any]] = fetch_from_redshift_with_params(sql, params)

        if not rows:
            LOGGER.info("No more rows returned from Redshift; stopping.")
            break

        LOGGER.info("Fetched %d rows from Redshift (batch %d).", len(rows), batches + 1)

        for row in rows:
            cve_id = row.get("cve_id")
            try:
                upsert_cve_from_redshift_row(row)  # pass dict directly
                total_processed += 1
                last_key = str(cve_id or last_key)
                LOGGER.debug("Upserted CVE %s; last_key now %r", cve_id, last_key)
            except Exception as e:
                LOGGER.exception("Failed to upsert CVE %r: %s", cve_id, e)

        batches += 1
        if batches >= max_batches:
            LOGGER.warning(
                "Stopping after %s batches to avoid long runtime.", max_batches
            )
            break

    LOGGER.info(
        "Redshift CVE sync complete: %s rows processed (last_key=%r).",
        total_processed,
        last_key,
    )
    return total_processed


def main() -> int:
    """Task entrypoint used by handler() and CLI."""
    # You can run multiple prefixes if desired; keeping it simple:
    return sync_cve_from_redshift(max_batches=100)


if __name__ == "__main__":
    sys.exit(main())
