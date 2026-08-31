"""Config loading for the VS Port/Service Inventory connector.

Same fail-closed shape as connectors A/D's config.py (§10i). Unlike Connector B, this one *does*
poll wholesale (§7c: full poll of the in-scope table every run, since there's no timestamp
watermark that can detect a port going stale -- see connector.py), so it needs the same
`org_acronym_allowlist`/`allow_unscoped_run` pair A/D use to guard against an accidentally
unscoped run, for the same reason (§9c). No `lookback_days` here, though -- that lever bounds a
*timestamp-filtered* first poll, and this connector's poll was never timestamp-filtered to begin
with (§7c's core gotcha: `mark_stale_latest_port_scans()` flips `current` without touching
`time_scanned`, so a time-based bound would just as silently hide already-stale rows as it would
speed up a first run).
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
            "VS_PORT_INVENTORY_DB_HOST", ["vs_port_inventory", "db_host"], self.raw
        )
        self.db_port = get_config_variable(
            "VS_PORT_INVENTORY_DB_PORT",
            ["vs_port_inventory", "db_port"],
            self.raw,
            isNumber=True,
            default=5432,
        )
        self.db_name = get_config_variable(
            "VS_PORT_INVENTORY_DB_NAME",
            ["vs_port_inventory", "db_name"],
            self.raw,
            default="cyhy_mini_data_lake_staging",
        )
        self.db_user = get_config_variable(
            "VS_PORT_INVENTORY_DB_USER",
            ["vs_port_inventory", "db_user"],
            self.raw,
            default="open_cti",
        )
        self.db_use_iam_auth = get_config_variable(
            "VS_PORT_INVENTORY_DB_USE_IAM_AUTH",
            ["vs_port_inventory", "db_use_iam_auth"],
            self.raw,
            default=True,
        )
        self.db_password = get_config_variable(
            "VS_PORT_INVENTORY_DB_PASSWORD",
            ["vs_port_inventory", "db_password"],
            self.raw,
            default="",
        )
        self.aws_region = get_config_variable(
            "VS_PORT_INVENTORY_AWS_REGION",
            ["vs_port_inventory", "aws_region"],
            self.raw,
        )

        # --- dev/test discipline (§9) ---
        self.is_local = get_config_variable(
            "IS_LOCAL", ["vs_port_inventory", "is_local"], self.raw, default=False
        )
        self.local_fixture_dir = get_config_variable(
            "VS_PORT_INVENTORY_LOCAL_FIXTURE_DIR",
            ["vs_port_inventory", "local_fixture_dir"],
            self.raw,
            default="./tests/fixtures",
        )

        org_allowlist_raw = get_config_variable(
            "VS_PORT_INVENTORY_ORG_ACRONYM_ALLOWLIST",
            ["vs_port_inventory", "org_acronym_allowlist"],
            self.raw,
            default="",
        )
        self.org_acronym_allowlist: List[str] = [
            acronym.strip()
            for acronym in (org_allowlist_raw or "").split(",")
            if acronym.strip()
        ]
        self.allow_unscoped_run = get_config_variable(
            "VS_PORT_INVENTORY_ALLOW_UNSCOPED_RUN",
            ["vs_port_inventory", "allow_unscoped_run"],
            self.raw,
            default=False,
        )
        # §7c: "full poll every run" is the whole strategy here, not a fallback path -- so this
        # cap matters more than it does for A/D's watermark-bounded polls. Row-count growth is
        # also structurally different: LatestPortScan rows never get deleted when a port goes
        # stale (only current flips to False), so the in-scope row count only ever grows over
        # time, unlike A's ticket backlog which a watermark eventually catches up past. Real
        # row counts for this table are still unconfirmed (OpenCTI-connector.md §6) -- start
        # conservative, same as A/D did before their own real numbers were known.
        self.max_rows_per_run = get_config_variable(
            "VS_PORT_INVENTORY_MAX_ROWS_PER_RUN",
            ["vs_port_inventory", "max_rows_per_run"],
            self.raw,
            isNumber=True,
            default=5000,
        )

        # --- attribution / marking (§10c) ---
        self.author_name = get_config_variable(
            "VS_PORT_INVENTORY_AUTHOR_NAME",
            ["vs_port_inventory", "author_name"],
            self.raw,
            default="CISA VulnScanning",
        )
        self.tlp_marking = get_config_variable(
            "VS_PORT_INVENTORY_TLP_MARKING",
            ["vs_port_inventory", "tlp_marking"],
            self.raw,
        )

        # §7c doesn't depend on VulnScanningSync's ticket-specific cadence the way A does, but
        # still shouldn't poll tighter than the source data actually changes. Same P1D starting
        # point as A, for the same reason -- tune once real `VulnScanningSync` cadence is known.
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
                "vs_port_inventory.tlp_marking is not set. This is a real, undecided policy "
                "question (OpenCTI-connector.md §10c) -- refusing to start rather than default "
                "to something like TLP:CLEAR for stakeholder vulnerability data. Set "
                "VS_PORT_INVENTORY_TLP_MARKING once the data-handling policy call is made."
            )
        if not self.org_acronym_allowlist and not self.allow_unscoped_run:
            raise ConfigError(
                "vs_port_inventory.org_acronym_allowlist is empty and allow_unscoped_run is not "
                "set. An empty allowlist means 'scoped to nothing', not 'all orgs' -- see "
                "OpenCTI-connector.md §9c. Set VS_PORT_INVENTORY_ORG_ACRONYM_ALLOWLIST for dev, "
                "or explicitly set VS_PORT_INVENTORY_ALLOW_UNSCOPED_RUN=true for a deliberate "
                "full-scope production run."
            )
        if not self.is_local and not self.db_host:
            raise ConfigError(
                "vs_port_inventory.db_host is not set and is_local is false -- nothing to "
                "connect to. Set VS_PORT_INVENTORY_DB_HOST, or IS_LOCAL=true to use fixtures "
                "instead."
            )
