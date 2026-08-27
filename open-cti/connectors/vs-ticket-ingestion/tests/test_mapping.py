"""Loop 1 (OpenCTI-connector.md §9b): pure mapping unit tests, no DB/OpenCTI/queue at all."""

# Standard Python Libraries
from decimal import Decimal
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

# stix2 validates id shape strictly (<type>--<uuid>) -- these need to be real, well-formed ids,
# not readable placeholders like "identity--author", for stix2.Relationship() to accept them at
# all (found by running these tests, not by inspection).
_AUTHOR_ID = OpenCTIIdentity.generate_id("Test Author", "system")
_MARKING_ID = stix2.TLP_AMBER.id
_IP_ID = mapping.map_ip_observable("198.51.100.5").id
_VULN_ID = mapping.map_vulnerability({"id": "x", "cve_string": "CVE-2024-0001"}).id


def test_severity_label_buckets_match_standard_cvss_scale():
    """Scores must bucket into the standard CVSS v3 low/medium/high/critical cutoffs."""
    assert mapping.severity_label(None) is None
    assert mapping.severity_label(0) is None
    assert mapping.severity_label(3.9) == "vs-severity-low"
    assert mapping.severity_label(4.0) == "vs-severity-medium"
    assert mapping.severity_label(6.9) == "vs-severity-medium"
    assert mapping.severity_label(7.0) == "vs-severity-high"
    assert mapping.severity_label(8.9) == "vs-severity-high"
    assert mapping.severity_label(9.0) == "vs-severity-critical"
    assert mapping.severity_label(10.0) == "vs-severity-critical"


def test_severity_label_handles_real_decimal_from_psycopg2():
    """Ticket.cvss_severity is a DecimalField, not a plain float.

    Verified against a real postgres:17 container (§9b Loop 4) that this comes back as
    decimal.Decimal, not float, on a live run.
    """
    assert mapping.severity_label(Decimal("7.50")) == "vs-severity-high"


def test_severity_label_returns_none_for_garbage_input():
    """A non-numeric value must not crash the mapping, just return no label."""
    assert mapping.severity_label("not-a-number") is None


def test_map_ip_observable_v4():
    """An IPv4 host address maps to an IPv4-Addr observable."""
    obj = mapping.map_ip_observable("198.51.100.5")
    assert obj.type == "ipv4-addr"
    assert obj.value == "198.51.100.5"


def test_map_ip_observable_v6():
    """An IPv6 host address maps to an IPv6-Addr observable."""
    obj = mapping.map_ip_observable("2001:db8::5")
    assert obj.type == "ipv6-addr"


def test_map_ip_observable_raises_on_malformed_input():
    """A malformed ip_string must raise, not silently produce a garbage observable."""
    with pytest.raises(ValueError):
        mapping.map_ip_observable("not-an-ip")


def test_map_vulnerability_uses_uppercased_cve_string_when_present():
    """A ticket with a cve_string names its Vulnerability from the uppercased CVE id."""
    ticket = {
        "id": "t1",
        "cve_string": "cve-2024-1234",
        "vuln_name": None,
        "service_name": None,
    }
    obj = mapping.map_vulnerability(ticket)
    assert obj.name == "CVE-2024-1234"


def test_map_vulnerability_falls_back_to_vuln_name_for_cve_less_tickets():
    """A CVE-less ticket names its Vulnerability from vuln_name when present."""
    ticket = {
        "id": "t2",
        "cve_string": None,
        "vuln_name": "Weak Telnet Auth",
        "service_name": None,
    }
    obj = mapping.map_vulnerability(ticket)
    assert obj.name == "Weak Telnet Auth"


def test_map_vulnerability_falls_back_to_service_name_when_vuln_name_missing():
    """A CVE-less, vuln_name-less ticket falls back to service_name."""
    ticket = {
        "id": "t3",
        "cve_string": None,
        "vuln_name": None,
        "service_name": "telnet",
    }
    obj = mapping.map_vulnerability(ticket)
    assert obj.name == "telnet"


def test_map_vulnerability_raises_when_nothing_usable_to_name_it_from():
    """A ticket with no cve_string, vuln_name, or service_name must raise, not fabricate a name."""
    ticket = {"id": "t4", "cve_string": None, "vuln_name": None, "service_name": None}
    with pytest.raises(ValueError):
        mapping.map_vulnerability(ticket)


def test_resolve_org_identity_id_matches_connector_ds_own_identity_construction():
    """§7a: 'look up, don't blindly create' -- this must land on connector D's own id.

    Specifically the exact same content-derived id connector D's mapping.map_organization()
    computes for the same org name, since that's the only way this resolves to the *same*
    Identity connector D already created.
    """
    connector_d_id = OpenCTIIdentity.generate_id(
        "Test Organization One", "organization"
    )
    assert mapping.resolve_org_identity_id("Test Organization One") == connector_d_id


