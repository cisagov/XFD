"""mini_data_lake access for the VS Organization & CIDR Bootstrap connector.

Two implementations behind one interface (VsOrgBootstrapRepository): a real Postgres-backed one
and an IS_LOCAL fixture-backed one, mirroring the convention already used throughout
backend/src/xfd_django/xfd_api/tasks/utils/query_redshift.py's load_test_data(). See
OpenCTI-connector.md §9a.

Table/column names below are taken from backend/src/xfd_django/xfd_mini_dl/models.py -- see
OpenCTI-connector.md §7d for the line references. Sector.organizations is a plain Django
ManyToManyField with no `through` model (models.py ~L2450), so its join table was initially a
guess at Django's default naming convention rather than something read off an explicit model
class -- confirmed against the real schema (2026-08-26) as `sector_organizations`, columns
`sector_id`/`organization_id`, exactly as guessed.
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

LOGGER = logging.getLogger("vs_org_bootstrap.db")


@dataclass
class OrgBootstrapData:
    """Everything one connector run needs, regardless of where it came from."""

    organizations: List[Dict] = field(default_factory=list)
    sectors: List[Dict] = field(default_factory=list)
    # sector acronym -> list of member org acronyms
    sector_memberships: Dict[str, List[str]] = field(default_factory=dict)
    # location id -> location row
    locations_by_id: Dict[str, Dict] = field(default_factory=dict)
    # list of {cidr fields..., organization_acronym, first_seen, last_seen, current}
    cidrs: List[Dict] = field(default_factory=list)


def _generate_iam_auth_token(config: Config) -> str:
    """Generate a short-lived RDS IAM auth token.

    See OpenCTI-connector.md §2 -- ~15min TTL, so this is called fresh per connection, never
    cached across the connector's lifetime.
    """
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


class VsOrgBootstrapRepository:
    """Fetches org/sector/CIDR/location data, scoped and capped per config (§9c)."""

    def __init__(self, config: Config):
        """Hold the config; connections are opened per-call, not cached (§10d)."""
        self.config = config

    def fetch(self, since_updated_at: Optional[str]) -> OrgBootstrapData:
        """Fetch one run's worth of data, from fixtures (IS_LOCAL) or mini_data_lake."""
        if self.config.is_local:
            return self._fetch_local()
        return self._fetch_live(since_updated_at)

    # ------------------------------------------------------------------
    # Live path
    # ------------------------------------------------------------------

    def _fetch_live(self, since_updated_at: Optional[str]) -> OrgBootstrapData:
        conn = get_connection(self.config)
        try:
            organizations = self._fetch_organizations_live(conn, since_updated_at)
            org_acronyms = [org["acronym"] for org in organizations]
            location_ids = [
                org["location_id"] for org in organizations if org.get("location_id")
            ]

            return OrgBootstrapData(
                organizations=organizations,
                sectors=self._fetch_sectors_live(conn),
                sector_memberships=self._fetch_sector_memberships_live(
                    conn, org_acronyms
                ),
                locations_by_id=self._fetch_locations_live(conn, location_ids),
                cidrs=self._fetch_cidrs_live(conn, org_acronyms),
            )
        finally:
            conn.close()

    def _fetch_organizations_live(
        self, conn, since_updated_at: Optional[str]
    ) -> List[Dict]:
        # Explicit column projection (§10d) -- only what mapping.py actually maps to STIX.
        # Filtered by the org acronym allowlist (§9c) and, when present, Organization.updated_at
        # (§7d -- the one table in this whole architecture with a real watermark column, no
        # LatestPortScan/Ticket-style gotchas).
        # `acronym = ANY(NULL)` evaluates to NULL (not TRUE) in Postgres -- verified against a
        # real instance -- so without the explicit "IS NULL OR" branch, an unscoped run
        # (ALLOW_UNSCOPED_RUN=true, empty allowlist -> acronyms param is None) would silently
        # return zero organizations instead of all of them. Found before this was ever actually
        # exercised, not from a live failure.
        query = """
            SELECT id, acronym, name, retired, stakeholder, vs_stakeholder, type,
                   state, state_name, county, county_fips, state_fips, country, country_name,
                   location_id, parent_id, updated_at
            FROM organization
            WHERE (%(acronyms)s IS NULL OR acronym = ANY(%(acronyms)s))
              AND (%(since)s IS NULL OR updated_at > %(since)s)
            ORDER BY updated_at
            LIMIT %(limit)s
        """
        with conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "acronyms": self.config.org_acronym_allowlist or None,
                    "since": since_updated_at,
                    "limit": self.config.max_rows_per_run,
                },
            )
            return [dict(row) for row in cur.fetchall()]

    def _fetch_sectors_live(self, conn) -> List[Dict]:
        # Small, low-cardinality table (~20 rows, CISA's sector taxonomy) -- full poll every run
        # rather than tracking incrementally, per §7d.
        with conn.cursor() as cur:
            cur.execute("SELECT id, acronym, name, retired FROM sector")
            return [dict(row) for row in cur.fetchall()]

    def _fetch_sector_memberships_live(
        self, conn, org_acronyms: List[str]
    ) -> Dict[str, List[str]]:
        if not org_acronyms:
            return {}
        # sector_organizations/sector_id/organization_id confirmed against the real schema
        # (see module docstring) -- Django's default M2M join-table naming, as guessed.
        query = """
            SELECT s.acronym AS sector_acronym, o.acronym AS org_acronym
            FROM sector_organizations so
            JOIN sector s ON s.id = so.sector_id
            JOIN organization o ON o.id = so.organization_id
            WHERE o.acronym = ANY(%(acronyms)s)
        """
        memberships: Dict[str, List[str]] = {}
        with conn.cursor() as cur:
            cur.execute(query, {"acronyms": org_acronyms})
            for row in cur.fetchall():
                memberships.setdefault(row["sector_acronym"], []).append(
                    row["org_acronym"]
                )
        return memberships

    def _fetch_locations_live(self, conn, location_ids: List[str]) -> Dict[str, Dict]:
        if not location_ids:
            return {}
        # location.id is a native Postgres uuid column; psycopg2 adapts a Python list of
        # id strings to a text[] array by default, and Postgres won't implicitly compare
        # uuid = ANY(text[]) -- "operator does not exist: uuid = text", hit for real on a live
        # run, not caught by the mapping-only tests (fixtures never round-trip through
        # psycopg2's actual type adaptation). Explicit cast needed; the other three ANY()
        # queries in this file all compare acronym (varchar), which doesn't have this problem.
        query = """
            SELECT id, name, country_abrv, country, county, county_fips, gnis_id,
                   state_abrv, state
            FROM location
            WHERE id = ANY(%(ids)s::uuid[])
        """
        with conn.cursor() as cur:
            cur.execute(query, {"ids": location_ids})
            return {str(row["id"]): dict(row) for row in cur.fetchall()}

    def _fetch_cidrs_live(self, conn, org_acronyms: List[str]) -> List[Dict]:
        if not org_acronyms:
            return []
        query = """
            SELECT c.network, c.retired AS cidr_retired,
                   co.first_seen, co.last_seen, co.current,
                   o.acronym AS organization_acronym
            FROM cidr_orgs co
            JOIN cidr c ON c.id = co.cidr_id
            JOIN organization o ON o.id = co.organization_id
            WHERE o.acronym = ANY(%(acronyms)s)
            LIMIT %(limit)s
        """
        with conn.cursor() as cur:
            cur.execute(
                query,
                {"acronyms": org_acronyms, "limit": self.config.max_rows_per_run},
            )
            return [dict(row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    # IS_LOCAL fixture path (§9a) -- same shape as the live path, zero DB/network.
    # ------------------------------------------------------------------

    def _fetch_local(self) -> OrgBootstrapData:
        directory = self.config.local_fixture_dir
        LOGGER.info("IS_LOCAL=true -- loading fixtures from %s", directory)
        return OrgBootstrapData(
            organizations=self._load_json(directory, "organizations.json"),
            sectors=self._load_json(directory, "sectors.json"),
            sector_memberships=self._load_json(directory, "sector_memberships.json"),
            locations_by_id=self._load_json(directory, "locations_by_id.json"),
            cidrs=self._load_json(directory, "cidrs.json"),
        )

    @staticmethod
    def _load_json(directory: str, filename: str):
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
