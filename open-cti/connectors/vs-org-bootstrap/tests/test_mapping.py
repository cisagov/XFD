"""Loop 1 (OpenCTI-connector.md §9b): pure unit tests against the fixtures in tests/fixtures/.

No DB, no OpenCTI, no queue -- run with: pytest tests/test_mapping.py -v
"""

# Standard Python Libraries
import json
import os
import sys
import uuid

# Third-Party Libraries
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
# First-Party
from src import mapping  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    """Load one tests/fixtures/*.json file by name."""
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def author_id():
    """Provide a real author Identity id for tests that need one."""
    return mapping.build_author("CISA VulnScanning").id


@pytest.fixture
def marking_id():
    """Provide a throwaway but validly-shaped marking-definition id for tests."""
    # Real value comes from config once the §10c policy decision is made.
    return "marking-definition--f88d31f6-486f-44da-b317-01333bde0b82"


def test_build_author_is_a_system_identity():
    """The author Identity must be class=system and deterministic by name."""
    author = mapping.build_author("CISA VulnScanning")
    assert author.identity_class == "system"
    assert author.name == "CISA VulnScanning"
    # Deterministic: building it twice gives the same id (content-derived, not random).
    assert author.id == mapping.build_author("CISA VulnScanning").id


def test_map_organization_basic_fields(author_id, marking_id):
    """An Organization row maps to an Identity carrying the right name/class/labels/reference."""
    orgs = load_fixture("organizations.json")
    org = mapping.map_organization(orgs[0], author_id, marking_id)

    assert org.name == "Test Organization One"
    assert org.identity_class == "organization"
    assert org.created_by_ref == author_id
    assert marking_id in org.object_marking_refs
    assert "vs-stakeholder" in org.labels
    assert "vs-vs-stakeholder" in org.labels
    assert "vs-retired" not in org.labels  # retired=false in the fixture
    assert org.external_references[0].external_id == "TESTORG1"


def test_map_organization_is_deterministic_by_name(author_id, marking_id):
    """Mapping the same org row twice must produce the same Identity id."""
    orgs = load_fixture("organizations.json")
    first = mapping.map_organization(orgs[0], author_id, marking_id)
    second = mapping.map_organization(orgs[0], author_id, marking_id)
    assert first.id == second.id  # same name -> same Identity.generate_id() result


def test_map_organization_retired_label(author_id, marking_id):
    """A retired org row must carry the vs-retired label."""
    org_row = dict(load_fixture("organizations.json")[0])
    org_row["retired"] = True
    org = mapping.map_organization(org_row, author_id, marking_id)
    assert "vs-retired" in org.labels


def test_map_sector(author_id, marking_id):
    """A Sector row maps to a class="class" Identity with its acronym as an external reference."""
    sector_row = load_fixture("sectors.json")[0]
    sector = mapping.map_sector(sector_row, author_id, marking_id)
    assert sector.identity_class == "class"
    assert sector.name == "Information Technology"
    assert sector.external_references[0].external_id == "IT"


def test_map_location_country_only(author_id, marking_id):
    """A Location row with country info maps to a country-level Location."""
    location_row = list(load_fixture("locations_by_id.json").values())[0]
    location = mapping.map_location(location_row, author_id, marking_id)
    assert location is not None
    assert location.name == "United States"
    assert location.x_opencti_location_type == "Country"


def test_map_location_returns_none_without_country(author_id, marking_id):
    """A Location row with no usable country field maps to None, not a garbage Location."""
    assert mapping.map_location({"name": "nowhere"}, author_id, marking_id) is None


def test_map_cidr_observable_ipv4():
    """An IPv4 CIDR string maps to an IPv4-Addr observable using CIDR notation as its value."""
    obs = mapping.map_cidr_observable("198.51.100.0/24")
    assert obs.value == "198.51.100.0/24"
    assert obs.type == "ipv4-addr"


