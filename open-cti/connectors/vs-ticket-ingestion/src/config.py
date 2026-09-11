"""Config loading for the VS Ticket Ingestion connector.

Structurally identical to connector D's config.py (OpenCTI-connector.md §10i: apply the same
discipline from the start, don't rediscover it) -- precedence is env var > config.yml > default
via pycti's own get_config_variable(), and the same two things fail closed rather than silently
defaulting to something wrong:
  - tlp_marking: still the same undecided policy question (§10c) -- shared across all four
    connectors, not re-litigated per connector.
  - org_acronym_allowlist: empty means "scoped to nothing," not "all orgs" (§9c).
"""

# Standard Python Libraries
import os
from typing import Dict, List, Optional

# Third-Party Libraries
from pycti import get_config_variable
import yaml


class ConfigError(RuntimeError):
    """Raised when required configuration is missing -- fail closed, not silent default."""


def load_yaml_config() -> Dict:
    """Load config.yml next to this connector if present; docker-compose drives env vars only."""
    here = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(here, "..", "config.yml")
    if os.path.isfile(config_file_path):
        with open(config_file_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


class Config:
    """Typed view over this connector's configuration."""

    def __init__(self, raw: Optional[Dict] = None):
        """Load config from `raw` if given (tests), else config.yml/env vars, then validate."""
        self.raw: Dict = raw if raw is not None else load_yaml_config()

        # --- mini_data_lake connectivity (OpenCTI-connector.md §2) ---
        self.db_host = get_config_variable(
            "VS_TICKET_INGESTION_DB_HOST", ["vs_ticket_ingestion", "db_host"], self.raw
        )
        self.db_port = get_config_variable(
            "VS_TICKET_INGESTION_DB_PORT",
            ["vs_ticket_ingestion", "db_port"],
            self.raw,
            isNumber=True,
            default=5432,
        )
        # cyhy_mini_data_lake_staging is the confirmed real staging DB name (verified 2026-08-27
        # via connector D against the live box); "mini_data_lake" stays the architectural name
        # for this data store throughout comments/docs.
        self.db_name = get_config_variable(
            "VS_TICKET_INGESTION_DB_NAME",
            ["vs_ticket_ingestion", "db_name"],
            self.raw,
            default="cyhy_mini_data_lake_staging",
        )
        self.db_user = get_config_variable(
            "VS_TICKET_INGESTION_DB_USER",
            ["vs_ticket_ingestion", "db_user"],
            self.raw,
            default="open_cti",
        )
        self.db_use_iam_auth = get_config_variable(
            "VS_TICKET_INGESTION_DB_USE_IAM_AUTH",
            ["vs_ticket_ingestion", "db_use_iam_auth"],
            self.raw,
            default=True,
        )
        self.db_password = get_config_variable(
            "VS_TICKET_INGESTION_DB_PASSWORD",
            ["vs_ticket_ingestion", "db_password"],
            self.raw,
            default="",
        )
        self.aws_region = get_config_variable(
            "VS_TICKET_INGESTION_AWS_REGION",
            ["vs_ticket_ingestion", "aws_region"],
            self.raw,
        )

        # --- dev/test discipline (§9) ---
        self.is_local = get_config_variable(
            "IS_LOCAL", ["vs_ticket_ingestion", "is_local"], self.raw, default=False
        )
        self.local_fixture_dir = get_config_variable(
            "VS_TICKET_INGESTION_LOCAL_FIXTURE_DIR",
            ["vs_ticket_ingestion", "local_fixture_dir"],
            self.raw,
            default="./tests/fixtures",
        )

        org_allowlist_raw = get_config_variable(
            "VS_TICKET_INGESTION_ORG_ACRONYM_ALLOWLIST",
            ["vs_ticket_ingestion", "org_acronym_allowlist"],
            self.raw,
            default="",
        )
        self.org_acronym_allowlist: List[str] = [
            acronym.strip()
            for acronym in (org_allowlist_raw or "").split(",")
            if acronym.strip()
        ]
        self.allow_unscoped_run = get_config_variable(
            "VS_TICKET_INGESTION_ALLOW_UNSCOPED_RUN",
            ["vs_ticket_ingestion", "allow_unscoped_run"],
            self.raw,
            default=False,
        )
        # Tickets outnumber orgs/CIDRs by a lot (§7a) -- start with the same default row cap as
        # connector D for the first scoped test runs, not a bigger number just because there's
        # more data; tune upward deliberately once real per-run timings are observed (§9c/§9d).
        self.max_rows_per_run = get_config_variable(
            "VS_TICKET_INGESTION_MAX_ROWS_PER_RUN",
            ["vs_ticket_ingestion", "max_rows_per_run"],
            self.raw,
            isNumber=True,
            default=5000,
        )
        # §9c's "Lookback override" scoping lever, planned but not built until now: bounds the
        # *first* poll against a fresh/reset connector state to the last N days, instead of every
        # ticket ever recorded for the scoped orgs. Read manually (not isNumber=True) because
        # get_config_variable() calls int(result) before checking for an empty string -- verified
        # directly against the installed pycti source -- so an unset-but-present env var (the
        # `${VAR:-}` pattern docker-compose.yml already uses for every other optional lever here)
        # would crash with "invalid literal for int()" instead of falling back to the default.
        # None (the default) means "no bound, pull the whole history" -- unchanged behavior,
        # matching the module docstring's fail-closed philosophy: don't silently start skipping
        # data just because a dev convenience knob exists. See connector.py for where this is
        # actually applied (only when no watermark exists yet, never overriding one that does --
        # bounding an in-progress incremental poll would create a permanent gap, not just delay).
        lookback_days_raw = get_config_variable(
            "VS_TICKET_INGESTION_LOOKBACK_DAYS",
            ["vs_ticket_ingestion", "lookback_days"],
            self.raw,
            default="",
        )
        self.lookback_days: Optional[int] = (
            int(lookback_days_raw) if lookback_days_raw not in (None, "") else None
        )

        # --- attribution / marking (§10c) ---
        # Same author name as connector D on purpose -- all VS-sourced content across all four
        # connectors should trace back to one consistent system Identity, not a per-connector one.
        self.author_name = get_config_variable(
            "VS_TICKET_INGESTION_AUTHOR_NAME",
            ["vs_ticket_ingestion", "author_name"],
            self.raw,
            default="CISA VulnScanning",
        )
        self.tlp_marking = get_config_variable(
            "VS_TICKET_INGESTION_TLP_MARKING",
            ["vs_ticket_ingestion", "tlp_marking"],
            self.raw,
        )

        # §7a -- polls on a schedule, should not be tighter than VulnScanningSync's own cadence
        # (§5, still unresolved). P1D matches connector-cisa-known-exploited-vulnerabilities'
        # current setting, used as the starting point per §7a.
        self.duration_period = get_config_variable(
            "CONNECTOR_DURATION_PERIOD",
            ["connector", "duration_period"],
            self.raw,
            default="P1D",
        )

        self._validate()

    def _validate(self) -> None:
        """Fail closed on the two decisions this doc can't make silently. See module docstring."""
        if not self.tlp_marking:
            raise ConfigError(
                "vs_ticket_ingestion.tlp_marking is not set. This is a real, undecided policy "
                "question (OpenCTI-connector.md §10c) -- refusing to start rather than default "
                "to something like TLP:CLEAR for stakeholder vulnerability data. Set "
                "VS_TICKET_INGESTION_TLP_MARKING once the data-handling policy call is made."
            )
        if not self.org_acronym_allowlist and not self.allow_unscoped_run:
            raise ConfigError(
                "vs_ticket_ingestion.org_acronym_allowlist is empty and allow_unscoped_run is "
                "not set. An empty allowlist means 'scoped to nothing', not 'all orgs' -- see "
                "OpenCTI-connector.md §9c. Set VS_TICKET_INGESTION_ORG_ACRONYM_ALLOWLIST for dev, "
                "or explicitly set VS_TICKET_INGESTION_ALLOW_UNSCOPED_RUN=true for a deliberate "
                "full-scope production run."
            )
        if not self.is_local and not self.db_host:
            raise ConfigError(
                "vs_ticket_ingestion.db_host is not set and is_local is false -- nothing to "
                "connect to. Set VS_TICKET_INGESTION_DB_HOST, or IS_LOCAL=true to use fixtures "
                "instead."
            )
