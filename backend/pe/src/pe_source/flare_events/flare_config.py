"""Flare API credentials from environment variables (replaces ATC database.ini)."""

# Standard Python Libraries
import os


def get_params(section=None):
    """Return flare config items in the same shape as ATC configparser get_params.

    Workers receive a single key via FLARE_API_KEY (assigned by peScanController).
    The controller reads the comma-separated FLARE_API_KEYS list to validate and
    distribute keys across containers.
    """
    del section
    tenant_id = os.environ.get("FLARE_TENANT_ID", "")
    params = [("tenant_id", tenant_id)]
    # Prefer the single key assigned to this worker container.
    api_key = os.environ.get("FLARE_API_KEY", "").strip()
    if api_key:
        params.append(("api_key", api_key))
    return params


def parse_flare_api_keys(raw: str | None = None) -> list[str]:
    """Split a comma-separated FLARE_API_KEYS string into non-empty keys."""
    if raw is None:
        raw = os.environ.get("FLARE_API_KEYS", "")
    return [part.strip() for part in (raw or "").split(",") if part.strip()]
