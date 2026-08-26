"""Pure row -> STIX mapping functions for the VS Organization & CIDR Bootstrap connector.

Deliberately dependency-free beyond stix2/pycti and the standard library -- no DB, no OpenCTI
API, no network. This is "Loop 1" from OpenCTI-connector.md §9b: the fastest possible test loop,
and where most of a connector's actual bugs live. See tests/test_mapping.py.

STIX mapping decisions implemented here are documented in OpenCTI-connector.md §7d; the
idempotency pattern (why relationships take an `existing_id` param) is §10a.
"""

# Standard Python Libraries
import datetime
from ipaddress import ip_network
from typing import Dict, List, Optional

# Third-Party Libraries
from pycti import Identity as OpenCTIIdentity
from pycti import Location as OpenCTILocation
from pycti import StixCoreRelationship
import stix2

VS_EXTERNAL_SOURCE = "VS"


def build_author(name: str) -> stix2.Identity:
    """Build the single system Identity every VS-sourced object should cite as createdBy (§10c)."""
    return stix2.Identity(
        id=OpenCTIIdentity.generate_id(name, "system"),
        name=name,
        identity_class="system",
    )


def map_organization(
    org: Dict,
    author_id: str,
    marking_id: str,
    parent_stix_id: Optional[str] = None,
) -> stix2.Identity:
    """Organization row -> Identity(class=organization).

    `acronym` is the durable join key (OpenCTI-connector.md §7d) -- carried as an External
    Reference for our own/analysts' traceability. It is NOT what makes this idempotent: Identity
    objects get OpenCTI's own content-derived standard_id from (name, identity_class) via
    Identity.generate_id(), independent of anything we attach -- see §10a for why that's *not*
    true of relationships, which is the part of this file that actually needs care.
    """
    labels = []
    if org.get("retired"):
        labels.append("vs-retired")
    if org.get("stakeholder"):
        labels.append("vs-stakeholder")
    if org.get("vs_stakeholder"):
        labels.append("vs-vs-stakeholder")

    extra = {"x_opencti_aliases": [org["acronym"]]} if org.get("acronym") else {}

    return stix2.Identity(
        id=OpenCTIIdentity.generate_id(org["name"], "organization"),
        name=org["name"],
        identity_class="organization",
        labels=labels or None,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
        external_references=[
            stix2.ExternalReference(
                source_name=VS_EXTERNAL_SOURCE, external_id=org["acronym"]
            )
        ]
        if org.get("acronym")
        else None,
        custom_properties=extra,
    )


def map_sector(sector: Dict, author_id: str, marking_id: str) -> stix2.Identity:
    """Map a sector row to Identity(class="class").

    "class" is STIX 2.1's open-vocab term for a categorical (non-org/individual/system/group)
    identity, which is how OpenCTI represents sectors. Collision risk with connector-opencti's
    default sector taxonomy is real -- see OpenCTI-connector.md §7d/§6; look-up-before-create
    against that taxonomy happens in connector.py, not here (this module has no OpenCTI API
    access by design).
    """
    return stix2.Identity(
        id=OpenCTIIdentity.generate_id(sector["name"], "class"),
        name=sector["name"],
        identity_class="class",
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
        external_references=[
            stix2.ExternalReference(
                source_name=VS_EXTERNAL_SOURCE, external_id=sector["acronym"]
            )
        ]
        if sector.get("acronym")
        else None,
    )


def map_location(
    location: Dict, author_id: str, marking_id: str
) -> Optional[stix2.Location]:
    """Map a location row to a country-level Location.

    Deliberately simplified to country only for this first pass (not state/county) -- see
    OpenCTI-connector.md §7d. Returns None when there's no usable country field, rather than
    emitting an empty/garbage Location.
    """
    country_name = location.get("country") or location.get("country_abrv")
    if not country_name:
        return None

    return stix2.Location(
        id=OpenCTILocation.generate_id(country_name, "Country"),
        name=country_name,
        country=location.get("country_abrv") or country_name,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
        custom_properties={"x_opencti_location_type": "Country"},
    )


