"""Orchestration for the VS Port/Service Inventory connector (OpenCTI-connector.md §7c).

Depends on connector D (org Identity must exist) -- independent of connectors A/B otherwise.

**Revised (2026-08-31): watermark-windowed polling, matching connector A's shape.** The original
version of this connector polled the *entire* in-scope `LatestPortScan` table every run, because
`mark_stale_latest_port_scans()` flips `current` to `False` without ever touching `time_scanned`
(verified directly against that function's source -- see db.py) -- a plain `WHERE time_scanned >
watermark` poll can't see that transition. That turned out to be too expensive against the real
table size (a plain aggregate query against it timed out even in a Lambda, 2026-08-31).

The fix isn't a bigger row cap, it's not needing a query to observe that transition at all:
`_run_aging_sweep()` below applies the *exact same* staleness rule
(`time_scanned` older than `config.latest_port_scan_cutoff_days`) locally, against connector
state, on every run -- independent of whatever this run's DB query happened to return. That turns
this back into an ordinary watermark poll (`db.py`'s `since_last_seen`/`include_current`, the
same shape as connector A's `since_last_seen`/`include_stale_open`), with staleness detection
handled entirely in-process instead of by re-reading the source.
"""

# Standard Python Libraries
import datetime
import logging
from typing import Dict, List, Optional

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
    """Polls an incremental window of LatestPortScan and locally ages out stale entries.

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

        # is_first_run gates the bootstrap `include_current` fetch -- the same role
        # is_first_run/include_stale_open play in connector A's run(), applied to this table's
        # own "don't permanently miss something currently active" case.
        since = state.get("last_seen_watermark")
        is_first_run = since is None

        try:
            data = self.repository.fetch(
                since_last_seen=since, include_current=is_first_run
            )
            new_watermark = self._process(data, state)
        except Exception as e:  # pylint: disable=broad-except
            # §10e/§10i: don't let one bad run corrupt state. connector_logger is pycti's
            # AppLogger, not a stdlib logging.Logger -- (message, meta=None) only.
            self.helper.connector_logger.error(
                "VS Port Inventory run failed", meta={"error": str(e)}
            )
            return

        if new_watermark is not None:
            state["last_seen_watermark"] = new_watermark
        # Persisted regardless of whether the watermark advanced -- the aging sweep can mutate
        # state (marking something locally stale) even on a run that fetched nothing new.
        self.helper.set_state(state)
        self.helper.connector_logger.info("VS Port Inventory run complete")

    # ------------------------------------------------------------------

    def _process(self, data: PortInventoryData, state: Dict) -> Optional[str]:
        """Process this run's fetched window, then age out anything state alone says is stale.

        `state["port_scan_state"]` is only ever added to or updated for keys actually seen this
        run, or found stale by the aging sweep -- never wholesale-replaced -- so a partial or
        empty poll (a transient DB issue, or a deliberately narrowed org scope) can't silently
        erase previously-recorded history for keys it simply didn't touch. A key that vanishes
        from the source entirely (as opposed to aging past the cutoff, which this connector now
        detects on its own) is a known, documented gap -- see README.md "Known gaps," same
        category as connector B's un-revoked stale Note.

        Returns the new watermark to persist (max `time_scanned` actually fetched this run), or
        None if nothing was fetched -- mirrors connector A's watermark contract exactly.
        """
        objects: List = [self.author, self.marking]
        port_scan_state = state.setdefault("port_scan_state", {})
        org_ip_rel_map = state.setdefault("org_ip_relationship_ids", {})
        run_time = datetime.datetime.now(datetime.timezone.utc)

        seen_keys = set()
        # §10e/§10i: one bad row must not sink the whole run -- built in from the start.
        for row in data.port_scans:
            key = self._key(row)
            seen_keys.add(key)
            try:
                self._process_row(
                    row, key, port_scan_state, org_ip_rel_map, run_time, objects
                )
            except Exception as e:  # pylint: disable=broad-except
                self.helper.connector_logger.warning(f"Skipping port scan {key!r}: {e}")
                continue

        self._run_aging_sweep(port_scan_state, seen_keys, run_time, objects)

        # §9 queue discipline: a poll where nothing actually changed for any row has nothing
        # new to send -- author+marking alone shouldn't hit the queue.
        if len(objects) > 2:
            objects = mapping.dedupe_bundle_objects(objects)
            bundle = self.helper.stix2_create_bundle(objects)
            self.helper.send_stix2_bundle(bundle, update=True)
            self.helper.connector_logger.info(
                f"Sent {len(objects)} objects ({len(data.port_scans)} port scans fetched this run)"
            )
        else:
            self.helper.connector_logger.info(
                f"Nothing changed ({len(data.port_scans)} port scans fetched this run)"
            )

        return self._compute_watermark(data.port_scans)

    def _process_row(
        self, row, key, port_scan_state, org_ip_rel_map, run_time, objects
    ) -> None:
        """Map, diff, and (if changed) queue one freshly-fetched LatestPortScan row's objects."""
        time_scanned = row.get("time_scanned")
        if not time_scanned:
            raise ValueError("LatestPortScan row has no time_scanned")

        org_id = mapping.resolve_org_identity_id(row["organization_name"])
        ip_obj = mapping.map_ip_observable(row["ip_string"])
        nt_obj = mapping.build_network_traffic(row, ip_obj.id)

        prev = port_scan_state.get(key)
        # Locally computed, deliberately ignoring row["current"] -- see module docstring. Using
        # our own rule uniformly (whether a row was just fetched or aged between polls) means a
        # bootstrap-caught row that already looks stale by our own clock behaves identically to
        # one the aging sweep would catch next run, rather than two different sources of truth.
        is_current = self._is_within_cutoff(time_scanned, run_time)
        start_time, stop_time = self._resolve_lifecycle(prev, row, is_current, run_time)

        labels = mapping.lifecycle_labels(row)
        external_id = mapping.lifecycle_external_id(row)
        lifecycle_rel = mapping.build_lifecycle_relationship_from_parts(
            org_id,
            nt_obj.id,
            self.author.id,
            self.marking.id,
            start_time=start_time,
            stop_time=stop_time,
            labels=labels,
            external_id=external_id,
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
            "network_traffic_id": nt_obj.id,
            "org_id": org_id,
            "labels": labels,
            "external_id": external_id,
            "start_time": _serialize(start_time),
            "stop_time": _serialize(stop_time),
            "current": is_current,
            "time_scanned": _serialize(mapping.normalize_timestamp(time_scanned)),
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
                "labels",
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

    def _run_aging_sweep(self, port_scan_state, seen_keys, run_time, objects) -> None:
        """Locally close out anything state alone says has aged past the cutoff.

        The whole point of this connector's redesign (see module docstring): no DB query here,
        just the same rule `mark_stale_latest_port_scans()` applies, evaluated against what
        connector state already knows. Only ever touches entries this run's fetch didn't already
        update -- a freshly-fetched row's own currency was already decided in _process_row().
        """
        for key, entry in port_scan_state.items():
            if key in seen_keys or not entry.get("current"):
                continue
            last_scanned = mapping.normalize_timestamp(entry.get("time_scanned"))
            if last_scanned is None:
                continue  # defensive -- don't let one malformed entry crash the whole sweep
            if run_time - last_scanned < datetime.timedelta(
                days=self.config.latest_port_scan_cutoff_days
            ):
                continue
            self._close_locally(key, entry, run_time, objects)

    def _close_locally(self, key, entry, run_time, objects) -> None:
        """Build an updated lifecycle relationship for one aged-out entry, from state alone."""
        rel = mapping.build_lifecycle_relationship_from_parts(
            entry["org_id"],
            entry["network_traffic_id"],
            self.author.id,
            self.marking.id,
            start_time=mapping.normalize_timestamp(entry.get("start_time")),
            stop_time=run_time,
            labels=entry.get("labels") or [],
            external_id=entry["external_id"],
            existing_id=entry["relationship_id"],
        )
        entry["current"] = False
        entry["stop_time"] = _serialize(run_time)
        objects.append(rel)
        self.helper.connector_logger.info(
            f"Marked {key!r} stale locally "
            f"(time_scanned aged past {self.config.latest_port_scan_cutoff_days}d cutoff)"
        )

    def _is_within_cutoff(self, time_scanned, run_time) -> bool:
        """Apply this connector's own copy of LATEST_PORT_SCAN_CUTOFF to a raw time_scanned value."""
        last_scanned = mapping.normalize_timestamp(time_scanned)
        return (run_time - last_scanned) < datetime.timedelta(
            days=self.config.latest_port_scan_cutoff_days
        )

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
    def _compute_watermark(port_scans) -> Optional[str]:
        """Compute the max time_scanned across everything actually fetched this run.

        Connector A's exact watermark contract, just a single timestamp column instead of a
        COALESCE of two.
        """
        values = [
            mapping.normalize_timestamp(row.get("time_scanned")) for row in port_scans
        ]
        watermark = max((v for v in values if v is not None), default=None)
        return _serialize(watermark)

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
