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
import logging
import os
from typing import Dict, List

LOGGER = logging.getLogger(__name__)


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


def _validate_flare(keys: List[str]) -> List[str]:
    # Third-Party Libraries
    from pe_source.flare.flare_helpers import validate_flare_api_key

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


def _validate_shodan(keys: List[str]) -> List[str]:
    try:
        # Third-Party Libraries
        import shodan
    except ImportError:
        LOGGER.warning("shodan package not installed; skipping key validation")
        return list(keys)

    valid = []
    for i, key in enumerate(keys, start=1):
        try:
            shodan.Shodan(key).info()
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
    "flare_events": {
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
    "asmSync": {
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
    valid = config["validate"](raw)
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


def worker_key_env(scan_name: str, api_key: str) -> Dict[str, str]:
    """Env vars to inject into one worker for this keyed scan."""
    config = KEYED_SCANS[scan_name]
    env = {config["worker_env"]: api_key}
    extra = config.get("extra_env")
    if extra:
        env.update(extra())
    return env