def test_build_ticket_relationship_carries_start_and_stop_time_for_a_closed_ticket():
    """A ticket with both opened_timestamp and closed_timestamp gets both on the relationship."""
    ticket = {
        "id": "t5",
        "opened_timestamp": "2026-06-01T00:00:00+00:00",
        "closed_timestamp": "2026-08-21T09:30:00+00:00",
        "vuln_source": "nessus",
        "is_kev": False,
        "is_kev_ransomware": False,
        "is_risky": False,
        "cvss_severity": None,
    }
    rel = mapping.build_ticket_relationship(
        ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID
    )
    assert rel.start_time is not None
    assert rel.stop_time is not None


def test_build_ticket_relationship_omits_stop_time_while_open():
    """A ticket with no closed_timestamp must not carry a stop_time at all."""
    ticket = {
        "id": "t6",
        "opened_timestamp": "2026-08-01T00:00:00+00:00",
        "closed_timestamp": None,
        "vuln_source": "nessus",
        "is_kev": False,
        "is_kev_ransomware": False,
        "is_risky": False,
        "cvss_severity": None,
    }
    rel = mapping.build_ticket_relationship(
        ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID
    )
    assert "stop_time" not in rel


def test_build_ticket_relationship_drops_stop_time_when_not_strictly_after_start_time():
    """§10i: STIX 2.1 requires strictly-later stop_time.

    Verified against the installed stix2 library that even equal values raise ValueError. An
    opened-and-closed-in-the-same-write-batch ticket (same timestamp for both) must not crash
    the whole run over one row.
    """
    ticket = {
        "id": "t7",
        "opened_timestamp": "2026-08-01T00:00:00+00:00",
        "closed_timestamp": "2026-08-01T00:00:00+00:00",
        "vuln_source": "nessus",
        "is_kev": False,
        "is_kev_ransomware": False,
        "is_risky": False,
        "cvss_severity": None,
    }
    rel = mapping.build_ticket_relationship(
        ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID
    )
    assert "stop_time" not in rel


def test_build_ticket_relationship_id_changes_with_lifecycle_when_not_pinned():
    """Shows generate_id() alone WOULD change id on closure -- the reason connector.py pins it."""
    open_ticket = {
        "id": "t8",
        "opened_timestamp": "2026-08-01T00:00:00+00:00",
        "closed_timestamp": None,
        "vuln_source": "nessus",
        "is_kev": False,
        "is_kev_ransomware": False,
        "is_risky": False,
        "cvss_severity": None,
    }
    closed_ticket = dict(open_ticket, closed_timestamp="2026-08-21T00:00:00+00:00")

    open_rel = mapping.build_ticket_relationship(
        open_ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID
    )
    closed_rel = mapping.build_ticket_relationship(
        closed_ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID
    )
    assert (
        open_rel.id != closed_rel.id
    )  # not pinned here -- connector.py is what pins it


def test_build_ticket_relationship_reuses_existing_id_when_pinned():
    """existing_id must be returned verbatim, not recomputed from source/target/time."""
    ticket = {
        "id": "t9",
        "opened_timestamp": "2026-08-01T00:00:00+00:00",
        "closed_timestamp": "2026-08-21T00:00:00+00:00",
        "vuln_source": "nessus",
        "is_kev": False,
        "is_kev_ransomware": False,
        "is_risky": False,
        "cvss_severity": None,
    }
    # A real, differently-computed relationship id -- proves build_ticket_relationship() returns
    # *this* id verbatim rather than recomputing its own from source/target/time, not just that
    # some well-formed id round-trips.
    pinned_id = StixCoreRelationship.generate_id(
        "related-to", _VULN_ID, _IP_ID, None, None
    )
    rel = mapping.build_ticket_relationship(
        ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID, existing_id=pinned_id
    )
    assert rel.id == pinned_id


def test_build_ticket_relationship_labels():
    """Source/kev/ransomware/risky/severity flags must all become labels."""
    ticket = {
        "id": "t10",
        "opened_timestamp": "2026-08-01T00:00:00+00:00",
        "closed_timestamp": None,
        "vuln_source": "nmap",
        "is_kev": True,
        "is_kev_ransomware": True,
        "is_risky": True,
        "cvss_severity": 9.5,
    }
    rel = mapping.build_ticket_relationship(
        ticket, _IP_ID, _VULN_ID, _AUTHOR_ID, _MARKING_ID
    )
    assert set(rel.labels) == {
        "vs-source-nmap",
        "vs-kev",
        "vs-kev-ransomware",
        "vs-risky",
        "vs-severity-critical",
    }


def test_dedupe_bundle_objects_collapses_repeated_ids():
    """Two STIX objects sharing an id must collapse to one in dedupe_bundle_objects()."""
    a = stix2.IPv4Address(value="10.0.0.1")
    a_again = stix2.IPv4Address(value="10.0.0.1")
    b = stix2.IPv4Address(value="10.0.0.2")
    result = mapping.dedupe_bundle_objects([a, a_again, b])
    assert len(result) == 2
