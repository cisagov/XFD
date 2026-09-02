"""Loop 1 (OpenCTI-connector.md §9b): pure mapping unit tests, no DB/OpenCTI/queue at all."""

# Standard Python Libraries
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti import Identity as OpenCTIIdentity  # noqa: E402
from pycti import StixCoreRelationship  # noqa: E402
import pytest  # noqa: E402

# First-Party
from src import mapping  # noqa: E402
import stix2  # noqa: E402

_AUTHOR_ID = OpenCTIIdentity.generate_id("Test Author", "system")
_MARKING_ID = stix2.TLP_AMBER.id
_ORG_ID = OpenCTIIdentity.generate_id("Test Organization One", "organization")
_IP_ID = mapping.map_ip_observable("198.51.100.5").id
_NETWORK_TRAFFIC_ID = stix2.NetworkTraffic(
    src_ref=_IP_ID, src_port=443, protocols=["tcp"]
).id


def _row(**overrides):
    row = {
        "id": "ps-1",
        "port_scan_id": "ps-1",
        "ip_string": "198.51.100.5",
        "port": 443,
        "protocol": "tcp",
        "state": "open",
        "time_scanned": "2026-08-20T12:00:00+00:00",
        "service_name": "https",
        "service_cpe": None,
        "service_product": None,
        "service_version": None,
        "source": "nmap",
        "nmi_service_group": None,
        "risky_service_group": None,
        "current": True,
    }
    row.update(overrides)
    return row


def test_resolve_org_identity_id_matches_connector_ds_own_identity_construction():
    """§7c: 'look up, don't blindly create' -- must land on connector D's own id."""
    assert mapping.resolve_org_identity_id("Test Organization One") == _ORG_ID


def test_map_ip_observable_v4_and_v6():
    """A host address maps to the matching IPv4Address/IPv6Address SCO type."""
    assert mapping.map_ip_observable("198.51.100.5").type == "ipv4-addr"
    assert mapping.map_ip_observable("2001:db8::5").type == "ipv6-addr"


def test_build_network_traffic_uses_normalized_lowercase_protocol():
    """Protocol strings get lower-cased regardless of how the scanner reported them."""
    nt = mapping.build_network_traffic(_row(protocol="TCP"), _IP_ID)
    assert nt.protocols == ["tcp"]
    assert nt.src_port == 443
    assert nt.src_ref == _IP_ID


def test_build_network_traffic_raises_without_a_port():
    """A row with no port number is malformed, not a default-able case."""
    with pytest.raises(ValueError):
        mapping.build_network_traffic(_row(port=None), _IP_ID)


def test_build_network_traffic_raises_without_a_protocol():
    """A row with no protocol is malformed, not a default-able case."""
    with pytest.raises(ValueError):
        mapping.build_network_traffic(_row(protocol=None), _IP_ID)


def test_build_network_traffic_id_is_stable_when_service_name_changes():
    """The id must not drift just because scanner-reported service metadata changes.

    §10i-style verification, done proactively: only src_ref/src_port/protocols are
    ID-contributing (verified against the installed stix2 library).
    """
    nt1 = mapping.build_network_traffic(_row(service_name="https"), _IP_ID)
    nt2 = mapping.build_network_traffic(_row(service_name="something else"), _IP_ID)
    assert nt1.id == nt2.id


def test_build_network_traffic_id_is_stable_when_state_changes():
    """The id must not drift when the scanner-reported state flips open<->closed either.

    Same reasoning as service_name above -- x_opencti_open must be free to change on a rescan
    without fragmenting the SCO into a new object.
    """
    nt_open = mapping.build_network_traffic(_row(state="open"), _IP_ID)
    nt_closed = mapping.build_network_traffic(_row(state="closed"), _IP_ID)
    assert nt_open.id == nt_closed.id


def test_build_network_traffic_open_reflects_scanner_state_not_recency():
    """x_opencti_open must come from LatestPortScan.state == "open", not any recency notion.

    connector.py's own `current`/staleness tracking is a wholly separate concept -- see
    mapping.py's module docstring for why an earlier version of this code got that wrong.
    """
    assert (
        mapping.build_network_traffic(_row(state="open"), _IP_ID).x_opencti_open is True
    )
    for closed_state in ("closed", "filtered", "open|filtered", None, "  "):
        nt = mapping.build_network_traffic(_row(state=closed_state), _IP_ID)
        assert nt.x_opencti_open is False, closed_state


def test_build_network_traffic_sets_service_custom_property():
    """x_opencti_service (and the pre-existing x_opencti_description) reflect service_name."""
    nt = mapping.build_network_traffic(_row(service_name="https"), _IP_ID)
    assert nt.x_opencti_service == "https"
    assert nt.x_opencti_description == "https"


def test_is_port_state_open_reduces_nmap_style_states_to_a_plain_boolean():
    """Only a literal "open" (case/whitespace-insensitive) counts -- everything else is False."""
    assert mapping.is_port_state_open("open") is True
    assert mapping.is_port_state_open("Open ") is True
    assert mapping.is_port_state_open("closed") is False
    assert mapping.is_port_state_open("filtered") is False
    assert mapping.is_port_state_open(None) is False
    assert mapping.is_port_state_open("") is False


def test_build_software_returns_none_without_product_version_or_cpe():
    """A row with no software detail at all produces no Software SCO."""
    assert mapping.build_software(_row()) is None


def test_build_software_maps_product_version_and_cpe():
    """service_product/version/cpe map onto Software's name/version/cpe respectively."""
    software = mapping.build_software(
        _row(
            service_product="Apache httpd",
            service_version="2.4.41",
            service_cpe="cpe:/a:x",
        )
    )
    assert software.name == "Apache httpd"
    assert software.version == "2.4.41"
    assert software.cpe == "cpe:/a:x"


