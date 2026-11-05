"""Pure row -> STIX mapping functions for the VS Ticket Ingestion connector.

Deliberately dependency-free beyond stix2/pycti and the standard library -- no DB, no OpenCTI
API, no network. This is "Loop 1" from OpenCTI-connector.md §9b. See tests/test_mapping.py.

STIX mapping decisions implemented here are documented in OpenCTI-connector.md §7a; the
idempotency pattern (why the relationship builder takes an `existing_id` param) is §10a, and
§10i (added after connector D) is why the live-vs-fixture type gaps called out below were
checked against a real Postgres container before this ever ran against the live box.
"""

# Standard Python Libraries
import datetime
from ipaddress import ip_address
from typing import Dict, List, Optional

# Third-Party Libraries
from dateutil import parser as dateutil_parser
from pycti import Identity as OpenCTIIdentity
from pycti import StixCoreRelationship
from pycti import Vulnerability as OpenCTIVulnerability
import stix2

VS_EXTERNAL_SOURCE = "VS"


def build_author(name: str) -> stix2.Identity:
    """Build the single system Identity every VS-sourced object should cite as createdBy (§10c).

    Identical construction to connector D's build_author() -- same name, same identity_class --
    so both connectors' Identity(class="system") objects resolve to the exact same content-derived
    id (OpenCTIIdentity.generate_id() is deterministic on (name, identity_class)) and upsert onto
    one shared author Identity in OpenCTI, not two separate ones.
    """
    return stix2.Identity(
        id=OpenCTIIdentity.generate_id(name, "system"),
        name=name,
        identity_class="system",
    )


def resolve_org_identity_id(organization_name: str) -> str:
    """Resolve an organization's existing Identity id -- look up, don't blindly create (§7a).

    Connector D (§7d) is what actually creates/maintains Identity(class="organization") objects.
    This connector never emits one of its own; it only needs to know what id to point
    relationships at. Identity's standard_id is deterministic, content-derived from
    (name, identity_class) via OpenCTIIdentity.generate_id() -- the same call connector D's
    mapping.map_organization() makes -- so recomputing it here reaches the identical id without
    a GraphQL round-trip per ticket. That's the point: at ticket volume (thousands of rows per
    poll, §7a) a live API lookup per row would be real, avoidable load (§10d's discipline
    generalizes to the OpenCTI API, not just mini_data_lake). The tradeoff to keep in mind: this
    assumes `organization.name` hasn't changed between connector D's last sync and this row's
    join (both read the same column, just at different times) -- a real but narrow edge case,
    not verified here structurally, only by both connectors reading the same source of truth.
    """
    return OpenCTIIdentity.generate_id(organization_name, "organization")


def map_ip_observable(ip_string: str):
    """IP string -> IPv4Address/IPv6Address SCO.

    Ticket.ip_string is a single scanned host's address (models.py: "IP address of the host that
    was vulnerability scanned"), not a CIDR block like connector D's Cidr.network -- ip_address(),
    not ip_network(). Raises ValueError on anything malformed; left to propagate so connector.py's
    per-row try/except (§10i) can skip just that one ticket rather than the whole run.
    """
    parsed = ip_address(ip_string)
    if parsed.version == 4:
        return stix2.IPv4Address(value=ip_string)
    return stix2.IPv6Address(value=ip_string)


def severity_label(cvss_severity) -> Optional[str]:
    """Bucket a CVSS severity score into the standard low/medium/high/critical qualitative scale.

    Ticket.cvss_severity is a DecimalField, not a string bucket -- psycopg2 hands back a real
    decimal.Decimal on a live run (verified against a real postgres:17 container, §9b Loop 4,
    before this ever touched the live box), not a plain float the way an IS_LOCAL JSON fixture
    would represent it. Decimal supports direct comparison against float literals in Python (also
    verified), so no explicit cast is required here -- just documented, since it's exactly the
    kind of live-vs-fixture type gap §10i calls out as a recurring bug class. Returns None for
    unscored/zero tickets rather than a "none" label -- the bucket only means something once a
    ticket actually has a score.
    """
    if cvss_severity is None:
        return None
    try:
        score = float(cvss_severity)
    except (TypeError, ValueError):
        return None
    if score <= 0:
        return None
    if score < 4.0:
        return "vs-severity-low"
    if score < 7.0:
        return "vs-severity-medium"
    if score < 9.0:
        return "vs-severity-high"
    return "vs-severity-critical"


