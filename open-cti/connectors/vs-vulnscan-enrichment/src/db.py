"""mini_data_lake access for the VS VulnScan Enrichment connector.

Same two-implementation shape as connectors A/D's db.py (real Postgres + IS_LOCAL fixtures, see
OpenCTI-connector.md §9a) -- kept structurally identical rather than reinvented (§10i), even
though this connector is looked up per-entity rather than polled wholesale (§7b).

Table/column names taken from backend/src/xfd_django/xfd_mini_dl/models.py -- `VulnScan`
(L1737) has `db_table = "vuln_scan"`.

Real, open verification item (not yet confirmed against the live box): `VulnScan.Meta` defines
no `indexes` at all (unlike `Ticket`'s `tickets_is_open_idx`/`ticket_last_seen_idx`) -- meaning
`ip_string`/`cve_string` lookups here may currently be sequential scans over the whole table.
That matters more for this connector than A/D's polls: this runs synchronously while an analyst
is waiting on OpenCTI's "Enrich" button, not on a background schedule. Confirm the real query
plan (`EXPLAIN ANALYZE`) against `cyhy_mini_data_lake_staging` via `crossfeed-staging-bastion`
before treating this as production-ready -- flagged here rather than assumed either way.
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

LOGGER = logging.getLogger("vs_vulnscan_enrichment.db")


@dataclass
class VulnScanEnrichmentData:
    """Everything one enrichment lookup needs, regardless of where it came from."""

    vuln_scans: List[Dict] = field(default_factory=list)


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


# Explicit column projection (§10d) -- only what mapping.py actually maps into a Note. Each
# query below is one complete literal string, matching connectors A/D's db.py convention --
# no f-string/`.format()` assembly of query text at the call site. That wasn't just a style
# preference: bandit's B608 (hardcoded_sql_expressions) flagged an earlier version of this file
# that built the query via f-string-interpolating a shared column-list constant, even though the
# actual variable data was always going through a proper %(value)s placeholder, never the
# f-string. A real, low-confidence-but-worth-fixing finding -- writing each query as one
# complete literal (some column-list duplication, same tradeoff A/D already made) removes the
# pattern entirely instead of suppressing the warning.
_IP_QUERY = """
    SELECT id, ip_string, cve_string, cvss_base_score, cvss_vector, cvss3_base_score,
           cvss3_vector, cvss3_temporal_score, plugin_id, plugin_name, plugin_family,
           solution, synopsis, description, risk_factor, exploit_available,
           exploitability_ease, see_also, xref, port, port_protocol, service, source,
           owner, vuln_detection_timestamp
    FROM vuln_scan
    WHERE ip_string = %(value)s
    LIMIT %(limit)s
"""

_CVE_QUERY = """
    SELECT id, ip_string, cve_string, cvss_base_score, cvss_vector, cvss3_base_score,
           cvss3_vector, cvss3_temporal_score, plugin_id, plugin_name, plugin_family,
           solution, synopsis, description, risk_factor, exploit_available,
           exploitability_ease, see_also, xref, port, port_protocol, service, source,
           owner, vuln_detection_timestamp
    FROM vuln_scan
    WHERE UPPER(cve_string) = UPPER(%(value)s)
    LIMIT %(limit)s
"""


class VulnScanEnrichmentRepository:
    """Looks up VulnScan rows for one triggered entity, capped per config (§9c)."""

    def __init__(self, config: Config):
        """Hold the config; connections are opened per-call, not cached (§10d)."""
        self.config = config

    def fetch_by_ip(self, ip_string: str) -> VulnScanEnrichmentData:
        """Look up scanner detail for an IPv4-Addr/IPv6-Addr entity, by exact ip_string match."""
        if self.config.is_local:
            return self._fetch_local(lambda row: row.get("ip_string") == ip_string)
        return self._fetch_live(_IP_QUERY, ip_string)

    def fetch_by_cve(self, cve_string: str) -> VulnScanEnrichmentData:
        """Look up scanner detail for a Vulnerability entity, by case-insensitive cve_string match.

        Case-insensitive because connector A uppercases the `Vulnerability.name` it creates
        (OpenCTI-connector.md §7a), but `VulnScan.cve_string` is raw scanner data whose casing
        isn't independently confirmed here -- safer to match loosely than to silently miss real
        rows over a casing mismatch.
        """
        if self.config.is_local:
            return self._fetch_local(
                lambda row: (row.get("cve_string") or "").upper() == cve_string.upper()
            )
        return self._fetch_live(_CVE_QUERY, cve_string)

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------

    def _fetch_live(self, query: str, value: str) -> VulnScanEnrichmentData:
        conn = get_connection(self.config)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    query,
                    {"value": value, "limit": self.config.max_vulnscan_rows_per_entity},
                )
                return VulnScanEnrichmentData(
                    vuln_scans=[dict(row) for row in cur.fetchall()]
                )
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # IS_LOCAL fixture path (§9a) -- same shape as the live path, zero DB/network.
    # ------------------------------------------------------------------

    def _fetch_local(self, matches) -> VulnScanEnrichmentData:
        directory = self.config.local_fixture_dir
        LOGGER.info("IS_LOCAL=true -- loading fixtures from %s", directory)
        rows = self._load_json(directory, "vuln_scans.json")
        matched = [row for row in rows if matches(row)]
        return VulnScanEnrichmentData(
            vuln_scans=matched[: self.config.max_vulnscan_rows_per_entity]
        )

    @staticmethod
    def _load_json(directory: str, filename: str):
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
