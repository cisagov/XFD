"""Orchestration for the VS Port/Service Inventory connector (OpenCTI-connector.md §7c).

Depends on connector D (org Identity must exist) -- independent of connectors A/B otherwise
(§8's build order lists this last only because it was scaffolded last, not because it has any
runtime dependency on them).

Structurally different from connector A in the one way that matters most here (§7c): no
timestamp watermark. `mark_stale_latest_port_scans()` flips `current` to `False` without
touching `time_scanned` (verified directly against that function's source -- see db.py), so a
`WHERE time_scanned > watermark` poll would never see a port going stale. This connector instead
polls the *entire* in-scope `LatestPortScan` table every run and diffs it against a
`(org, ip, port, protocol) -> last-known-state` map kept in connector state -- closer to a
reconciliation loop than to connectors A/D's incremental polls.
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
from .db import PortInventoryData, VsPortInventoryRepository

LOGGER = logging.getLogger("vs_port_inventory")

# Same well-known TLP marking-definition ids as connectors A/B/D.
_TLP_MARKINGS = {
    "TLP:CLEAR": stix2.TLP_WHITE,
    "TLP:WHITE": stix2.TLP_WHITE,
    "TLP:GREEN": stix2.TLP_GREEN,
    "TLP:AMBER": stix2.TLP_AMBER,
    "TLP:RED": stix2.TLP_RED,
}


def resolve_marking(tlp_marking: str) -> stix2.MarkingDefinition:
    """Resolve a TLP string to its well-known marking-definition object. Identical to A/B/D."""
    marking = _TLP_MARKINGS.get(tlp_marking.strip().upper())
    if marking is None:
        raise ValueError(
            f"Unrecognized tlp_marking {tlp_marking!r}. Expected one of: "
            f"{', '.join(_TLP_MARKINGS)} (see OpenCTI-connector.md §10c)."
        )
    return marking


class VsPortInventoryConnector:
    """Polls the full in-scope LatestPortScan table and reconciles it against connector state.

    Produces IPv4-Addr/IPv6-Addr, Network-Traffic, and (when present) Software objects, plus the
    relationships tying them to their owning org -- with the port's open/stale lifecycle carried
    on a pinned relationship, never on the Network-Traffic SCO itself (see mapping.py).
    """

    def __init__(self, config: Optional[Config] = None, helper=None):
        """Build the connector, injecting `config`/`helper` for tests instead of the real thing."""
        self.config = config or Config()
        self.helper = helper or OpenCTIConnectorHelper(self.config.raw)
        self.repository = VsPortInventoryRepository(self.config)

        self.author = mapping.build_author(self.config.author_name)
        self.marking = resolve_marking(self.config.tlp_marking)

        LOGGER.info(
            "VS Port Inventory connector initialized (is_local=%s, org_allowlist=%s)",
            self.config.is_local,
            self.config.org_acronym_allowlist or "<unscoped>",
        )

    def run(self) -> None:
        """Entry point pycti's scheduler calls each duration_period tick."""
        self.helper.connector_logger.info("Starting VS Port Inventory run")
        state = self.helper.get_state() or {}

        try:
            data = self.repository.fetch()
            self._process(data, state)
        except Exception as e:  # pylint: disable=broad-except
            # §10e/§10i: don't let one bad run corrupt state. connector_logger is pycti's
            # AppLogger, not a stdlib logging.Logger -- (message, meta=None) only.
            self.helper.connector_logger.error(
                "VS Port Inventory run failed", meta={"error": str(e)}
            )
            return

        # Unlike connectors A/D's watermark, this connector's state *is* the reconciliation map
        # itself -- it needs persisting after every successful poll, not just when "something
        # changed," since next run's diff depends on having seen this run's full picture.
        self.helper.set_state(state)
        self.helper.connector_logger.info("VS Port Inventory run complete")

    # ------------------------------------------------------------------

    def _process(self, data: PortInventoryData, state: Dict) -> None:
        """Diff this run's full poll against state and send only what actually changed.

        `state["port_scan_state"]` is only ever added to or updated for keys actually seen this
        run -- never wholesale-replaced -- so a partial or empty poll (a transient DB issue, or
        a deliberately narrowed org scope) can't silently erase previously-recorded history for
        keys it simply didn't touch. A key that vanishes from the source entirely (as opposed to
        flipping `current=False`, which the source *does* signal) is a known, documented gap --
        see README.md "Known gaps," same category as connector B's un-revoked stale Note.
        """
        if not data.port_scans:
            self.helper.connector_logger.info("No port scans in scope for this run")
            return

        objects = [self.author, self.marking]
        port_scan_state = state.setdefault("port_scan_state", {})
        org_ip_rel_map = state.setdefault("org_ip_relationship_ids", {})
        run_time = datetime.datetime.now(datetime.timezone.utc)

        # §10e/§10i: one bad row must not sink the whole run -- built in from the start.
        for row in data.port_scans:
            key = self._key(row)
            try:
                self._process_row(
                    row, key, port_scan_state, org_ip_rel_map, run_time, objects
                )
            except Exception as e:  # pylint: disable=broad-except
                self.helper.connector_logger.warning(f"Skipping port scan {key!r}: {e}")
                continue

        # §9 queue discipline: a poll where nothing actually changed for any row has nothing
        # new to send -- author+marking alone shouldn't hit the queue.
        if len(objects) > 2:
            objects = mapping.dedupe_bundle_objects(objects)
            bundle = self.helper.stix2_create_bundle(objects)
            self.helper.send_stix2_bundle(bundle, update=True)
            self.helper.connector_logger.info(
                f"Sent {len(objects)} objects ({len(data.port_scans)} port scans seen this run)"
            )
        else:
            self.helper.connector_logger.info(
                f"Nothing changed ({len(data.port_scans)} port scans seen this run)"
            )

    def _process_row(
        self, row, key, port_scan_state, org_ip_rel_map, run_time, objects
    ) -> None:
        """Map, diff, and (if changed) queue one LatestPortScan row's objects."""
        org_id = mapping.resolve_org_identity_id(row["organization_name"])
        ip_obj = mapping.map_ip_observable(row["ip_string"])
        nt_obj = mapping.build_network_traffic(row, ip_obj.id)

        prev = port_scan_state.get(key)
        is_current = bool(row.get("current"))
        start_time, stop_time = self._resolve_lifecycle(prev, row, is_current, run_time)

        lifecycle_rel = mapping.build_lifecycle_relationship(
            row,
            org_id,
            nt_obj.id,
            self.author.id,
            self.marking.id,
            start_time=start_time,
            stop_time=stop_time,
            existing_id=(prev or {}).get("relationship_id"),
        )

        org_ip_key = f"{org_id}:{ip_obj.id}"
        org_ip_rel = mapping.build_org_owns_ip(
            org_id,
            ip_obj.id,
            self.author.id,
            self.marking.id,
            existing_id=org_ip_rel_map.get(org_ip_key),
        )
        org_ip_rel_map[org_ip_key] = org_ip_rel.id

        software_obj = mapping.build_software(row)
        software_rel = None
        if software_obj is not None:
            software_rel = mapping.build_software_relationship(
                nt_obj.id,
                software_obj.id,
                self.author.id,
                self.marking.id,
                existing_id=(prev or {}).get("software_relationship_id"),
            )

        new_state = {
            "relationship_id": lifecycle_rel.id,
            "start_time": _serialize(start_time),
            "stop_time": _serialize(stop_time),
            "current": is_current,
            "service_name": row.get("service_name"),
            "software_relationship_id": software_rel.id if software_rel else None,
        }
        changed = prev is None or any(
            prev.get(field) != new_state[field]
            for field in (
                "current",
                "service_name",
                "software_relationship_id",
                "stop_time",
            )
        )
        port_scan_state[key] = new_state

        if changed:
            objects.append(ip_obj)
            objects.append(nt_obj)
            objects.append(lifecycle_rel)
            objects.append(org_ip_rel)
            if software_obj is not None:
                objects.append(software_obj)
                objects.append(software_rel)

    @staticmethod
    def _resolve_lifecycle(prev, row, is_current, run_time):
        """§7c: preserve start_time once set; pin stop_time at first-observed-closed, not later.

        A port that reopens after being marked stale clears its stop_time (the same relationship
        goes active again) but keeps its *original* start_time -- resetting start_time on reopen
        would overstate how novel that exposure is. Not explicitly spelled out in the design doc;
        a documented judgment call, consistent with how "preserve start_time, never overwrite"
        is stated there for the first-seen case.
        """
        if prev is None:
            start_time = (
                mapping.normalize_timestamp(row.get("time_scanned")) or run_time
            )
            stop_time = None if is_current else run_time
        else:
            start_time = mapping.normalize_timestamp(prev.get("start_time"))
            if is_current:
                stop_time = None
            else:
                stop_time = (
                    mapping.normalize_timestamp(prev["stop_time"])
                    if prev.get("stop_time")
                    else run_time
                )
        return start_time, stop_time

    @staticmethod
    def _key(row: Dict) -> str:
        """Build the reconciliation key this connector diffs on: (org, ip, port, protocol)."""
        return (
            f"{row.get('organization_acronym')}:{row.get('ip_string')}:"
            f"{row.get('port')}:{row.get('protocol')}"
        )


def _serialize(value) -> Optional[str]:
    """isoformat() a datetime for JSON-safe state storage; pass through None/strings as-is.

    Same live-vs-fixture type gap as connectors A/D's watermark serialization (§10i):
    psycopg2/normalize_timestamp hand back real datetime.datetime objects, but pycti's
    set_state() does a plain json.dumps() with no datetime support. isinstance, not hasattr --
    same mypy-narrowing reason documented in connector A's connector.py.
    """
    return value.isoformat() if isinstance(value, datetime.datetime) else value
