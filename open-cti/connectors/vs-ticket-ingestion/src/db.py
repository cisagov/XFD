"""mini_data_lake access for the VS Ticket Ingestion connector.

Same two-implementation shape as connector D's db.py (real Postgres + IS_LOCAL fixtures, see
OpenCTI-connector.md §9a) -- kept structurally identical rather than reinvented, per §10i.

Table/column names taken from backend/src/xfd_django/xfd_mini_dl/models.py -- see
OpenCTI-connector.md §7a. `Ticket` (L2846) has `db_table = "ticket"` and its `organization`
FK column is `organization_id` (Django's default naming, no explicit db_column override --
confirmed by reading the model, not guessed).

Deliberate design choice, applying §10i's uuid-cast lesson before it could bite here too:
`Ticket.organization_id` is a native Postgres `uuid` column, same type as `Location.id` was in
connector D (where an unguarded `= ANY(%(list)s)` needed an explicit `::uuid[]` cast). Rather than
pull ticket rows first and then look up organizations by a Python list of ids the way connector D's
`_fetch_locations_live` did, this joins `ticket` to `organization` directly in one query and scopes
by `organization.acronym` (varchar) instead -- sidesteps the uuid/text[] type-adaptation gotcha
entirely rather than needing a cast to work around it. Verified against a real throwaway
`postgres:17` container before ever touching the live box (OpenCTI-connector.md §9b Loop 4).
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

LOGGER = logging.getLogger("vs_ticket_ingestion.db")


@dataclass
class TicketIngestionData:
    """Everything one connector run needs, regardless of where it came from."""

    tickets: List[Dict] = field(default_factory=list)


def _generate_iam_auth_token(config: Config) -> str:
    """Generate a short-lived RDS IAM auth token. Same pattern as connector D -- see its db.py."""
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


class VsTicketIngestionRepository:
    """Fetches ticket data, scoped and capped per config (§9c)."""

    def __init__(self, config: Config):
        """Hold the config; connections are opened per-call, not cached (§10d)."""
        self.config = config

    def fetch(self, since_last_seen: Optional[str]) -> TicketIngestionData:
        """Fetch one run's worth of data, from fixtures (IS_LOCAL) or mini_data_lake."""
        if self.config.is_local:
            return self._fetch_local()
        return self._fetch_live(since_last_seen)

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------

    def _fetch_live(self, since_last_seen: Optional[str]) -> TicketIngestionData:
        conn = get_connection(self.config)
        try:
            return TicketIngestionData(
                tickets=self._fetch_tickets_live(conn, since_last_seen)
            )
        finally:
            conn.close()

    def _fetch_tickets_live(self, conn, since_last_seen: Optional[str]) -> List[Dict]:
        # Explicit column projection (§10d) -- only what mapping.py actually maps to STIX.
        #
        # Incremental strategy (§7a): COALESCE(closed_timestamp, updated_timestamp), already
        # indexed as ticket_last_seen_idx (models.py ~L3044) -- a ticket flipping open->closed,
        # or not-false-positive->false-positive, shows up naturally as an "updated" row on the
        # next poll without any separate closure-detection logic.
        #
        # Deliberately NOT filtering false_positive=True out of the query. §7a: a
        # previously-ingested ticket that flips to false_positive=True needs its relationship
        # revoked (connector.py), not silently dropped -- filtering it out in SQL would mean the
        # connector never sees that row again after the flip and could never detect the reversal.
        #
        # (%(acronyms)s IS NULL OR ...) guard built in from the start, not added after a live
        # "returned zero rows" surprise -- that's what happened building connector D
        # (OpenCTI-connector.md §10i) with the exact same acronym = ANY(NULL) semantics.
        query = """
            SELECT t.id, t.cve_string, t.vuln_name, t.service_name, t.vuln_source,
                   t.ip_string, t.opened_timestamp, t.closed_timestamp, t.updated_timestamp,
                   t.is_open, t.is_kev, t.is_kev_ransomware, t.is_risky, t.false_positive,
                   t.cvss_severity, t.vuln_port, t.port_protocol,
                   o.acronym AS organization_acronym, o.name AS organization_name
            FROM ticket t
            JOIN organization o ON o.id = t.organization_id
            WHERE (%(acronyms)s IS NULL OR o.acronym = ANY(%(acronyms)s))
              AND (
                  %(since)s IS NULL
                  OR COALESCE(t.closed_timestamp, t.updated_timestamp) > %(since)s
              )
            ORDER BY COALESCE(t.closed_timestamp, t.updated_timestamp)
            LIMIT %(limit)s
        """
        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "acronyms": self.config.org_acronym_allowlist or None,
                    "since": since_last_seen,
                    "limit": self.config.max_rows_per_run,
                },
            )
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # IS_LOCAL fixture path (§9a) -- same shape as the live path, zero DB/network.
    # ------------------------------------------------------------------

    def _fetch_local(self) -> TicketIngestionData:
        directory = self.config.local_fixture_dir
        LOGGER.info("IS_LOCAL=true -- loading fixtures from %s", directory)
        return TicketIngestionData(tickets=self._load_json(directory, "tickets.json"))

    @staticmethod
    def _load_json(directory: str, filename: str):
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
