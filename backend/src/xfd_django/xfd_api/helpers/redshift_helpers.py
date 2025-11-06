"""Helper functions for parsing and normalizing CVE, CVSS, and SSVC data from.

Redshift or CVE JSON feeds.
"""

# Standard Python Libraries
from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)


def safe_json_loads(raw_text: Optional[str]) -> Optional[Any]:
    """Parse JSON if present; sanitize obvious malformed backslashes first."""
    if not raw_text:
        return None
    cleaned = raw_text.replace("\\https://", "https://").replace("\\http://", "http://")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def pick_english_description(
    descriptions: Optional[List[Dict[str, Any]]]
) -> Optional[str]:
    """Choose first English description.value, fallback to first value."""
    if not descriptions:
        return None
    for description_item in descriptions:
        if str(description_item.get("lang", "")).lower().startswith("en"):
            value = description_item.get("value")
            if value:
                return str(value)
    # fallback
    value = (
        descriptions[0].get("value")
        if descriptions and isinstance(descriptions[0], dict)
        else None
    )
    return str(value) if value else None


def extract_references(references: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Return list of reference URLs as strings."""
    urls: List[str] = []
    if not references:
        return urls
    for reference in references:
        url_value = reference.get("url")
        if url_value:
            urls.append(str(url_value))
    return urls


def extract_cvss(
    metrics_list: list[dict[str, Any]]
) -> dict[str, dict[str, Optional[Any]]]:
    """
    Extract both CVSS v3 and v4 details from CNA metrics.

    Returns:
        {
          "v3": {"version": str|None, "vector": str|None, "base_score": float|str|None, "base_severity": str|None},
          "v4": {"version": str|None, "vector": str|None, "base_score": float|str|None, "base_severity": str|None},
        }
    """
    result: dict[str, dict[str, Optional[Any]]] = {
        "v3": {
            "version": None,
            "vector": None,
            "base_score": None,
            "base_severity": None,
        },
        "v4": {
            "version": None,
            "vector": None,
            "base_score": None,
            "base_severity": None,
        },
    }

    if not isinstance(metrics_list, list):
        return result

    for metric in metrics_list:
        if not isinstance(metric, dict):
            continue

        v3_data = metric.get("cvssV3_1") or metric.get("cvssV3_0")
        if isinstance(v3_data, dict):
            result["v3"] = {
                "version": v3_data.get("version"),
                "vector": v3_data.get("vectorString"),
                "base_score": v3_data.get("baseScore"),
                "base_severity": v3_data.get("baseSeverity"),
            }

        v4_data = metric.get("cvssV4_0")
        if isinstance(v4_data, dict):
            result["v4"] = {
                "version": v4_data.get("version"),
                "vector": v4_data.get("vectorString"),
                "base_score": v4_data.get("baseScore"),
                "base_severity": v4_data.get("baseSeverity"),
            }

    return result


def extract_ssvc(adp_items: Optional[List[Dict[str, Any]]]) -> Dict[str, Optional[str]]:
    """
    From containers_adp[*].metrics[*].other.content.options (array of single-key dicts),.

    pick Exploitation / Automatable / Technical Impact.
    Also pull provider shortName, title, content.version, content.timestamp, providerMetadata.dateUpdated.
    If multiple ADP items exist, caller should already have filtered to the latest per CVE.
    """
    result: Dict[str, Optional[str]] = {
        "exploitation": None,
        "automatable": None,
        "technical_impact": None,
        "adp_provider": None,
        "adp_title": None,
        "ssvc_version": None,
        "ssvc_timestamp": None,
        "adp_date_updated": None,
    }
    if not adp_items:
        LOGGER.warning("No adp_items found. Returning empty SSVC response.")
        return result

    for adp_item in adp_items:
        metrics_list = adp_item.get("metrics") or []
        for metric_item in metrics_list:
            other = metric_item.get("other") or {}
            if str(other.get("type") or "").lower() != "ssvc":
                continue

            # Found SSVC block — extract
            content = other.get("content") or {}
            result["ssvc_version"] = str(content.get("version") or "")
            result["ssvc_timestamp"] = str(content.get("timestamp") or "")
            options_list = content.get("options") or []
            for option_item in options_list:
                # option_item is like {"Exploitation": "none"}
                for option_key, option_value in option_item.items():
                    key_normalized = str(option_key).strip().lower().replace(" ", "_")
                    if key_normalized == "exploitation":
                        result["exploitation"] = str(option_value)
                    elif key_normalized == "automatable":
                        result["automatable"] = str(option_value)
                    elif key_normalized == "technical_impact":
                        result["technical_impact"] = str(option_value)

            # Fill in metadata from this same ADP item
            result["adp_provider"] = str(
                adp_item.get("providerMetadata", {}).get("shortName") or ""
            )
            result["adp_title"] = str(adp_item.get("title") or "")
            result["adp_date_updated"] = str(
                adp_item.get("providerMetadata", {}).get("dateUpdated") or ""
            )
            LOGGER.info("SSVC data identified and returned.")
            return result  # stop once we found the right SSVC block

    # No SSVC found at all
    return result


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 date string, handling 'Z' suffix as UTC."""
    if not value:
        return None
    # no regex; rely on fromisoformat tolerant variant where possible
    try:
        # Handle 'Z' suffix
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def newdata_set(cve_object, field_name: str, value):
    """Set a field on the cve_object if the value is not None."""
    if value is not None:
        setattr(cve_object, field_name, value)
        return True
    return False


def extract_weaknesses_from_problem_types(problem_types_json) -> list[str]:
    """
    From containers_cna_problem_types (list of objects), gather CWE IDs (or descriptions).

    into a flat list of strings suitable for Cve.weaknesses.
    Structure usually looks like:
      [{"descriptions":[{"cweId":"CWE-79","description":"...","lang":"en","type":"CWE"}]}, ...]
    """
    out: list[str] = []
    if not isinstance(problem_types_json, list):
        return out

    for entry in problem_types_json:
        descs = entry.get("descriptions") or []
        for d in descs:
            cwe = d.get("cweId")
            if cwe:
                out.append(str(cwe))
            else:
                # fallback to english description if no cweId
                if str(d.get("lang", "")).lower().startswith("en") and d.get(
                    "description"
                ):
                    out.append(str(d["description"]))
    return list(dict.fromkeys(out))