def map_vulnerability(ticket: Dict) -> stix2.Vulnerability:
    """Ticket row -> minimal Vulnerability SDO.

    Deliberately minimal when cve_string is present -- name only, no CVSS/description of our own
    (§7a). connector-cve (docker-compose.yml) already runs continuously against NVD and almost
    certainly already has (or will shortly have) a Vulnerability for that CVE; a bare-minimum
    upsert here resolves to the same content-derived id rather than forking a second, VS-flavored
    copy of the same CVE's data.

    For CVE-less tickets (nmap-sourced risky-service tickets, vuln_source="nmap") there's no
    connector-cve equivalent to defer to, so build a real Vulnerability named from vuln_name or
    service_name instead of skipping the ticket -- STIX Vulnerability doesn't require a CVE id.
    Raises ValueError when neither cve_string, vuln_name, nor service_name is usable; left to
    propagate to connector.py's per-row isolation rather than fabricating a placeholder name.
    """
    cve_string = (ticket.get("cve_string") or "").strip()
    if cve_string:
        name = cve_string.upper()
    else:
        name = (ticket.get("vuln_name") or ticket.get("service_name") or "").strip()
    if not name:
        raise ValueError(
            f"Ticket {ticket.get('id')!r} has no cve_string, vuln_name, or service_name to "
            "name a Vulnerability from"
        )
    return stix2.Vulnerability(
        id=OpenCTIVulnerability.generate_id(name),
        name=name,
    )


