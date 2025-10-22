"""Utility function for fetching and normalizing allowed admin email domains."""

# Standard Python Libraries
import json
import logging
import os

LOGGER = logging.getLogger(__name__)


def get_allowed_admin_domains() -> list[str]:
    """Fetch and normalize ALLOWED_ADMIN_EMAIL_DOMAINS env var into a list of strings."""
    raw_value = os.getenv("ALLOWED_ADMIN_EMAIL_DOMAINS", "")

    # If already a list (e.g., manually injected in local dev)
    if isinstance(raw_value, list):
        return [str(x).strip() for x in raw_value if x]

    # If empty or None, return empty list
    if not raw_value:
        return []

    # Try parsing as JSON (handles '["a","b"]' style)
    if raw_value.strip().startswith("["):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if x]
            LOGGER.warning(
                "ALLOWED_ADMIN_EMAIL_DOMAINS JSON parsed to non-list, ignoring."
            )
        except json.JSONDecodeError:
            LOGGER.warning(
                "ALLOWED_ADMIN_EMAIL_DOMAINS not valid JSON, falling back to CSV parsing."
            )

    # Fallback: treat as comma-delimited string
    domains = [d.strip() for d in raw_value.split(",") if d.strip()]
    return domains
