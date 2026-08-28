"""Orchestration for the VS VulnScan Enrichment connector (OpenCTI-connector.md §7b).

Depends on connector A (or some other process) having already created the Vulnerability/
IPv4-Addr/IPv6-Addr entity being enriched (§7b) -- this is not a standalone ingestion path.

Structurally different from connectors A/D in one real way, not just cosmetically: this is
INTERNAL_ENRICHMENT, triggered per-entity via `helper.listen()`, not `schedule_iso()`. There's no
`run()`/watermark/scoping-lever machinery here because there's no wholesale poll to guard -- each
invocation is already scoped to exactly one entity by construction. Everything else (author/
marking setup, AppLogger call discipline, idempotent-id pinning via connector state) follows the
same §10i discipline as A/D.
"""

# Standard Python Libraries
import logging
from typing import Dict, Optional

# Third-Party Libraries
from pycti import OpenCTIConnectorHelper
import stix2

from . import mapping
from .config import Config
from .db import VulnScanEnrichmentRepository

LOGGER = logging.getLogger("vs_vulnscan_enrichment")

# Same well-known TLP marking-definition ids as connectors A/D.
_TLP_MARKINGS = {
    "TLP:CLEAR": stix2.TLP_WHITE,
    "TLP:WHITE": stix2.TLP_WHITE,
    "TLP:GREEN": stix2.TLP_GREEN,
    "TLP:AMBER": stix2.TLP_AMBER,
    "TLP:RED": stix2.TLP_RED,
}

# CONNECTOR_SCOPE (§7b) -- the only entity types this connector ever gets triggered on.
_IP_TYPES = {"IPv4-Addr", "IPv6-Addr"}
_VULNERABILITY_TYPE = "Vulnerability"


def resolve_marking(tlp_marking: str) -> stix2.MarkingDefinition:
    """Resolve a TLP string to its well-known marking-definition object. Identical to A/D."""
    marking = _TLP_MARKINGS.get(tlp_marking.strip().upper())
    if marking is None:
        raise ValueError(
            f"Unrecognized tlp_marking {tlp_marking!r}. Expected one of: "
            f"{', '.join(_TLP_MARKINGS)} (see OpenCTI-connector.md §10c)."
        )
    return marking


class VsVulnscanEnrichmentConnector:
    """Enriches a triggered IP/Vulnerability entity with VulnScan scanner-level detail.

    Produces one Note per triggered entity (§7b's "additive, not overwriting" design), pinned
    per entity in connector state so re-enrichment updates that same Note rather than piling up
    duplicates.
    """

    def __init__(self, config: Optional[Config] = None, helper=None):
        """Build the connector, injecting `config`/`helper` for tests instead of the real thing."""
        self.config = config or Config()
        self.helper = helper or OpenCTIConnectorHelper(self.config.raw)
        self.repository = VulnScanEnrichmentRepository(self.config)

        self.author = mapping.build_author(self.config.author_name)
        self.marking = resolve_marking(self.config.tlp_marking)

        LOGGER.info(
            "VS VulnScan Enrichment connector initialized (is_local=%s)",
            self.config.is_local,
        )

    def process_message(self, data: Dict) -> str:
        """Entry point pycti's `listen()` calls once per "Enrich" trigger.

        `data` is pycti's own event dict (ListenQueue._data_handler) -- `entity_id`,
        `entity_type`, and `stix_entity` (already parsed from JSON) are what this connector
        needs; `work_id`/error reporting back to OpenCTI are handled entirely by pycti itself
        around this call (it catches whatever this raises and marks the work as errored, so
        there's no need to catch-and-report manually here the way A/D's run() does for its own
        top-level state-corruption concern -- a single bad entity has no shared state to
        protect, unlike a wholesale poll).
        """
        entity_id = data["entity_id"]
        entity_type = data.get("entity_type")
        stix_entity = data.get("stix_entity") or {}

        vuln_scans = self._lookup(entity_type, stix_entity).vuln_scans

        # §9 queue discipline, same instinct as connector A's revocation-only-run: nothing found
        # means nothing worth putting on the queue. A permanent "nothing found" Note attached to
        # the entity would just be clutter in OpenCTI's UI, not a useful artifact -- the status
        # message returned below (visible in the work's own history for this Enrich click) is
        # where "we checked and found nothing" belongs, not a persistent object on the entity.
        if not vuln_scans:
            message = f"No VS scanner-level detail found for {entity_id}"
            self.helper.connector_logger.info(message)
            return message

        state = self.helper.get_state() or {}
        note_map = state.setdefault("note_ids", {})
        note = mapping.build_note(
            entity_id,
            vuln_scans,
            self.author.id,
            self.marking.id,
            existing_id=note_map.get(entity_id),
        )
        note_map[entity_id] = note.id
        self.helper.set_state(state)

        objects = mapping.dedupe_bundle_objects([self.author, self.marking, note])
        bundle = self.helper.stix2_create_bundle(objects)
        # work_id defaults to self.helper.work_id, which pycti already set before calling this
        # method -- no need to pass it explicitly (confirmed against the installed pycti source).
        self.helper.send_stix2_bundle(bundle, update=True)

        message = f"Enriched {entity_id} with {len(vuln_scans)} VS scanner finding(s)"
        self.helper.connector_logger.info(message)
        return message

    def _lookup(self, entity_type: Optional[str], stix_entity: Dict):
        """Resolve the triggered entity to a lookup key and query VulnScan for it.

        Raises for anything outside CONNECTOR_SCOPE (§7b) rather than silently returning nothing
        -- a scope mismatch is a configuration problem worth surfacing via the work's error
        state, not swallowing.
        """
        if entity_type in _IP_TYPES:
            ip_string = stix_entity.get("value")
            if not ip_string:
                raise ValueError(f"IP entity has no usable 'value': {stix_entity!r}")
            return self.repository.fetch_by_ip(ip_string)
        if entity_type == _VULNERABILITY_TYPE:
            cve_string = stix_entity.get("name")
            if not cve_string:
                raise ValueError(
                    f"Vulnerability entity has no usable 'name': {stix_entity!r}"
                )
            return self.repository.fetch_by_cve(cve_string)
        raise ValueError(
            f"Unexpected entity_type {entity_type!r} -- outside this connector's "
            f"CONNECTOR_SCOPE ({', '.join(sorted(_IP_TYPES | {_VULNERABILITY_TYPE}))})"
        )
