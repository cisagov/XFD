"""mini_data_lake access for the VS Port/Service Inventory connector.

Same two-implementation shape as connectors A/D's db.py (real Postgres + IS_LOCAL fixtures, see
OpenCTI-connector.md §9a) -- kept structurally identical rather than reinvented (§10i).

Table/column names taken from backend/src/xfd_django/xfd_mini_dl/models.py -- `LatestPortScan`
(L3116) has `db_table = "latest_port_scan"` and, unlike `VulnScan` (Connector B), *does* have
real indexes: a unique constraint plus explicit indexes on
`(organization, ip, port, protocol)`, `(ip, current, time_scanned)`, `time_scanned`, and `state`
-- confirmed by reading the model's own `Meta.indexes`, not assumed.

No timestamp-watermark query here, deliberately (§7c) -- `mark_stale_latest_port_scans()`
(`backend/src/xfd_django/xfd_api/tasks/utils/vs_port_scans.py:771`) flips `current` to `False`
via a plain `UPDATE ... SET current = FALSE WHERE time_scanned < cutoff`, never touching
`time_scanned` itself -- confirmed by reading that function directly. A `WHERE time_scanned >
watermark` poll would never see that transition, so this connector polls the *entire*
in-scope table every run instead and lets connector.py diff against its own state (§10i-style
verification: read the actual mutation before trusting a watermark strategy would work here).
"""

# Standard Python Libraries
from dataclasses import dataclass, field
import json
import logging
import os
from typing import Dict, List

# Third-Party Libraries
import boto3
import psycopg2
import psycopg2.extras

from .config import Config

LOGGER = logging.getLogger("vs_port_inventory.db")


@dataclass
class PortInventoryData:
    """Everything one connector run needs, regardless of where it came from."""

    port_scans: List[Dict] = field(default_factory=list)


def _generate_iam_auth_token(config: Config) -> str:
    """Generate a short-lived RDS IAM auth token. Same pattern as connectors A/D -- see their db.py."""
    client = boto3.client("rds", region_name=config.aws_region)
    return client.generate_db_auth_token(
        DBHostname=config.db_host,
        Port=config.db_port,
        DBUsername=config.db_user,
    )


def get_connection(config: Config):
    """Open a psycopg2 connection to mini_data_lake, IAM-auth or password per config."""
    password = (
        _generate_iam_auth_token(config)
        if config.db_use_iam_auth
        else config.db_password
    )
    return psycopg2.connect(
        host=config.db_host,
        port=config.db_port,
        dbname=config.db_name,
        user=config.db_user,
        password=password,
        sslmode="require",  # IAM auth requires TLS regardless of rds.force_ssl -- §2
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
    )


# One complete literal query, matching connectors A/B/D's convention -- no f-string/`.format()`
# assembly of query text (Connector B's db.py hit a real bandit B608 finding over exactly that
# pattern; avoided here from the start instead of fixed after the fact).
#
# Explicit column projection (§10d) -- only what mapping.py actually maps to STIX. `current` is
# selected (not filtered on) deliberately -- §7c's full-poll-and-diff strategy needs to see both
# still-open *and* newly-stale rows in the same query, not just the currently-open subset, so
# connector.py can tell "went stale this run" apart from "was already stale last run" itself.
#
# (%(acronyms)s IS NULL OR ...) guard built in from the start (§10i) -- same acronym = ANY(NULL)
# semantics already found for real once building connector D.
#
# organization is a direct FK here (unlike VulnScan's denormalized `owner` string) -- joined
# server-side and scoped by acronym (varchar), the same structural choice connector A's db.py
# made to sidestep ever needing a `uuid = ANY(list)` cast for organization_id.
_QUERY = """
    SELECT lps.id, lps.ip_string, lps.port, lps.protocol, lps.state, lps.time_scanned,
           lps.service_name, lps.service_cpe, lps.service_product, lps.service_version,
           lps.source, lps.nmi_service_group, lps.risky_service_group, lps.current,
           lps.port_scan_id, o.acronym AS organization_acronym, o.name AS organization_name
    FROM latest_port_scan lps
    JOIN organization o ON o.id = lps.organization_id
    WHERE (%(acronyms)s IS NULL OR o.acronym = ANY(%(acronyms)s))
    ORDER BY o.acronym, lps.ip_string, lps.port, lps.protocol
    LIMIT %(limit)s
"""


class VsPortInventoryRepository:
    """Fetches the full in-scope LatestPortScan table, capped per config (§9c)."""

    def __init__(self, config: Config):
        """Hold the config; connections are opened per-call, not cached (§10d)."""
        self.config = config

    def fetch(self) -> PortInventoryData:
        """Fetch this run's full in-scope snapshot, from fixtures (IS_LOCAL) or mini_data_lake."""
        if self.config.is_local:
            return self._fetch_local()
        return self._fetch_live()

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------

    def _fetch_live(self) -> PortInventoryData:
        conn = get_connection(self.config)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _QUERY,
                    {
                        "acronyms": self.config.org_acronym_allowlist or None,
                        "limit": self.config.max_rows_per_run,
                    },
                )
                return PortInventoryData(
                    port_scans=[dict(row) for row in cur.fetchall()]
                )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # IS_LOCAL fixture path (§9a) -- same shape as the live path, zero DB/network.
    # ------------------------------------------------------------------

    def _fetch_local(self) -> PortInventoryData:
        directory = self.config.local_fixture_dir
        LOGGER.info("IS_LOCAL=true -- loading fixtures from %s", directory)
        return PortInventoryData(
            port_scans=self._load_json(directory, "port_scans.json")
        )

    @staticmethod
    def _load_json(directory: str, filename: str):
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
