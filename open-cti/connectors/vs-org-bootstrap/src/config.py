"""Config loading for the VS Organization & CIDR Bootstrap connector.

Precedence is env var > config.yml > default, via pycti's own get_config_variable() -- see
OpenCTI-connector.md §10b ("confirm rather than assume" pycti behavior; this one's verified
against the installed pycti==7.260824.0 source).

Fails closed on two things deliberately, rather than silently defaulting to something wrong:
  - tlp_marking: unset in this repo on purpose (§10c is a real, undecided policy question this
    doc can't answer). Refusing to start beats guessing TLP:CLEAR for stakeholder vuln data.
  - org_acronym_allowlist: empty means "scoped to nothing," not "all orgs" (§9c) -- a connector
    run has to opt in to being unscoped via allow_unscoped_run, not fall into it by omission.
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
            "VS_ORG_BOOTSTRAP_DB_HOST", ["vs_org_bootstrap", "db_host"], self.raw
        )
        self.db_port = get_config_variable(
            "VS_ORG_BOOTSTRAP_DB_PORT",
            ["vs_org_bootstrap", "db_port"],
            self.raw,
            isNumber=True,
            default=5432,
        )
        self.db_name = get_config_variable(
            "VS_ORG_BOOTSTRAP_DB_NAME",
            ["vs_org_bootstrap", "db_name"],
            self.raw,
            default="cyhy_mini_data_lake_staging",
        )
        self.db_user = get_config_variable(
            "VS_ORG_BOOTSTRAP_DB_USER",
            ["vs_org_bootstrap", "db_user"],
            self.raw,
            default="open_cti",
        )
        self.db_use_iam_auth = get_config_variable(
            "VS_ORG_BOOTSTRAP_DB_USE_IAM_AUTH",
            ["vs_org_bootstrap", "db_use_iam_auth"],
            self.raw,
            default=True,
        )
        self.db_password = get_config_variable(
            "VS_ORG_BOOTSTRAP_DB_PASSWORD",
            ["vs_org_bootstrap", "db_password"],
            self.raw,
            default="",
        )
        self.aws_region = get_config_variable(
            "VS_ORG_BOOTSTRAP_AWS_REGION", ["vs_org_bootstrap", "aws_region"], self.raw
        )

        # --- dev/test discipline (§9) ---
        self.is_local = get_config_variable(
            "IS_LOCAL", ["vs_org_bootstrap", "is_local"], self.raw, default=False
        )
        self.local_fixture_dir = get_config_variable(
            "VS_ORG_BOOTSTRAP_LOCAL_FIXTURE_DIR",
            ["vs_org_bootstrap", "local_fixture_dir"],
            self.raw,
            default="./tests/fixtures",
        )

        org_allowlist_raw = get_config_variable(
            "VS_ORG_BOOTSTRAP_ORG_ACRONYM_ALLOWLIST",
            ["vs_org_bootstrap", "org_acronym_allowlist"],
            self.raw,
            default="",
        )
        self.org_acronym_allowlist: List[str] = [
            acronym.strip()
            for acronym in (org_allowlist_raw or "").split(",")
            if acronym.strip()
        ]
        self.allow_unscoped_run = get_config_variable(
            "VS_ORG_BOOTSTRAP_ALLOW_UNSCOPED_RUN",
            ["vs_org_bootstrap", "allow_unscoped_run"],
            self.raw,
            default=False,
        )
        self.max_rows_per_run = get_config_variable(
            "VS_ORG_BOOTSTRAP_MAX_ROWS_PER_RUN",
            ["vs_org_bootstrap", "max_rows_per_run"],
            self.raw,
            isNumber=True,
            default=5000,
        )

        # --- attribution / marking (§10c) ---
        self.author_name = get_config_variable(
            "VS_ORG_BOOTSTRAP_AUTHOR_NAME",
            ["vs_org_bootstrap", "author_name"],
            self.raw,
            default="CISA VulnScanning",
        )
        self.tlp_marking = get_config_variable(
            "VS_ORG_BOOTSTRAP_TLP_MARKING",
            ["vs_org_bootstrap", "tlp_marking"],
            self.raw,
        )

        # Deliberately slower than Connectors A/C (§7d) -- org/CIDR data churns far less than
        # scan findings. ISO 8601 duration, read the same way pycti's own connectors do.
        self.duration_period = get_config_variable(
            "CONNECTOR_DURATION_PERIOD",
            ["connector", "duration_period"],
            self.raw,
            default="PT6H",
        )

        self._validate()

    def _validate(self) -> None:
        """Fail closed on the two decisions this doc can't make silently. See module docstring."""
        if not self.tlp_marking:
            raise ConfigError(
                "vs_org_bootstrap.tlp_marking is not set. This is a real, undecided policy "
                "question (OpenCTI-connector.md §10c) -- refusing to start rather than default "
                "to something like TLP:CLEAR for stakeholder vulnerability data. Set "
                "VS_ORG_BOOTSTRAP_TLP_MARKING once the data-handling policy call is made."
            )
        if not self.org_acronym_allowlist and not self.allow_unscoped_run:
            raise ConfigError(
                "vs_org_bootstrap.org_acronym_allowlist is empty and allow_unscoped_run is not "
                "set. An empty allowlist means 'scoped to nothing', not 'all orgs' -- see "
                "OpenCTI-connector.md §9c. Set VS_ORG_BOOTSTRAP_ORG_ACRONYM_ALLOWLIST for dev, "
                "or explicitly set VS_ORG_BOOTSTRAP_ALLOW_UNSCOPED_RUN=true for a deliberate "
                "full-scope production run."
            )
        if not self.is_local and not self.db_host:
            raise ConfigError(
                "vs_org_bootstrap.db_host is not set and is_local is false -- nothing to connect "
                "to. Set VS_ORG_BOOTSTRAP_DB_HOST, or IS_LOCAL=true to use fixtures instead."
            )
