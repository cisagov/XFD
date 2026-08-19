"""One API key per worker for keyed PE scans (Flare, Shodan, ...).

Keys come from a comma-separated SSM env var. The controller validates them,
clamps COUNT to the number of valid keys, and starts one container per key.

Usage in peScanController::

    if scan_name in KEYED_SCANS:
        for key in plan_worker_keys(scan_name, count):
            env.update(worker_key_env(scan_name, key))

To add a scan: write a validator and add an entry to KEYED_SCANS.
"""

# Standard Python Libraries
import importlib.util
import logging
import os
import time
from typing import Any, Dict, List

# Third-Party Libraries
from retry import retry

LOGGER = logging.getLogger(__name__)


class ShodanRateLimitError(Exception):
    """Shodan API rate limit hit during key validation."""


def _split_keys(raw: str) -> List[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def api_key_label(api_key: str) -> str:
    """Return a log-safe API key identifier (last four characters only)."""
    key = (api_key or "").strip()
    if not key:
        return "(unset)"
    if len(key) <= 4:
        return "****"
    return "...{}".format(key[-4:])


def _validate_flare(keys: List[str], max_valid=None) -> List[str]:
    del max_valid  # Flare validation unchanged; accepts kwarg for plan_worker_keys.
    # Third-Party Libraries
    from pe_source.flare_events.flare_helpers import validate_flare_api_key

    tenant_id = os.environ.get("FLARE_TENANT_ID", "")
    if not tenant_id:
        raise ValueError("FLARE_TENANT_ID is required to validate Flare API keys")

    valid = []
    for i, key in enumerate(keys, start=1):
        try:
            if validate_flare_api_key(key, tenant_id=tenant_id):
                valid.append(key)
                LOGGER.info(
                    "Flare API key %d/%d is valid (%s)",
                    i,
                    len(keys),
                    api_key_label(key),
                )
            else:
                LOGGER.warning(
                    "Flare API key %d/%d failed validation (%s); skipping",
                    i,
                    len(keys),
                    api_key_label(key),
                )
        except Exception as exc:
            LOGGER.warning(
                "Flare API key %d/%d raised during validation; skipping: %s",
                i,
                len(keys),
                exc,
            )
    return valid


@retry(ShodanRateLimitError, tries=4, delay=1, backoff=1)
def _check_shodan_api_key(api_key: str) -> None:
    """Validate one Shodan API key; retries on rate-limit responses."""
    # Third-Party Libraries
    import shodan

    try:
        shodan.Shodan(api_key).info()
    except Exception as exc:
        if "rate limit" in str(exc).lower():
            raise ShodanRateLimitError(str(exc)) from exc
        raise


def _validate_shodan(keys: List[str], max_valid=None) -> List[str]:
    if importlib.util.find_spec("shodan") is None:
        LOGGER.warning("shodan package not installed; skipping key validation")
        if max_valid is None:
            return list(keys)
        return list(keys)[:max_valid]

    valid: List[str] = []
    for i, key in enumerate(keys, start=1):
        if max_valid is not None and len(valid) >= max_valid:
            break
        if i > 1:
            time.sleep(1)
        try:
            _check_shodan_api_key(key)
            valid.append(key)
            LOGGER.info(
                "Shodan API key %d/%d is valid (%s)",
                i,
                len(keys),
                api_key_label(key),
            )
        except Exception as exc:
            LOGGER.warning(
                "Shodan API key %d/%d failed validation; skipping: %s",
                i,
                len(keys),
                exc,
            )
    return valid


# keys_env: SSM/env with comma-separated keys
# worker_env: singular key injected into each container
# extra_env: optional extra vars every worker for this scan needs
KEYED_SCANS: Dict[str, Dict] = {
    "asmsync": {
        "keys_env": "PE_SHODAN_API_KEYS",
        "worker_env": "PE_SHODAN_API_KEY",
        "validate": _validate_shodan,
    },
    "flare_events": {
        "keys_env": "FLARE_API_KEYS",
        "worker_env": "FLARE_API_KEY",
        "validate": _validate_flare,
        "extra_env": lambda: {"FLARE_TENANT_ID": os.environ.get("FLARE_TENANT_ID", "")},
    },
    "flare_creds": {
        "keys_env": "FLARE_API_KEYS",
        "worker_env": "FLARE_API_KEY",
        "validate": _validate_flare,
        "extra_env": lambda: {"FLARE_TENANT_ID": os.environ.get("FLARE_TENANT_ID", "")},
    },
    "flare_ident_prune": {
        "keys_env": "FLARE_API_KEYS",
        "worker_env": "FLARE_API_KEY",
        "validate": _validate_flare,
        "extra_env": lambda: {"FLARE_TENANT_ID": os.environ.get("FLARE_TENANT_ID", "")},
    },
    "flare_ident_refresh": {
        "keys_env": "FLARE_API_KEYS",
        "worker_env": "FLARE_API_KEY",
        "validate": _validate_flare,
        "extra_env": lambda: {"FLARE_TENANT_ID": os.environ.get("FLARE_TENANT_ID", "")},
    },
    "shodan": {
        "keys_env": "PE_SHODAN_API_KEYS",
        "worker_env": "PE_SHODAN_API_KEY",
        "validate": _validate_shodan,
    },
    "shodan_top_cves": {
        "keys_env": "PE_SHODAN_API_KEYS",
        "worker_env": "PE_SHODAN_API_KEY",
        "validate": _validate_shodan,
    },
}


def plan_worker_keys(scan_name: str, count: int) -> List[str]:
    """Load, validate, and clamp keys for a keyed scan. One key per worker."""
    config = KEYED_SCANS[scan_name]
    keys_env = config["keys_env"]
    raw = _split_keys(os.environ.get(keys_env, ""))
    if not raw:
        raise ValueError(
            "{} is empty; provide comma-separated API keys".format(keys_env)
        )

    LOGGER.info("Validating %d %s API key(s)", len(raw), scan_name)
    valid = config["validate"](raw, max_valid=count)
    if not valid:
        raise ValueError(
            "No valid API keys found in {}; cannot start {} workers".format(
                keys_env, scan_name
            )
        )

    if count > len(valid):
        LOGGER.warning(
            "Requested %d %s container(s) but only %d valid key(s); "
            "starting %d (one per key).",
            count,
            scan_name,
            len(valid),
            len(valid),
        )
        return valid

    if count < len(valid):
        LOGGER.warning(
            "Starting %d of %d valid %s key(s). Set COUNT/taskCount to %d "
            "to use the remaining key(s).",
            count,
            len(valid),
            scan_name,
            len(valid),
        )
        return valid[:count]

    return valid


def plan_worker_keys_for_scans(
    scan_list: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Validate and plan worker API keys for every keyed scan in the list."""
    planned: Dict[str, List[str]] = {}
    for scan in scan_list:
        scan_name = scan["scan"]
        if scan_name in KEYED_SCANS:
            planned[scan_name] = plan_worker_keys(scan_name, int(scan["count"]))
    return planned


def worker_keys_for_scan(
    scan_name: str,
    count: int,
    planned: Dict[str, List[str]] | None,
) -> List[str]:
    """Return planned keys when available, otherwise load and validate."""
    if planned is not None and scan_name in planned:
        return planned[scan_name]
    return plan_worker_keys(scan_name, count)


def worker_key_env(scan_name: str, api_key: str) -> Dict[str, str]:
    """Env vars to inject into one worker for this keyed scan."""
    config = KEYED_SCANS[scan_name]
    env = {config["worker_env"]: api_key}
    extra = config.get("extra_env")
    if extra:
        env.update(extra())
    return env
