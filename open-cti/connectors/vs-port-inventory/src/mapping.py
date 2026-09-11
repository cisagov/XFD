"""Pure row -> STIX mapping functions for the VS Port/Service Inventory connector.

Deliberately dependency-free beyond stix2/pycti and the standard library -- no DB, no OpenCTI
API, no network. This is "Loop 1" from OpenCTI-connector.md §9b. See tests/test_mapping.py.

STIX mapping decisions here are documented in OpenCTI-connector.md §7c. The idempotency pattern
(§10a) applies to the lifecycle relationship the same way it did for connectors A/D -- but this
connector also had to verify, and steer clear of, a *third* instance of the same underlying bug
class: putting `start`/`end` directly on the `NetworkTraffic` SCO itself. Verified directly
against the installed stix2 library that `start`/`end` are among `NetworkTraffic`'s own
ID-contributing properties -- two NetworkTraffic objects built with the same
src_ref/src_port/protocols but *different* `start` values get *different* ids. Putting the
lifecycle there instead of on a separate, pinned relationship would have fragmented one port's
history into a new SCO every time it changed, not updated one object in place -- so the
NetworkTraffic SCO here is built from stable fields only, and the lifecycle lives entirely on
`build_lifecycle_relationship()`/`build_lifecycle_relationship_from_parts()`, pinned in connector
state exactly like connectors A/D already do.

Revised (2026-08-31, see db.py's module docstring): connector.py now computes port staleness
locally from `time_scanned` + a known cutoff, rather than re-polling for it, which means it
sometimes needs to build an updated lifecycle relationship with no fresh DB row on hand --
`build_lifecycle_relationship_from_parts()` exists for exactly that case.

Revised (2026-09-02): the Network-Traffic SCO carries a service/state summary readable straight
off the observable, without following the relationship to the org for it -- but **not** via
`x_opencti_service`/`x_opencti_open` custom properties, as an earlier version of this file tried.
Verified directly against this platform's real GraphQL schema (`__type(name: "NetworkTraffic")`)
that those two keys aren't recognized fields at all -- OpenCTI's Network-Traffic schema only
knows a fixed set of `x_opencti_*` keys (`x_opencti_stix_ids`, `x_opencti_modified_at`,
`x_opencti_inferences`, `x_opencti_score`, `x_opencti_description`), so anything else gets
silently dropped on ingest. Confirmed with a real, throwaway bundle sent through a live instance
and read back via GraphQL: `x_opencti_description` survives (already relied on below), an
unrecognized `x_opencti_*` key does not, and a bare (non-`x_opencti_`-prefixed) `labels` custom
property *does* land as `objectLabel` -- so that's what carries this connector's own
service/state summary now, the same mechanism `lifecycle_labels()` already uses on the
relationship, applied here to the SCO itself.

The state label is **not** this connector's locally-computed recency flag (`current`/
`is_within_cutoff`) -- an earlier version of this code conflated the two, which was wrong. It's
`LatestPortScan.state == "open"` (`is_port_state_open()` below), the scanner's own confirmed
finding for this exact port on its most recent scan (`models.py`'s help text: "State of the port,
as reported by the scanner; see nmap states" -- and the platform's own `PortScanSummary` rollup
treats it the same way, filtering `WHERE ps.state = 'open'`). `state` gets overwritten in place on
every rescan (`insert_port_scans_sql()`'s `ON CONFLICT ... DO UPDATE`), so a port that was open
and is later rescanned closed genuinely flips this label -- independent of whether that rescan
happened to also be within the freshness cutoff. Consequence: the aging sweep (connector.py, no
fresh row on hand) must never touch these labels -- going stale (unobserved for 14+ days) is not
evidence a port closed, just that its last-known state is unconfirmed by anything more recent.
"""

# Standard Python Libraries
import datetime
from ipaddress import ip_address
from typing import Dict, List, Optional

