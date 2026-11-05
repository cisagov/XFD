"""Config loading for the VS VulnScan Enrichment connector.

Same fail-closed shape as connectors A/D's config.py -- precedence is env var > config.yml >
default via pycti's own get_config_variable() (§10i: apply the same discipline, don't reinvent
it per connector). Two things this module still fails closed on:
  - tlp_marking: the same shared, still-undecided policy question (§10c) -- one call across all
    four connectors, not re-litigated per connector.

What's deliberately *not* here, unlike A/D: an org_acronym_allowlist / allow_unscoped_run pair.
This connector never polls wholesale (§7b) -- it's INTERNAL_ENRICHMENT, triggered per-entity by
an analyst (or, if CONNECTOR_AUTO is ever flipped on, by the platform) via `helper.listen()`, not
`schedule_iso()`. There's no "accidentally unscoped run" failure mode to guard against here the
way there is for A/C's wholesale polls -- each invocation is already scoped to exactly one
triggered entity by construction.
"""

# Standard Python Libraries
import os
from typing import Dict, Optional

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
            "VS_VULNSCAN_ENRICHMENT_DB_HOST",
            ["vs_vulnscan_enrichment", "db_host"],
            self.raw,
        )
        self.db_port = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_DB_PORT",
            ["vs_vulnscan_enrichment", "db_port"],
            self.raw,
            isNumber=True,
            default=5432,
        )
        self.db_name = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_DB_NAME",
            ["vs_vulnscan_enrichment", "db_name"],
            self.raw,
            default="cyhy_mini_data_lake_staging",
        )
        self.db_user = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_DB_USER",
            ["vs_vulnscan_enrichment", "db_user"],
            self.raw,
            default="open_cti",
        )
        self.db_use_iam_auth = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_DB_USE_IAM_AUTH",
            ["vs_vulnscan_enrichment", "db_use_iam_auth"],
            self.raw,
            default=True,
        )
        self.db_password = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_DB_PASSWORD",
            ["vs_vulnscan_enrichment", "db_password"],
            self.raw,
            default="",
        )
        self.aws_region = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_AWS_REGION",
            ["vs_vulnscan_enrichment", "aws_region"],
            self.raw,
        )

        # --- dev/test discipline (§9) ---
        self.is_local = get_config_variable(
            "IS_LOCAL", ["vs_vulnscan_enrichment", "is_local"], self.raw, default=False
        )
        self.local_fixture_dir = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_LOCAL_FIXTURE_DIR",
            ["vs_vulnscan_enrichment", "local_fixture_dir"],
            self.raw,
            default="./tests/fixtures",
        )

        # A single "Enrich" click can, in principle, match many VulnScan rows for the same
        # host (many ports/plugins) or the same CVE (many hosts) -- bound how many go into one
        # Note the same way max_rows_per_run bounds A/D's polls, for the same reason (§9c): a
        # hard cap as a second, independent safety net against an unexpectedly large match set,
        # not something a per-entity trigger is naturally exempt from just because it's scoped
        # to one entity.
        self.max_vulnscan_rows_per_entity = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_MAX_ROWS_PER_ENTITY",
            ["vs_vulnscan_enrichment", "max_vulnscan_rows_per_entity"],
            self.raw,
            isNumber=True,
            default=50,
        )

        # --- attribution / marking (§10c) ---
        # Same author name as connectors A/D on purpose -- one consistent system Identity across
        # all four connectors.
        self.author_name = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_AUTHOR_NAME",
            ["vs_vulnscan_enrichment", "author_name"],
            self.raw,
            default="CISA VulnScanning",
        )
        self.tlp_marking = get_config_variable(
            "VS_VULNSCAN_ENRICHMENT_TLP_MARKING",
            ["vs_vulnscan_enrichment", "tlp_marking"],
            self.raw,
        )

        self._validate()

    def _validate(self) -> None:
        """Fail closed on the one decision this doc can't make silently. See module docstring."""
        if not self.tlp_marking:
            raise ConfigError(
                "vs_vulnscan_enrichment.tlp_marking is not set. This is a real, undecided "
                "policy question (OpenCTI-connector.md §10c) -- refusing to start rather than "
                "default to something like TLP:CLEAR for stakeholder vulnerability data. Set "
                "VS_VULNSCAN_ENRICHMENT_TLP_MARKING once the data-handling policy call is made."
            )
        if not self.is_local and not self.db_host:
            raise ConfigError(
                "vs_vulnscan_enrichment.db_host is not set and is_local is false -- nothing to "
                "connect to. Set VS_VULNSCAN_ENRICHMENT_DB_HOST, or IS_LOCAL=true to use "
                "fixtures instead."
            )
