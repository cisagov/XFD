"""Orchestration for the VS Organization & CIDR Bootstrap connector (OpenCTI-connector.md §7d).

Root of the four-connector dependency chain (§8) -- Connectors A and C both resolve their org
Identity by acronym against what this connector creates. Build/deploy order: this one first.
"""

# Standard Python Libraries
import datetime
import logging
from typing import Dict, Optional

# Third-Party Libraries
from pycti import OpenCTIConnectorHelper
import stix2

from . import mapping
from .config import Config
from .db import OrgBootstrapData, VsOrgBootstrapRepository

LOGGER = logging.getLogger("vs_org_bootstrap")

# Well-known, platform-recognized TLP marking-definition STIX ids (stix2 ships these with the
# fixed ids OpenCTI already seeds by default -- no lookup/create needed, just reference them).
# TLP:CLEAR is the STIX 2.1 successor name for TLP:WHITE; both map to the same marking here since
# this stix2 version only ships the pre-2.1 WHITE/GREEN/AMBER/RED set.
_TLP_MARKINGS = {
    "TLP:CLEAR": stix2.TLP_WHITE,
    "TLP:WHITE": stix2.TLP_WHITE,
    "TLP:GREEN": stix2.TLP_GREEN,
    "TLP:AMBER": stix2.TLP_AMBER,
    "TLP:RED": stix2.TLP_RED,
}


def resolve_marking(tlp_marking: str) -> stix2.MarkingDefinition:
    """Resolve a TLP string to its well-known marking-definition object.

    Config validation (config.py) already refuses an empty value -- this refuses an unrecognized
    one too, rather than silently falling back to something permissive.
    """
    marking = _TLP_MARKINGS.get(tlp_marking.strip().upper())
    if marking is None:
        raise ValueError(
            f"Unrecognized tlp_marking {tlp_marking!r}. Expected one of: "
            f"{', '.join(_TLP_MARKINGS)} (see OpenCTI-connector.md §10c)."
        )
    return marking