def normalize_timestamp(value):
    """Normalize a DateTimeField value to something stix2's TimestampProperty accepts.

    Ticket.opened_timestamp/closed_timestamp/updated_timestamp are all DateTimeField
    (timestamptz), unlike connector D's CidrOrgs.first_seen/last_seen (DateField, date-only) --
    so the date-only precision-loss risk mostly doesn't apply here. Still needed because
    IS_LOCAL fixtures store these as plain ISO strings, not live psycopg2 datetimes.

    Deliberately more careful than connector D's same-named helper about *which* string formats
    it hands back to stix2 unmodified: found by actually running this connector's own test suite
    (§9b Loop 1) that stix2's TimestampProperty rejects a `+00:00`-offset ISO string outright
    ("must be a datetime object, date object, or timestamp string in a recognizable format") while
    accepting the exact same instant written as `...Z` or as a real datetime object. Connector D
    never hit this because none of its date-only CidrOrgs fixtures ever exercised that passthrough
    branch with an offset suffix -- but any fixture author writing `datetime.isoformat()`-style
    strings (which produce `+00:00`, not `Z`) for *this* connector's DateTimeField fixtures would.
    Parsing every string through dateutil (already a pinned dependency, §7a) and always returning
    a real datetime object -- never a bare string -- closes the gap for every ISO variant at once
    instead of special-casing `Z`.
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


def _relationship_id(
    relationship_type: str,
    source_ref: str,
    target_ref: str,
    start_time,
    stop_time,
    existing_id: Optional[str],
) -> str:
    """Apply the §10a idempotency pattern -- identical reasoning to connector D's mapping.py.

    Recomputing via generate_id() every time hashes in start_time/stop_time, so it would produce
    a *different* id the moment a ticket closes (stop_time going from unset to set). Only the
    first sighting of a given Ticket.id computes a fresh id; every later write reuses the id
    connector.py already recorded in state (keyed directly by Ticket.id -- simpler than connector
    D's composite CIDR key, since Ticket.id is already a durable, unique external key on its own).
    """
    if existing_id:
        return existing_id
    return StixCoreRelationship.generate_id(
        relationship_type, source_ref, target_ref, start_time, stop_time
    )


def build_org_owns_ip(
    org_id: str,
    ip_observable_id: str,
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Org -> IP observable, so a ticket's vulnerability is actually reachable from its org.

    Without this, resolve_org_identity_id()'s result would be computed and never used --
    §7a lists organization resolution as part of this connector's per-ticket mapping, and the
    only way that's meaningful is a relationship linking the org into the graph, alongside
    connector D's own org->CIDR edges. Not time-scoped (no start/stop) since it isn't tracking a
    lifecycle the way the ticket's own relationship does -- just "this org is associated with
    this host," which multiple tickets against the same host should collapse onto one shared
    edge, not one per ticket. Same idempotency pattern as every relationship builder in this file.
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


def build_ticket_relationship(
    ticket: Dict,
    ip_observable_id: str,
    vulnerability_id: str,
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Build the IP-observable -> Vulnerability relationship carrying a ticket's lifecycle.

    start_time/stop_time = opened_timestamp/closed_timestamp (stop_time omitted while open),
    native SRO fields rather than a separate container object (§7a's Case/Incident decision).
    Severity/kev/risky/source become labels; an External Reference records Ticket.id for our own
    bookkeeping only -- per §10a it plays no role in OpenCTI's own dedup, which is why the id
    itself is pinned via `existing_id` instead.

    `updated_timestamp` (Ticket's own "last updated" column, and the value this connector's
    watermark is COALESCE'd from -- see connector.py/db.py) is carried onto this relationship as
    `x_opencti_updated_timestamp`, a plain custom property rather than the SRO's native
    `modified`. Deliberately not `modified`: OpenCTI/stix2 give that field real merge/versioning
    semantics of their own, and a bootstrap run can hand back tickets whose `updated_timestamp` is
    genuinely in the past relative to what's already stored -- letting that drive `modified` risks
    the platform quietly treating an old bootstrap row as stale and skipping the write. A plain
    custom property carries the same information with none of that risk (same reasoning already
    proven safe for connector C's `x_opencti_*` fields -- verified there that custom properties
    don't feed a STIX object's id the way `start_time`/`stop_time` do, and it's doubly true here
    since this relationship's id is always explicitly pinned, never derived from its own content).
    Deliberately NOT put on the Vulnerability SDO itself -- that object is intentionally minimal
    and shared/deduped across every ticket and org that references the same CVE (see
    `map_vulnerability()`'s docstring); stamping one ticket's update time onto it would let
    whichever connector run happened last overwrite a fact that has nothing to do with that CVE
    itself. This relationship, scoped to one specific (ip, vulnerability) pair, is the right home
    for it -- the same place opened_timestamp/closed_timestamp already live.

    Same defensive stop_time<=start_time guard as connector D's build_owns_cidr, for the same
    reason: STIX 2.1 requires strictly-later stop_time (verified against the installed stix2
    library -- even equal values raise ValueError), and while Ticket's timestamps are full
    DateTimeTime precision (unlike connector D's date-only CidrOrgs columns), an opened-and-closed
    -in-the-same-write-batch ticket is a real, if rarer, possibility -- not something to find out
    about for the first time at full production scale again (§10i).
    """
    start_time = normalize_timestamp(ticket.get("opened_timestamp"))
    stop_time = normalize_timestamp(ticket.get("closed_timestamp"))
    if start_time is not None and stop_time is not None and stop_time <= start_time:
        stop_time = None

    custom_properties: Dict[str, object] = {}
    updated_timestamp = normalize_timestamp(ticket.get("updated_timestamp"))
    if updated_timestamp is not None:
        custom_properties["x_opencti_updated_timestamp"] = updated_timestamp

    labels: List[str] = []
    if ticket.get("vuln_source"):
        labels.append(f"vs-source-{ticket['vuln_source']}")
    if ticket.get("is_kev"):
        labels.append("vs-kev")
    if ticket.get("is_kev_ransomware"):
        labels.append("vs-kev-ransomware")
    if ticket.get("is_risky"):
        labels.append("vs-risky")
    severity = severity_label(ticket.get("cvss_severity"))
    if severity:
        labels.append(severity)

    rel_id = _relationship_id(
        "related-to",
        ip_observable_id,
        vulnerability_id,
        start_time,
        stop_time,
        existing_id,
    )
    return stix2.Relationship(
        id=rel_id,
        relationship_type="related-to",
        source_ref=ip_observable_id,
        target_ref=vulnerability_id,
        start_time=start_time,
        stop_time=stop_time,
        labels=labels or None,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
        external_references=[
            stix2.ExternalReference(
                source_name=VS_EXTERNAL_SOURCE, external_id=ticket["id"]
            )
        ],
        custom_properties=custom_properties,
    )


def dedupe_bundle_objects(objects: List) -> List:
    """Collapse a list of STIX objects to one per id, keeping the last occurrence of each.

    Same rationale as connector D: many tickets against the same host/CVE repeat the same
    IP/Vulnerability object across a run (e.g. two tickets, same host, two different CVEs still
    share the IP observable) -- collapse before sending, both for bundle size (§10b) and because
    stix2.Bundle construction is order-sensitive about duplicate ids.
    """
    seen = {}
    for obj in objects:
        seen[obj["id"]] = obj
    return list(seen.values())
