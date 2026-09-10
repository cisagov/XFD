"""Sync CVE/SSVC data from Databricks (cyhy_silver) into MDL."""
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

from ..helpers.databricks_helpers import (
    extract_cvss,
    extract_references,
    extract_weaknesses_from_problem_types,
    newdata_set,
    pick_english_description,
)
from .utils.query_databricks import fetch_from_databricks_with_params

# Setup logging
LOGGER = logging.getLogger(__name__)

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# MODIFIED: new constant. The old Redshift query had no LIMIT (it relied on
# the AE feed being small enough to return in one shot), but Databricks'
# cyhy_cve_data table is expected to be much larger, so pagination here is a
# real LIMIT/OFFSET-by-keyset loop rather than the effectively-single-shot
# loop the Redshift version had.
_PAGE_SIZE = 5000


def handler(event):
    """Sync CVE/SSVC data from Databricks into MDL."""
    try:
        main()
        return {
            "statusCode": 200,
            "body": "Databricks scan update completed successfully.",
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

def parse_databricks_row(row: dict[str, Any]) -> dict[str, Any]:
    """Parse a Databricks row (dict) into a structured dict for CveModel."""
    cna = parse_json(row.get("cna"))
    if not isinstance(cna, dict):
        cna = {}

    weakness = parse_json(row.get("weaknesses"))
    if not isinstance(weakness, list):
        weakness = None

    affected = parse_json(row.get("affected_item"))
    if not isinstance(affected, (dict, list)):
        affected = None

    return {
        "cve_name": row.get("cve_id"),
        "assigner_short_name": None,
        "cna_title": cna.get("title"),
        "descriptions_json": cna.get("descriptions"),
        "affected_json": affected,
        "metrics_json": cna.get("metrics"),
        "problem_types_json": cna.get("problemTypes"),
        "references_json": extract_references(cna.get("references")),
        "source_json": cna.get("source"),
        "adp_json": None,
        "published_at": cna.get("datePublic"),
        "modified_at": None,
        "state": None,
        "date_reserved": None,
        "assigner_org_id": None,
        "cna_provider_org_id": None,
        "cna_provider_short_name": None,
        "cna_provider_date_updated": None,
        "weakness": weakness,
        "exploitation": row.get("exploitation"),
        "automatable": row.get("automatable"),
        "technical_impact": row.get("technical_impact"),
    }


def create_or_update_cve(parsed: dict) -> CveModel:
    """Create or minimally patch a CveModel record (supports CVSS v3 + v4)."""
    # MODIFIED: was extract_weaknesses_from_problem_types(parse_json(parsed["problem_types_json"]))
    # on Redshift - cyhy_cve_data already provides a pre-computed top-level
    # `weaknesses` array (parsed["weakness"] - see parse_databricks_row());
    # only fall back to deriving it from cna.problemTypes if that's empty.
    weaknesses_list = parsed.get("weakness") or extract_weaknesses_from_problem_types(
        parsed["problem_types_json"]
    )

    description_text = pick_english_description(parsed["descriptions_json"])
    # MODIFIED: no longer calls extract_references() here - parsed["references_json"]
    # is already a pre-extracted list of URL strings, computed once in
    # parse_databricks_row() (Redshift's version called extract_references()
    # at this point instead, since references_json there was still the raw list).
    reference_urls_list = parsed["references_json"]

    # dict result with both versions possible
    # MODIFIED: no longer wrapped in parse_json() - parsed["metrics_json"] is
    # already a native list (decoded once, up front, in parse_databricks_row()
    # via the `cna` struct), not a raw JSON string like on Redshift.
    cvss_results: dict[str, dict[str, Optional[Any]]] = extract_cvss(
        parsed["metrics_json"]
    )
    v3 = cvss_results.get("v3", {}) or {}
    v4 = cvss_results.get("v4", {}) or {}

    defaults = {
        "description": description_text,
        "title": parsed["cna_title"],
        "assigner": parsed["assigner_short_name"],
        "source_attribution": "Databricks",
        "published_at": parsed["published_at"],
        "modified_at": parsed["modified_at"],
        "reference_urls": reference_urls_list or None,
        "cna_source_json": parsed["source_json"]
        if isinstance(parsed["source_json"], (dict, list))
        else None,
        "cna_affected_json": parsed["affected_json"],
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

    # pass the dict so both v3 and v4 can be patched independently
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


def upsert_ssvc(cve_object, parsed: dict) -> None:
    """Upsert SSVC decision points into the CveSsvc model."""
    exploitation = (parsed.get("exploitation") or "").lower() or None
    automatable = (parsed.get("automatable") or "").lower() or None
    technical_impact = (parsed.get("technical_impact") or "").lower() or None

    CveSsvc.objects.update_or_create(
        cve=cve_object,
        defaults={
            "exploitation": exploitation,
            "automatable": automatable,
            "technical_impact": technical_impact,
            "adp_provider": None,
            "adp_title": None,
            "ssvc_version": None,
            "ssvc_timestamp": None,
            "adp_date_updated": None,
        },
    )


def upsert_cve_from_databricks_row(row: Dict[str, Any]) -> None:
    """Parse a Databricks result row (dict), upsert the CVE, then upsert SSVC."""
    parsed = parse_databricks_row(row)
    if not parsed.get("cve_name"):
        return
    with transaction.atomic():
        cve_object = create_or_update_cve(parsed)
        upsert_ssvc(cve_object, parsed)


def build_databricks_sql() -> str:
    """Build the Databricks SQL query for CVE data with keyset pagination.

    Uses Databricks named parameter markers (:p0, :p1, :p2) per
    query_databricks()'s calling convention - params are bound positionally
    by list index, so a value referenced twice in the WHERE clause (the
    keyset guard) is passed twice, matching the convention already used by
    the keyset helpers in query_databricks.py.

    The WHERE clause stands in for the old Redshift query's
    `containers_adp IS NOT NULL` filter - "only rows that have been
    assessed by the ADP/SSVC feed" - now just the flat `exploitation`
    column being populated, since exploitation/automatable are sourced from
    the flat row columns only (see parse_databricks_row()/upsert_ssvc()).
    The old query's one-year modified-date filter has no equivalent column
    on this table and is dropped; add one back here if cyhy_cve_data gains a
    comparable column.
    """

    return """
           SELECT
               cve_id,
               affected_item,
               cna,
               exploitation,
               automatable,
               technical_impact,
               weaknesses
           FROM cyber_insights_prd.cyhy_silver.cyhy_cve_data
           WHERE exploitation IS NOT NULL
             AND (:p0 = '' OR cve_id > :p1)
           ORDER BY cve_id
           LIMIT :p2
           """  # nosec B608


def sync_cve_from_databricks(
    max_batches: int = 100, page_size: int = _PAGE_SIZE
) -> int:
    """
    Fetch CVE rows from Databricks (parameterized, keyset-paginated), then upsert into local models.

    Returns total rows processed.
    """
    sql = build_databricks_sql()
    total_processed = 0
    last_key = ""
    batches = 0

    while True:
        # MODIFIED: was `params: Tuple[Any, Any] = (last_key, last_key)` -
        # now a 3-tuple, adding page_size for the new LIMIT :p2 marker.
        params: Tuple[Any, Any, Any] = (last_key, last_key, page_size)
        LOGGER.debug("Fetching Databricks rows with last_key=%r", last_key)
        rows: List[Dict[str, Any]] = fetch_from_databricks_with_params(sql, params)

        if not rows:
            LOGGER.info("No more rows returned from Databricks; stopping.")
            break

        LOGGER.info(
            "Fetched %d rows from Databricks (batch %d).", len(rows), batches + 1
        )

        for row in rows:
            cve_id = row.get("cve_id")
            try:
                # MODIFIED: was upsert_cve_from_redshift_row(row)
                upsert_cve_from_databricks_row(row)
                total_processed += 1
                last_key = str(cve_id or last_key)
                LOGGER.debug("Upserted CVE %s; last_key now %r", cve_id, last_key)
            except Exception as e:
                LOGGER.exception("Failed to upsert CVE %r: %s", cve_id, e)

        batches += 1

        if len(rows) < page_size:
            LOGGER.info(
                "Fetched a partial page (%d < %d); no more rows remain.",
                len(rows),
                page_size,
            )
            break
        if batches >= max_batches:
            LOGGER.warning(
                "Stopping after %s batches to avoid long runtime.", max_batches
            )
            break

    LOGGER.info(
        "Databricks CVE sync complete: %s rows processed (last_key=%r).",
        total_processed,
        last_key,
    )
    return total_processed


def main() -> int:
    """Task entrypoint used by handler() and CLI."""
    return sync_cve_from_databricks(max_batches=100)


if __name__ == "__main__":
    sys.exit(main())