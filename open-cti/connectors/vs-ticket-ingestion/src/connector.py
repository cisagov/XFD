"""Orchestration for the VS Ticket Ingestion connector (OpenCTI-connector.md §7a).

Depends on connector D (§7d/§8) -- the organization Identity a ticket resolves to (§7a's "look
up, don't blindly create") must already exist. Deploy order: D, then this one.

Builds proactively on every lesson connector D's live debugging surfaced (§10i), rather than
rediscovering the same bug classes: AppLogger call signatures, row-level error isolation from
day one, the `IS NULL OR` unscoped-query guard, and the datetime/JSON watermark gotcha are all
already accounted for below and in db.py -- not patched in after a crash this time.
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
from .db import TicketIngestionData, VsTicketIngestionRepository

LOGGER = logging.getLogger("vs_ticket_ingestion")

# Same well-known TLP marking-definition ids as connector D -- see its connector.py for why
# TLP:CLEAR/TLP:WHITE share one object (this stix2 version only ships the pre-2.1 name).
_TLP_MARKINGS = {
    "TLP:CLEAR": stix2.TLP_WHITE,
    "TLP:WHITE": stix2.TLP_WHITE,
    "TLP:GREEN": stix2.TLP_GREEN,
    "TLP:AMBER": stix2.TLP_AMBER,
    "TLP:RED": stix2.TLP_RED,
}


def resolve_marking(tlp_marking: str) -> stix2.MarkingDefinition:
    """Resolve a TLP string to its well-known marking-definition object. Identical to connector D."""
    marking = _TLP_MARKINGS.get(tlp_marking.strip().upper())
    if marking is None:
        raise ValueError(
            f"Unrecognized tlp_marking {tlp_marking!r}. Expected one of: "
            f"{', '.join(_TLP_MARKINGS)} (see OpenCTI-connector.md §10c)."
        )
    return marking


class VsTicketIngestionConnector:
    """Polls Ticket data from mini_data_lake and upserts it into OpenCTI.

    Produces IPv4-Addr/IPv6-Addr and Vulnerability objects plus the relationship carrying each
    ticket's open/closed lifecycle -- no Case/Incident container (§7a).
    """

    def __init__(self, config: Optional[Config] = None, helper=None):
        """Build the connector, injecting `config`/`helper` for tests instead of the real thing."""
        self.config = config or Config()
        self.helper = helper or OpenCTIConnectorHelper(self.config.raw)
        self.repository = VsTicketIngestionRepository(self.config)

        self.author = mapping.build_author(self.config.author_name)
        self.marking = resolve_marking(self.config.tlp_marking)

        LOGGER.info(
            "VS Ticket Ingestion connector initialized (is_local=%s, org_allowlist=%s)",
            self.config.is_local,
            self.config.org_acronym_allowlist or "<unscoped>",
        )

    def run(self) -> None:
        """Entry point pycti's scheduler calls each duration_period tick."""
        self.helper.connector_logger.info("Starting VS Ticket Ingestion run")
        state = self.helper.get_state() or {}

        since_last_seen = self._effective_since(state)
        try:
            data = self.repository.fetch(since_last_seen=since_last_seen)
            new_watermark = self._process(data, state)
        except Exception as e:  # pylint: disable=broad-except
            # §10e/§10i: don't let one bad run corrupt state -- log and let the next scheduled
            # tick retry from the last confirmed watermark. connector_logger is pycti's AppLogger,
            # not a stdlib logging.Logger -- (message, meta=None) only, no exc_info kwarg (it
            # captures the traceback internally regardless). Got this right from the start here;
            # connector D only found it by crashing on a live run.
            self.helper.connector_logger.error(
                "VS Ticket Ingestion run failed", meta={"error": str(e)}
            )
            return

        # §10f: only advance the watermark once the run has actually completed -- new_watermark
        # is None (unchanged) whenever there was nothing to process.
        if new_watermark is not None:
            state["last_seen_watermark"] = new_watermark
            self.helper.set_state(state)

        self.helper.connector_logger.info("VS Ticket Ingestion run complete")

    def _effective_since(self, state: Dict) -> Optional[str]:
        """Compute the `since_last_seen` to actually poll from -- watermark, lookback bound, or none.

        §9c's "lookback override" lever, finally built: bounds the *first* poll against a
        fresh/reset connector state to the last `lookback_days` days, instead of every ticket
        ever recorded for the scoped orgs -- the thing that makes an org with years of history
        slow to iterate against during dev, and the exact scenario the doc called out ("matters
        especially the first time a fresh connector state points at a real environment").

        Deliberately only kicks in when there is no watermark yet. Once a real incremental poll is
        underway, clamping `since` to a rolling lookback window on every run would silently create
        a permanent gap -- a ticket whose last-seen timestamp never moves again (e.g. opened long
        ago, still open, nothing about it has changed since) would fall outside the window and
        then never be picked up again, since the watermark only ever advances forward from here.
        That's a real completeness cost, not just a delay, which is why `lookback_days` defaults
        to unset/None (§10c's same fail-closed instinct: don't silently start skipping data) and
        why this only ever touches the *first* poll, never an in-progress one.
        """
        watermark = state.get("last_seen_watermark")
        if watermark is not None or self.config.lookback_days is None:
            return watermark
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=self.config.lookback_days
        )
        self.helper.connector_logger.info(
            f"No watermark yet -- bounding this first poll to the last "
            f"{self.config.lookback_days} day(s) (VS_TICKET_INGESTION_LOOKBACK_DAYS)"
        )
        return since.isoformat()

    # ------------------------------------------------------------------

    def _process(self, data: TicketIngestionData, state: Dict) -> Optional[str]:
        """Build and send this run's STIX bundle, and revoke any newly-false-positive tickets.

        Returns the new watermark value to persist, or None if there was nothing seen this run
        (so run() leaves state untouched).
        """
        if not data.tickets:
            self.helper.connector_logger.info("No tickets in scope for this run")
            return None

        objects = [self.author, self.marking]
        rel_map = state.setdefault("ticket_relationship_ids", {})
        org_ip_rel_map = state.setdefault("org_ip_relationship_ids", {})

        # §10e/§10i: one bad row must not sink the whole run -- built in from the start this
        # time, not added after a live crash the way connector D's CIDR loop needed to be.
        for ticket in data.tickets:
            ticket_id = ticket.get("id")
            try:
                if ticket.get("false_positive"):
                    self._revoke_if_known(rel_map, ticket_id)
                    continue

                # Looked up, not created (§7a) -- connector D owns Identity(class="organization").
                org_id = mapping.resolve_org_identity_id(ticket["organization_name"])
                ip_obj = mapping.map_ip_observable(ticket["ip_string"])
                vuln_obj = mapping.map_vulnerability(ticket)
                ticket_relationship = mapping.build_ticket_relationship(
                    ticket,
                    ip_obj.id,
                    vuln_obj.id,
                    self.author.id,
                    self.marking.id,
                    existing_id=rel_map.get(ticket_id),
                )
                org_ip_key = f"{org_id}:{ip_obj.id}"
                org_ip_relationship = mapping.build_org_owns_ip(
                    org_id,
                    ip_obj.id,
                    self.author.id,
                    self.marking.id,
                    existing_id=org_ip_rel_map.get(org_ip_key),
                )
            except Exception as e:  # pylint: disable=broad-except
                self.helper.connector_logger.warning(
                    f"Skipping ticket {ticket_id!r}: {e}"
                )
                continue

            rel_map[ticket_id] = ticket_relationship.id
            org_ip_rel_map[org_ip_key] = org_ip_relationship.id
            objects.append(ip_obj)
            objects.append(vuln_obj)
            objects.append(ticket_relationship)
            objects.append(org_ip_relationship)

        # §9 queue discipline: a run that only revoked false positives has nothing new to send --
        # don't put an author+marking-only bundle on the queue for no reason.
        if len(objects) > 2:
            objects = mapping.dedupe_bundle_objects(objects)
            bundle = self.helper.stix2_create_bundle(objects)
            self.helper.send_stix2_bundle(bundle, update=True)
            self.helper.connector_logger.info(
                f"Sent {len(objects)} objects ({len(data.tickets)} tickets seen this run)"
            )
        else:
            self.helper.connector_logger.info(
                f"Nothing new to send ({len(data.tickets)} tickets seen this run, "
                "all false-positive/skipped)"
            )

        return self._compute_watermark(data.tickets)

    def _revoke_if_known(self, rel_map: Dict, ticket_id: Optional[str]) -> None:
        """Revoke a ticket's relationship if we ever sent one, now that it's false_positive.

        §7a: leaving a stale "still vulnerable" edge in the graph is worse than doing nothing, but
        a ticket that was *never* ingested (rel_map has no entry) needs no action either way.
        Deletion goes through the OpenCTI API directly, not the STIX bundle -- send_stix2_bundle()
        upserts by id, it has no delete primitive; this is why revocation needs
        `helper.api.stix_core_relationship.delete()` instead (confirmed against the installed
        pycti version's stix_core_relationship API entity).

        `ticket_id` is Optional only because `dict.get("id")` types that way -- Ticket.id is a
        non-nullable primary key in practice, so a `None` here means a malformed row, not a real
        ticket; nothing to revoke either way, same outcome as "never ingested."
        """
        if ticket_id is None:
            return
        rel_id = rel_map.pop(ticket_id, None)
        if rel_id is None:
            return
        self.helper.api.stix_core_relationship.delete(id=rel_id)
        self.helper.connector_logger.info(
            f"Revoked relationship for ticket {ticket_id!r} (now false_positive)"
        )

    @staticmethod
    def _compute_watermark(tickets) -> Optional[str]:
        """COALESCE(closed_timestamp, updated_timestamp), computed in Python over every ticket seen.

        Uses every fetched row, not just the ones that produced STIX objects -- skipped and
        revoked tickets still need to move the watermark past them, exactly like connector D takes
        the max across every organization row regardless of whether it emitted a CIDR.

        Same live-vs-fixture type gap as connector D's watermark (§10i): psycopg2 hands back a
        real datetime.datetime for these timestamptz columns, but pycti's set_state() does a plain
        json.dumps() with no datetime support. isinstance, not hasattr, for the same mypy
        narrowing reason documented in connector D's connector.py.
        """
        last_seen_values = [
            mapping.normalize_timestamp(t.get("closed_timestamp"))
            or mapping.normalize_timestamp(t.get("updated_timestamp"))
            for t in tickets
        ]
        watermark = max((v for v in last_seen_values if v is not None), default=None)
        return (
            watermark.isoformat()
            if isinstance(watermark, datetime.datetime)
            else watermark
        )