def map_cidr_observable(network: str):
    """CIDR string -> IPv4Address/IPv6Address SCO using CIDR notation directly as `value`.

    STIX 2.1 explicitly permits a CIDR block as an address SCO's value (no custom observable type
    needed -- OpenCTI-connector.md §7d). SCOs get the STIX spec's own deterministic, value-derived
    ID automatically; nothing here needs pycti's generate_id helpers.
    """
    parsed = ip_network(network, strict=False)
    if parsed.version == 4:
        return stix2.IPv4Address(value=network)
    return stix2.IPv6Address(value=network)


def normalize_timestamp(value):
    """Normalize a DateField/DateTimeField value to something stix2's TimestampProperty accepts.

    CidrOrgs.first_seen/last_seen are DateField (date-only) in mini_data_lake -- see
    OpenCTI-connector.md §7d -- and psycopg2 hands those back as bare datetime.date objects (or
    bare "YYYY-MM-DD" strings in the IS_LOCAL JSON fixtures). stix2's TimestampProperty rejects
    both; it needs a full datetime. Found by actually running the dry-run test against fixture
    data (tests/test_connector_dry_run.py), not by inspection -- worth remembering as a class of
    bug this codebase's DateField-vs-DateTimeField columns will keep producing elsewhere too.
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
        if "T" in value:
            return value
        return f"{value}T00:00:00Z"
    return value


def _relationship_id(
    relationship_type: str,
    source_ref: str,
    target_ref: str,
    start_time,
    stop_time,
    existing_id: Optional[str],
) -> str:
    """Apply the §10a idempotency pattern: reuse a known ID rather than always recomputing one.

    Recomputing via generate_id() every time hashes in start_time/stop_time and would therefore
    produce a *different* ID the moment stop_time changes (e.g. a CIDR being retired). Only call
    generate_id() the first time this external key is seen; every later reference to it passes
    back the ID connector.py already has recorded in state, so OpenCTI is told "update this exact
    object" rather than left to its fuzzy ±30-day type/source/target/time window match
    (docs.opencti.io/latest/usage/deduplication/) to find it on its own.
    """
    if existing_id:
        return existing_id
    return StixCoreRelationship.generate_id(
        relationship_type, source_ref, target_ref, start_time, stop_time
    )


def build_part_of(
    child_id: str,
    parent_id: str,
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Org -> Sector, or child-org -> parent-org."""
    rel_id = _relationship_id("part-of", child_id, parent_id, None, None, existing_id)
    return stix2.Relationship(
        id=rel_id,
        relationship_type="part-of",
        source_ref=child_id,
        target_ref=parent_id,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
    )


def build_located_at(
    org_id: str,
    location_id: str,
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Org -> Location."""
    rel_id = _relationship_id(
        "located-at", org_id, location_id, None, None, existing_id
    )
    return stix2.Relationship(
        id=rel_id,
        relationship_type="located-at",
        source_ref=org_id,
        target_ref=location_id,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
    )


def build_owns_cidr(
    org_id: str,
    cidr_observable_id: str,
    author_id: str,
    marking_id: str,
    first_seen=None,
    last_seen_or_stop=None,
    existing_id: Optional[str] = None,
) -> stix2.Relationship:
    """Build the org -> CIDR observable relationship.

    Carries the CidrOrgs.first_seen/current lifecycle (§7d) as native start_time/stop_time --
    stop_time set only once CidrOrgs.current has flipped to False (retired). Same idempotency
    caveat as every relationship in this file: see _relationship_id.
    """
    start_time = normalize_timestamp(first_seen)
    stop_time = normalize_timestamp(last_seen_or_stop)
    rel_id = _relationship_id(
        "related-to", org_id, cidr_observable_id, start_time, stop_time, existing_id
    )
    return stix2.Relationship(
        id=rel_id,
        relationship_type="related-to",
        source_ref=org_id,
        target_ref=cidr_observable_id,
        start_time=start_time,
        stop_time=stop_time,
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
    )


def dedupe_bundle_objects(objects: List) -> List:
    """Collapse a list of STIX objects to one per id, keeping the last occurrence of each.

    Bundles built across many orgs/sectors in one run will repeat the same Identity/Location many
    times (e.g. every org in the same sector references that Sector Identity). stix2's Bundle
    doesn't dedupe for you -- collapse by id before sending, both to keep bundles smaller (§10b)
    and because stix2.Bundle construction is order-sensitive about duplicate IDs.
    """
    seen = {}
    for obj in objects:
        seen[obj["id"]] = obj
    return list(seen.values())