def test_map_cidr_observable_ipv6():
    """An IPv6 CIDR string maps to an IPv6-Addr observable using CIDR notation as its value."""
    obs = mapping.map_cidr_observable("2001:db8::/32")
    assert obs.value == "2001:db8::/32"
    assert obs.type == "ipv6-addr"


def test_cidr_observable_ids_are_deterministic():
    """Mapping the same CIDR twice must produce the same observable id."""
    # SCOs get the STIX spec's own value-derived id -- no pycti generate_id needed (§7d/mapping.py
    # docstring). Confirming this actually holds for our exact usage, not just trusting the spec.
    first = mapping.map_cidr_observable("198.51.100.0/24")
    second = mapping.map_cidr_observable("198.51.100.0/24")
    assert first.id == second.id


@pytest.fixture
def org_stix_id(author_id, marking_id):
    """Provide the mapped Identity id for the first fixture organization."""
    return mapping.map_organization(
        load_fixture("organizations.json")[0], author_id, marking_id
    ).id


@pytest.fixture
def cidr_stix_id():
    """Provide the mapped observable id for a fixed test CIDR."""
    return mapping.map_cidr_observable("198.51.100.0/24").id


def test_part_of_relationship_without_existing_id_is_generated(
    author_id, marking_id, org_stix_id
):
    """With no existing_id, a part-of relationship gets a freshly generated STIX id."""
    sector_id = mapping.map_sector(
        load_fixture("sectors.json")[0], author_id, marking_id
    ).id
    rel = mapping.build_part_of(org_stix_id, sector_id, author_id, marking_id)
    assert rel.relationship_type == "part-of"
    assert rel.source_ref == org_stix_id
    assert rel.target_ref == sector_id
    assert rel.id.startswith("relationship--")


def test_relationship_reuses_existing_id_when_given(
    author_id, marking_id, org_stix_id, cidr_stix_id
):
    """Test the core §10a behavior: a known relationship id must be reused verbatim.

    Recomputing instead, with a changed stop_time, would silently produce a *different* id
    (StixCoreRelationship.generate_id hashes start/stop time in) -- exactly the failure mode
    this pattern exists to avoid.
    """
    known_id = f"relationship--{uuid.uuid4()}"
    rel = mapping.build_owns_cidr(
        org_stix_id,
        cidr_stix_id,
        author_id,
        marking_id,
        first_seen="2025-01-01T00:00:00Z",
        last_seen_or_stop="2026-08-20T00:00:00Z",
        existing_id=known_id,
    )
    assert rel.id == known_id


def test_relationship_id_changes_with_stop_time_when_not_pinned(
    author_id, marking_id, org_stix_id, cidr_stix_id
):
    """Demonstrate *why* §10a's existing_id pattern is necessary.

    Without it, closing out a CIDR (setting stop_time) changes the generated id, which is
    precisely what would defeat naive "just resubmit the relationship" idempotency.
    """
    open_rel = mapping.build_owns_cidr(
        org_stix_id,
        cidr_stix_id,
        author_id,
        marking_id,
        first_seen="2025-01-01T00:00:00Z",
        last_seen_or_stop=None,
    )
    closed_rel = mapping.build_owns_cidr(
        org_stix_id,
        cidr_stix_id,
        author_id,
        marking_id,
        first_seen="2025-01-01T00:00:00Z",
        last_seen_or_stop="2026-08-20T00:00:00Z",
    )
    assert open_rel.id != closed_rel.id


def test_dedupe_bundle_objects_collapses_repeated_ids(author_id, marking_id):
    """Two STIX objects sharing an id must collapse to one in dedupe_bundle_objects()."""
    org_row = load_fixture("organizations.json")[0]
    same_org_twice = [
        mapping.map_organization(org_row, author_id, marking_id),
        mapping.map_organization(org_row, author_id, marking_id),
    ]
    deduped = mapping.dedupe_bundle_objects(same_org_twice)
    assert len(deduped) == 1