# Third-Party Libraries
from dateutil import parser as dateutil_parser
from pycti import Identity as OpenCTIIdentity
from pycti import StixCoreRelationship
import stix2

VS_EXTERNAL_SOURCE = "VS"


def build_author(name: str) -> stix2.Identity:
    """Build the single system Identity every VS-sourced object should cite as createdBy (§10c).

    Identical construction to connectors A/B/D's build_author() -- all four connectors'
    Identity(class="system") objects resolve to the one shared, content-derived author.
    """
    return stix2.Identity(
        id=OpenCTIIdentity.generate_id(name, "system"),
        name=name,
        identity_class="system",
    )


def resolve_org_identity_id(organization_name: str) -> str:
    """Resolve an organization's existing Identity id -- look up, don't blindly create (§7c).

    Identical reasoning to connector A's mapping.resolve_org_identity_id() -- connector D owns
    creating Identity(class="organization"); this recomputes the same content-derived id rather
    than a live API lookup per row, given this connector's own full-poll volume (§9c).
    """
    return OpenCTIIdentity.generate_id(organization_name, "organization")


def build_org_owns_ip(
    org_id: str,
    ip_observable_id: str,
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Org -> IP observable, built identically to connector A's equivalent mapping function.

    Deliberately identical -- same relationship_type/source/target/no-time-component means the
    same deterministic id, so this connector's and connector A's org->IP edges for the same
    (org, ip) pair collide into the *same* OpenCTI relationship rather than each connector
    creating its own separate copy of "this org is associated with this host."
    """
    rel_id = _relationship_id(
        "related-to", org_id, ip_observable_id, None, None, existing_id
    )
    return stix2.Relationship(
        id=rel_id,
        relationship_type="related-to",
        source_ref=org_id,
        target_ref=ip_observable_id,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
    )


def map_ip_observable(ip_string: str):
    """IP string -> IPv4Address/IPv6Address SCO.

    LatestPortScan.ip_string is a single scanned host's address, same shape as connector A's
    Ticket.ip_string -- ip_address(), not ip_network(). Raises ValueError on anything malformed;
    left to propagate so connector.py's per-row try/except (§10i) can skip just that one row.
    """
    parsed = ip_address(ip_string)
    if parsed.version == 4:
        return stix2.IPv4Address(value=ip_string)
    return stix2.IPv6Address(value=ip_string)


def normalize_timestamp(value):
    """Normalize a DateTimeField value, or a value read back from connector state, to a datetime.

    Same helper connector A's mapping.py already proved out, reused verbatim here rather than
    reinvented (§10i). Two distinct sources feed this: `LatestPortScan.time_scanned` (a real
    psycopg2 datetime on a live run, an ISO string in IS_LOCAL fixtures) *and* values read back
    out of connector state (always JSON strings, since state round-trips through
    pycti's set_state()/get_state()). Parsing every string through dateutil and always returning
    a real datetime object closes the `+00:00`-offset-string gap connector A found the hard way,
    for both sources at once rather than trusting either one to already be in a stix2-safe shape.
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime(
            value.year, value.month, value.day, tzinfo=datetime.timezone.utc
        )
    if isinstance(value, str):
        parsed = dateutil_parser.isoparse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed
    return value


def _normalize_protocol(protocol: Optional[str]) -> str:
    """Lower-case the scanned protocol for STIX's `protocols` list.

    LatestPortScan.protocol is documented as "'tcp' or 'udp'" (models.py) -- deliberately not
    validated against a fixed enum beyond that, since stix2's own StringProperty doesn't
    constrain `protocols` to a fixed vocabulary either. Raises on a missing value rather than
    guessing "tcp" -- a port scan with no protocol at all is a malformed row, not a default case.
    """
    if not protocol:
        raise ValueError("LatestPortScan row has no protocol")
    return protocol.strip().lower()


def is_port_state_open(state: Optional[str]) -> bool:
    """Reduce LatestPortScan.state (nmap-style: open/closed/filtered/...) to a plain boolean.

    Anything other than a literal "open" (case/whitespace-insensitive) -- closed, filtered,
    open|filtered, missing entirely -- reads as "not confirmed open". Feeds `network_traffic_labels()`
    below, not `current`/recency -- see module docstring for why those are different things.
    """
    return (state or "").strip().lower() == "open"


def _label_safe(value: str) -> str:
    """Normalize a raw value into a plain OpenCTI label token: lower-case, hyphenated."""
    return "-".join(value.strip().lower().split())


def network_traffic_labels(row: Dict) -> List[str]:
    """Compute this row's service/state summary as OpenCTI Labels on the SCO itself.

    Not `x_opencti_service`/`x_opencti_open` -- verified those aren't real fields on this
    platform's Network-Traffic schema and get silently dropped (see module docstring). `labels`
    (bare, not `x_opencti_`-prefixed) is the confirmed-working mechanism -- verified end-to-end
    against a real instance that it lands as `objectLabel`. `vs-state-<state>` mirrors the exact
    label `lifecycle_labels()` already puts on the relationship, for the same row; `vs-open` is
    an additional presence-only tag for a quick visual filter, since "is this thing open" is
    exactly the question this connector exists to answer.
    """
    labels: List[str] = []
    state = row.get("state")
    if state:
        labels.append(f"vs-state-{_label_safe(state)}")
    if is_port_state_open(state):
        labels.append("vs-open")
    service_name = row.get("service_name")
    if service_name:
        labels.append(f"vs-service-{_label_safe(service_name)}")
    return labels


def build_network_traffic(row: Dict, ip_observable_id: str) -> stix2.NetworkTraffic:
    """Build the Network-Traffic SCO for one (ip, port, protocol) row.

    Deliberately built from stable fields only -- see module docstring for why `start`/`end`/
    `is_active` never go here. `service_name` is often not a valid STIX protocol string (§7c), so
    it's carried as a custom property instead of crammed into `protocols`.
    """
    protocol = _normalize_protocol(row.get("protocol"))
    port = row.get("port")
    if not port:
        raise ValueError("LatestPortScan row has no port")
    # Verified against the installed stix2 library that custom_properties do not feed
    # NetworkTraffic's own id computation (unlike start/end) -- safe to vary between polls
    # without fragmenting the SCO the way start/end would have. This includes `labels` (verified
    # separately, end-to-end against a real instance, that it's a real accepted field for this
    # SCO type and not itself ID-contributing).
    custom_properties: Dict[str, object] = {}
    labels = network_traffic_labels(row)
    if labels:
        custom_properties["labels"] = labels
    service_name = row.get("service_name")
    if service_name:
        custom_properties["x_opencti_description"] = service_name
    return stix2.NetworkTraffic(
        src_ref=ip_observable_id,
        src_port=int(port),
        protocols=[protocol],
        custom_properties=custom_properties,
    )


def build_software(row: Dict) -> Optional[stix2.Software]:
    """Build a Software SCO when the row actually has product/version/cpe detail.

    Content-derived id is the *correct* behavior here, unlike NetworkTraffic's lifecycle -- a
    different product/version genuinely is a different Software entity, not an update to the
    same one, so no pinning is needed (same reasoning as connector D's IPv4-Addr/IPv6-Addr reuse:
    SCOs with real ID Contributing Properties don't need §10a's pinning pattern at all).
    """
    if not (
        row.get("service_product")
        or row.get("service_version")
        or row.get("service_cpe")
    ):
        return None
    return stix2.Software(
        name=row.get("service_product") or row.get("service_name") or "unknown",
        version=row.get("service_version"),
        cpe=row.get("service_cpe"),
    )


def _relationship_id(
    relationship_type: str,
    source_ref: str,
    target_ref: str,
    start_time,
    stop_time,
    existing_id: Optional[str],
) -> str:
    """Apply the §10a idempotency pattern -- identical reasoning to connectors A/D's mapping.py."""
    if existing_id:
        return existing_id
    return StixCoreRelationship.generate_id(
        relationship_type, source_ref, target_ref, start_time, stop_time
    )


def lifecycle_labels(row: Dict) -> List[str]:
    """Compute this row's labels once, so connector state can cache and reuse them.

    Needed for the state-only relationship rebuild in build_lifecycle_relationship_from_parts()
    when there's no fresh row on hand.
    """
    labels: List[str] = []
    if row.get("source"):
        labels.append(f"vs-source-{row['source']}")
    if row.get("risky_service_group"):
        labels.append(f"vs-risky-service-{row['risky_service_group']}")
    if row.get("nmi_service_group"):
        labels.append(f"vs-nmi-service-{row['nmi_service_group']}")
    if row.get("state"):
        labels.append(f"vs-state-{row['state']}")
    return labels


def lifecycle_external_id(row: Dict) -> str:
    """Return the bookkeeping id carried on the lifecycle relationship's External Reference."""
    return row.get("port_scan_id") or row["id"]


def build_lifecycle_relationship_from_parts(
    org_id: str,
    network_traffic_id: str,
    author_id: str,
    marking_id: str,
    start_time,
    stop_time,
    labels: List[str],
    external_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Build the org -> Network-Traffic lifecycle relationship from already-resolved parts.

    The lower-level builder both `build_lifecycle_relationship()` (fresh row on hand) and
    connector.py's locally-computed staleness sweep (no fresh row -- state only, see db.py's
    module docstring for why that's a real, deliberate case now) share. `start_time`/`stop_time`
    are passed in already-resolved, not computed here -- §10a's idempotency depends on connector
    state (what was recorded last run), which this dependency-free module deliberately has no
    access to.
    """
    rel_id = _relationship_id(
        "related-to", org_id, network_traffic_id, start_time, stop_time, existing_id
    )
    return stix2.Relationship(
        id=rel_id,
        relationship_type="related-to",
        source_ref=org_id,
        target_ref=network_traffic_id,
        start_time=start_time,
        stop_time=stop_time,
        labels=labels or None,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
        external_references=[
            stix2.ExternalReference(
                source_name=VS_EXTERNAL_SOURCE, external_id=external_id
            )
        ],
    )


def build_lifecycle_relationship(
    row: Dict,
    org_id: str,
    network_traffic_id: str,
    author_id: str,
    marking_id: str,
    start_time,
    stop_time,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Build the org -> Network-Traffic relationship carrying this port's open/stale lifecycle.

    Thin wrapper around build_lifecycle_relationship_from_parts() for the common case: a fresh
    row is on hand, so labels/external_id are computed from it directly.
    """
    return build_lifecycle_relationship_from_parts(
        org_id,
        network_traffic_id,
        author_id,
        marking_id,
        start_time,
        stop_time,
        labels=lifecycle_labels(row),
        external_id=lifecycle_external_id(row),
        existing_id=existing_id,
    )


def build_software_relationship(
    network_traffic_id: str,
    software_id: str,
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Network-Traffic -> Software, with no lifecycle of its own.

    Presence/absence tracks with Software's own content-derived id instead of a separate
    start/stop window.
    """
    rel_id = _relationship_id(
        "related-to", network_traffic_id, software_id, None, None, existing_id
    )
    return stix2.Relationship(
        id=rel_id,
        relationship_type="related-to",
        source_ref=network_traffic_id,
        target_ref=software_id,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
    )


def dedupe_bundle_objects(objects: List) -> List:
    """Collapse a list of STIX objects to one per id, keeping the last occurrence of each.

    Same rationale as connectors A/B/D -- many rows share the same IP/org across one poll.
    """
    seen = {}
    for obj in objects:
        seen[obj["id"]] = obj
    return list(seen.values())
