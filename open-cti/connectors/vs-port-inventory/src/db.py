"""mini_data_lake access for the VS Port/Service Inventory connector.

Same two-implementation shape as connectors A/D's db.py (real Postgres + IS_LOCAL fixtures, see
OpenCTI-connector.md §9a) -- kept structurally identical rather than reinvented (§10i).

Table/column names taken from backend/src/xfd_django/xfd_mini_dl/models.py -- `LatestPortScan`
(L3116) has `db_table = "latest_port_scan"` and, unlike `VulnScan` (Connector B), *does* have
real indexes: a unique constraint plus explicit indexes on
`(organization, ip, port, protocol)`, `(ip, current, time_scanned)`, `time_scanned`, and `state`
-- confirmed by reading the model's own `Meta.indexes`, not assumed.

**Revised design (2026-08-31): windowed/watermark polling, not a full-table poll every run.**
The original version of this file polled the entire in-scope table on every run, specifically
because `mark_stale_latest_port_scans()`
(`backend/src/xfd_django/xfd_api/tasks/utils/vs_port_scans.py:771`) flips `current` to `False`
via a plain `UPDATE ... SET current = FALSE WHERE time_scanned < cutoff`, never touching
`time_scanned` -- confirmed by reading that function directly. A plain `WHERE time_scanned >
watermark` poll can never see that transition, on the first run or any later one, since nothing
ever bumps the timestamp when it happens.

Full-table-every-run turned out to be too expensive against the real row count, though -- so the
fix isn't a bigger `max_rows_per_run`, it's not needing to observe that transition via a query at
all. `connector.py` now computes staleness itself, locally, from `time_scanned` and a known
cutoff -- the exact same rule `mark_stale_latest_port_scans()` applies, just evaluated in our own
process instead of re-derived from a fresh row every time. That turns this back into an ordinary
watermark poll:

- `since_last_seen`/`include_current` here are connector A's `since_last_seen`/
  `include_stale_open` pattern, applied to this table: the bootstrap poll (no watermark yet)
  also pulls in every row the source still marks `current = TRUE`, regardless of how old
  `time_scanned` is, so a currently-open port scanned long ago isn't permanently missed the same
  way connector A's stale-open tickets were. Bounded by `max_rows_per_run` + `ORDER BY
  time_scanned` exactly like connector A's bootstrap -- a "monumental" first run still safely
  paginates across however many polls it takes, oldest-relevant-first, instead of ever pulling
  everything in one shot.
- Every poll after that is a plain `time_scanned > watermark` query -- new ports and anything
  actually rescanned. Nothing here ever needs to re-derive "did this go stale," because
  connector.py already tracks that itself from data it already has.
"""

# Standard Python Libraries
from dataclasses import dataclass, field
import json
import logging
import os
from typing import Dict, List, Optional

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
# still selected -- used only to decide what to *fetch* during the bootstrap poll (see module
# docstring), never trusted directly for the state connector.py actually records; that's derived
# locally from `time_scanned` + the configured cutoff instead, uniformly for every row regardless
# of how it was matched.
#
# (%(acronyms)s IS NULL OR ...) guard built in from the start (§10i) -- same acronym = ANY(NULL)
# lesson connector A's db.py already applies.
#
# The since/include_current condition is deliberately *not* "since IS NULL OR ..." the way
# connector A's is -- verified directly against a real postgres:17 container (§9b Loop 4) that
# copying that shape here was a real bug: on a bootstrap poll (since IS NULL), an unconditional
# "IS NULL" branch makes the whole OR true regardless of `current`, silently pulling in
# already-stale rows a bootstrap poll should never touch. `(since IS NOT NULL AND time_scanned >
# since) OR (include_current AND current IS TRUE)` means the first branch only ever fires once a
# real watermark exists, so a bootstrap poll (since IS NULL) is governed by `include_current`
# alone -- confirmed against the same container that this correctly excludes a stale row with
# current=false, and excludes everything once include_current=False in steady state.
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
      AND (
          (%(since)s IS NOT NULL AND lps.time_scanned > %(since)s)
          OR (%(include_current)s AND lps.current IS TRUE)
      )
    ORDER BY lps.time_scanned
    LIMIT %(limit)s
"""


class VsPortInventoryRepository:
    """Fetches one incremental window of LatestPortScan, capped per config (§9c)."""

    def __init__(self, config: Config):
        """Hold the config; connections are opened per-call, not cached (§10d)."""
        self.config = config

    def fetch(
        self, since_last_seen: Optional[str], include_current: bool = False
    ) -> PortInventoryData:
        """Fetch one run's worth of data, from fixtures (IS_LOCAL) or mini_data_lake.

        `include_current` is the bootstrap-only safety net (see connector.py's `run()` for where
        it's computed) -- see the module docstring for why it exists.
        """
        if self.config.is_local:
            return self._fetch_local()
        return self._fetch_live(since_last_seen, include_current)

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------

    def _fetch_live(
        self, since_last_seen: Optional[str], include_current: bool
    ) -> PortInventoryData:
        conn = get_connection(self.config)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    _QUERY,
                    {
                        "acronyms": self.config.org_acronym_allowlist or None,
                        "since": since_last_seen,
                        "include_current": include_current,
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