def test_build_software_id_changes_with_version():
    """A genuinely different version is a genuinely different Software entity.

    Content-derived id drift here is correct, unlike NetworkTraffic's lifecycle fields.
    """
    a = mapping.build_software(
        _row(service_product="Apache httpd", service_version="2.4.41")
    )
    b = mapping.build_software(
        _row(service_product="Apache httpd", service_version="2.4.62")
    )
    assert a.id != b.id


def test_normalize_timestamp_parses_offset_and_z_suffixed_strings_to_the_same_instant():
    """A bare +00:00-offset string and a Z-suffixed string must parse to the same instant.

    §10i: stix2's TimestampProperty rejects a bare +00:00-offset string outright -- this helper
    must always hand back a real datetime regardless of which ISO variant it's given.
    """
    a = mapping.normalize_timestamp("2026-08-20T12:00:00+00:00")
    b = mapping.normalize_timestamp("2026-08-20T12:00:00Z")
    assert isinstance(a, datetime.datetime)
    assert a == b


def test_build_lifecycle_relationship_reuses_existing_id_when_pinned():
    """A pinned id must be returned verbatim, not recomputed from source/target/time."""
    pinned_id = StixCoreRelationship.generate_id(
        "related-to", _ORG_ID, "network-traffic--x", None, None
    )
    rel = mapping.build_lifecycle_relationship(
        _row(),
        _ORG_ID,
        _NETWORK_TRAFFIC_ID,
        _AUTHOR_ID,
        _MARKING_ID,
        start_time=None,
        stop_time=None,
        existing_id=pinned_id,
    )
    assert rel.id == pinned_id


def test_build_lifecycle_relationship_labels_reflect_row_fields():
    """source/risky_service_group/nmi_service_group/state must all become labels."""
    rel = mapping.build_lifecycle_relationship(
        _row(
            source="nmap",
            risky_service_group="telnet",
            nmi_service_group="web",
            state="open",
        ),
        _ORG_ID,
        _NETWORK_TRAFFIC_ID,
        _AUTHOR_ID,
        _MARKING_ID,
        start_time=None,
        stop_time=None,
    )
    assert set(rel.labels) == {
        "vs-source-nmap",
        "vs-risky-service-telnet",
        "vs-nmi-service-web",
        "vs-state-open",
    }


def test_lifecycle_labels_matches_what_build_lifecycle_relationship_produces():
    """This must be the exact same label computation build_lifecycle_relationship() uses.

    It's cached in connector state for the aging sweep (db.py's module docstring), so a drift
    here would silently change labels on a locally-closed relationship.
    """
    row = _row(
        source="nmap",
        risky_service_group="telnet",
        nmi_service_group="web",
        state="open",
    )
    assert set(mapping.lifecycle_labels(row)) == {
        "vs-source-nmap",
        "vs-risky-service-telnet",
        "vs-nmi-service-web",
        "vs-state-open",
    }


def test_lifecycle_external_id_prefers_port_scan_id_over_id():
    """port_scan_id is preferred; the row's own id is only a fallback."""
    assert (
        mapping.lifecycle_external_id(_row(port_scan_id="ps-real", id="fallback"))
        == "ps-real"
    )
    assert (
        mapping.lifecycle_external_id(_row(port_scan_id=None, id="fallback"))
        == "fallback"
    )


def test_build_lifecycle_relationship_from_parts_reuses_existing_id_when_pinned():
    """The lower-level, state-only builder (no fresh row) must also honor a pinned id."""
    pinned_id = StixCoreRelationship.generate_id(
        "related-to", _ORG_ID, "network-traffic--x", None, None
    )
    rel = mapping.build_lifecycle_relationship_from_parts(
        _ORG_ID,
        _NETWORK_TRAFFIC_ID,
        _AUTHOR_ID,
        _MARKING_ID,
        start_time=None,
        stop_time=None,
        labels=["vs-source-nmap"],
        external_id="ps-1",
        existing_id=pinned_id,
    )
    assert rel.id == pinned_id


def test_build_lifecycle_relationship_and_from_parts_produce_identical_relationships():
    """The row-driven wrapper must be a pure pass-through to the parts-based builder.

    Same id, same labels, same external reference, for the same underlying data.
    """
    row = _row(source="nmap", risky_service_group="telnet")
    via_row = mapping.build_lifecycle_relationship(
        row,
        _ORG_ID,
        _NETWORK_TRAFFIC_ID,
        _AUTHOR_ID,
        _MARKING_ID,
        start_time=None,
        stop_time=None,
    )
    via_parts = mapping.build_lifecycle_relationship_from_parts(
        _ORG_ID,
        _NETWORK_TRAFFIC_ID,
        _AUTHOR_ID,
        _MARKING_ID,
        start_time=None,
        stop_time=None,
        labels=mapping.lifecycle_labels(row),
        external_id=mapping.lifecycle_external_id(row),
    )
    assert via_row.id == via_parts.id
    assert via_row.labels == via_parts.labels


def test_dedupe_bundle_objects_collapses_repeated_ids():
    """Two STIX objects sharing an id must collapse to one in dedupe_bundle_objects()."""
    a = stix2.IPv4Address(value="10.0.0.1")
    a_again = stix2.IPv4Address(value="10.0.0.1")
    b = stix2.IPv4Address(value="10.0.0.2")
    result = mapping.dedupe_bundle_objects([a, a_again, b])
    assert len(result) == 2