class VsOrgBootstrapConnector:
    """Polls org/CIDR data from mini_data_lake and upserts it into OpenCTI.

    Produces Identity/Location/IPv4-Addr(CIDR) objects and their relationships.
    """

    def __init__(self, config: Optional[Config] = None, helper=None):
        """Build the connector, injecting `config`/`helper` for tests instead of the real thing.

        `config`/`helper` injection points exist for tests (§9b Loop 2 dry-run) -- production
        (main.py) always calls VsOrgBootstrapConnector() with neither, building the real thing.
        """
        self.config = config or Config()
        self.helper = helper or OpenCTIConnectorHelper(self.config.raw)
        self.repository = VsOrgBootstrapRepository(self.config)

        self.author = mapping.build_author(self.config.author_name)
        self.marking = resolve_marking(self.config.tlp_marking)

        LOGGER.info(
            "VS Org Bootstrap connector initialized (is_local=%s, org_allowlist=%s)",
            self.config.is_local,
            self.config.org_acronym_allowlist or "<unscoped>",
        )

    def run(self) -> None:
        """Entry point pycti's scheduler calls each duration_period tick."""
        self.helper.connector_logger.info("Starting VS Org Bootstrap run")
        state = self.helper.get_state() or {}

        try:
            data = self.repository.fetch(
                since_updated_at=state.get("last_updated_at_watermark")
            )
            new_watermark = self._process(data, state)
        except Exception as e:  # pylint: disable=broad-except
            # §10e: don't let one bad run corrupt state -- log and let the next scheduled tick
            # retry from the last confirmed watermark rather than partially advancing it.
            # connector_logger is pycti's own AppLogger, not a stdlib logging.Logger -- verified
            # against the installed source after this call itself crashed with "unexpected
            # keyword argument 'exc_info'" while trying to log a real error (worse than not
            # catching at all, since it masked the original exception). AppLogger.error() takes
            # (message, meta=None) and always passes exc_info=1 to the underlying logger
            # internally, so the traceback is captured automatically either way.
            self.helper.connector_logger.error(
                "VS Org Bootstrap run failed", meta={"error": str(e)}
            )
            return

        # §10f: only advance the watermark after the bundle has actually been accepted by
        # OpenCTI, not before -- new_watermark is None (unchanged) whenever nothing was sent.
        if new_watermark is not None:
            state["last_updated_at_watermark"] = new_watermark
            self.helper.set_state(state)

        self.helper.connector_logger.info("VS Org Bootstrap run complete")

    # ------------------------------------------------------------------

    def _process(self, data: OrgBootstrapData, state: Dict) -> Optional[str]:
        """Build the STIX bundle for one run and send it.

        Returns the new watermark value to persist, or None if there was nothing to send (so
        run() leaves state untouched).
        """
        if not data.organizations:
            self.helper.connector_logger.info("No organizations in scope for this run")
            return None

        objects = [self.author, self.marking]

        # --- Sectors first (org->sector relationships need the Sector Identity to exist) ---
        # §7d / §6: real collision risk with connector-opencti's default sector taxonomy.
        # TODO: look up existing Identity(class=sector) by name via self.helper.api before
        # deciding to mint a new one -- deferred here pending the ground-truthing pass
        # (OpenCTI-connector.md §10, next steps) that checks the actual overlap.
        sector_stix_by_acronym = {}
        for sector_row in data.sectors:
            sector_obj = mapping.map_sector(sector_row, self.author.id, self.marking.id)
            sector_stix_by_acronym[sector_row["acronym"]] = sector_obj.id
            objects.append(sector_obj)

        # --- Locations, keyed by mini_data_lake location id ---
        location_stix_by_id = {}
        for location_id, location_row in data.locations_by_id.items():
            location_obj = mapping.map_location(
                location_row, self.author.id, self.marking.id
            )
            if location_obj is not None:
                location_stix_by_id[location_id] = location_obj.id
                objects.append(location_obj)

        # --- Organizations + their part-of/located-at relationships ---
        org_stix_by_acronym = {}
        org_row_by_acronym = {}
        for org_row in data.organizations:
            org_obj = mapping.map_organization(org_row, self.author.id, self.marking.id)
            org_stix_by_acronym[org_row["acronym"]] = org_obj.id
            org_row_by_acronym[org_row["acronym"]] = org_row
            objects.append(org_obj)

            if (
                org_row.get("location_id")
                and org_row["location_id"] in location_stix_by_id
            ):
                objects.append(
                    self._located_at_relationship(
                        state,
                        org_row["acronym"],
                        org_obj.id,
                        location_stix_by_id[org_row["location_id"]],
                    )
                )

        # Parent/child org relationships -- needs both orgs resolved first, hence a second pass.
        for acronym, org_row in org_row_by_acronym.items():
            parent_id = org_row.get("parent_id")
            if not parent_id:
                continue
            parent_acronym = next(
                (a for a, r in org_row_by_acronym.items() if r["id"] == parent_id), None
            )
            if parent_acronym and parent_acronym in org_stix_by_acronym:
                objects.append(
                    self._part_of_relationship(
                        state,
                        f"org:{acronym}->org:{parent_acronym}",
                        org_stix_by_acronym[acronym],
                        org_stix_by_acronym[parent_acronym],
                    )
                )

        # Sector membership -- from the M2M join, not a column on organization itself.
        for sector_acronym, member_acronyms in data.sector_memberships.items():
            if sector_acronym not in sector_stix_by_acronym:
                continue
            for member_acronym in member_acronyms:
                if member_acronym not in org_stix_by_acronym:
                    continue
                objects.append(
                    self._part_of_relationship(
                        state,
                        f"org:{member_acronym}->sector:{sector_acronym}",
                        org_stix_by_acronym[member_acronym],
                        sector_stix_by_acronym[sector_acronym],
                    )
                )

        # --- CIDRs + ownership relationships ---
        # §10e says one bad row shouldn't sink an entire poll's bundle -- this loop is where
        # that was actually just tested for real: a single malformed CIDR (a same-day
        # open+close, see mapping.build_owns_cidr) previously aborted the *whole* run, at full
        # production scale (13k+ orgs), not just that one org. Isolated per-row instead of
        # relying on run()'s top-level catch, which only protects state from a failed run, not
        # one run's success from a single bad row within it.
        for cidr_row in data.cidrs:
            org_acronym = cidr_row.get("organization_acronym")
            if org_acronym not in org_stix_by_acronym:
                continue
            try:
                cidr_obj = mapping.map_cidr_observable(cidr_row["network"])
                relationship = self._cidr_relationship(
                    state, org_stix_by_acronym[org_acronym], cidr_obj.id, cidr_row
                )
            except Exception as e:  # pylint: disable=broad-except
                self.helper.connector_logger.warning(
                    f"Skipping CIDR {cidr_row.get('network')!r} for org {org_acronym!r}: {e}"
                )
                continue
            objects.append(cidr_obj)
            objects.append(relationship)

        objects = mapping.dedupe_bundle_objects(objects)
        bundle = self.helper.stix2_create_bundle(objects)
        self.helper.send_stix2_bundle(bundle, update=True)

        # connector_logger is pycti's AppLogger, not a stdlib logging.Logger -- it takes
        # (message, meta=None), not lazy %-style formatting with extra positional args (same
        # class of mistake as the exc_info bug above; found the same way, by it crashing on a
        # real run). Pre-format the message into one string instead.
        self.helper.connector_logger.info(
            f"Sent {len(objects)} objects "
            f"({len(data.organizations)} orgs, {len(data.sectors)} sectors, "
            f"{len(data.cidrs)} CIDRs)"
        )

        watermark = max(
            (org["updated_at"] for org in data.organizations if org.get("updated_at")),
            default=None,
        )
        # Same live-vs-fixture type gap as mapping.normalize_timestamp() -- psycopg2 returns a
        # real datetime.datetime for organization.updated_at (a timestamptz column), but our
        # IS_LOCAL fixtures store it as a JSON/ISO string already. pycti's set_state() does a
        # plain json.dumps(state) with no datetime support, so a raw datetime here crashes for
        # real on a live run ("Object of type datetime is not JSON serializable") -- not caught
        # by fixture-based tests for the same reason the UUID/date bugs weren't.
        # isinstance, not hasattr -- mypy can verify the None branch is unreachable through
        # isinstance narrowing, which it can't do for a hasattr() guard (a real limitation, not
        # a runtime bug: hasattr(None, "isoformat") is correctly False at runtime either way,
        # proven by the test suite, but mypy flagged this as a real pre-commit blocker).
        return (
            watermark.isoformat()
            if isinstance(watermark, datetime.datetime)
            else watermark
        )

    # ------------------------------------------------------------------
    # §10a idempotency: reuse a previously-recorded relationship id rather than trusting
    # OpenCTI's fuzzy ±30-day type/source/target/time dedup window to find the right one,
    # especially for the null->set stop_time transition that isn't clearly documented there.
    # ------------------------------------------------------------------

    def _located_at_relationship(
        self, state: Dict, org_acronym: str, org_id: str, location_id: str
    ):
        rel_map = state.setdefault("located_at_relationship_ids", {})
        rel = mapping.build_located_at(
            org_id,
            location_id,
            self.author.id,
            self.marking.id,
            existing_id=rel_map.get(org_acronym),
        )
        rel_map[org_acronym] = rel.id
        return rel

    def _part_of_relationship(
        self, state: Dict, key: str, child_id: str, parent_id: str
    ):
        rel_map = state.setdefault("part_of_relationship_ids", {})
        rel = mapping.build_part_of(
            child_id,
            parent_id,
            self.author.id,
            self.marking.id,
            existing_id=rel_map.get(key),
        )
        rel_map[key] = rel.id
        return rel

    def _cidr_relationship(
        self, state: Dict, org_id: str, cidr_id: str, cidr_row: Dict
    ):
        rel_map = state.setdefault("cidr_relationship_ids", {})
        key = f"{org_id}:{cidr_row['network']}"
        stop_time = None if cidr_row.get("current") else cidr_row.get("last_seen")
        rel = mapping.build_owns_cidr(
            org_id,
            cidr_id,
            self.author.id,
            self.marking.id,
            first_seen=cidr_row.get("first_seen"),
            last_seen_or_stop=stop_time,
            existing_id=rel_map.get(key),
        )
        rel_map[key] = rel.id
        return rel
