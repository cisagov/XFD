"""Loop 1 (OpenCTI-connector.md §9b): pure mapping unit tests, no DB/OpenCTI/queue at all."""

# Standard Python Libraries
from decimal import Decimal
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti import Identity as OpenCTIIdentity  # noqa: E402

# First-Party
from src import mapping  # noqa: E402
import stix2  # noqa: E402

_AUTHOR_ID = OpenCTIIdentity.generate_id("Test Author", "system")
_MARKING_ID = stix2.TLP_AMBER.id
_ENTITY_ID = stix2.IPv4Address(value="198.51.100.5").id


def test_build_author_is_a_system_identity():
    """The author Identity must be class=system and deterministic by name."""
    obj = mapping.build_author("CISA VulnScanning")
    assert obj.identity_class == "system"
    assert obj.id == OpenCTIIdentity.generate_id("CISA VulnScanning", "system")


def test_build_note_content_lists_every_matched_row():
    """Every VulnScan row must show up in the rendered content, not just the first."""
    rows = [
        {"id": "v1", "plugin_name": "Finding A", "port": 443},
        {"id": "v2", "plugin_name": "Finding B", "port": 22},
    ]
    content = mapping.build_note_content(rows)
    assert "Finding A" in content
    assert "Finding B" in content


def test_build_note_content_handles_decimal_cvss3_score():
    """cvss3_base_score is a DecimalField, not a plain float.

    Verified against a real postgres:17 container (§9b Loop 4) that this comes back as
    decimal.Decimal on a live run.
    """
    rows = [
        {"id": "v1", "plugin_name": "Finding A", "cvss3_base_score": Decimal("9.80")}
    ]
    content = mapping.build_note_content(rows)
    assert "9.80" in content


def test_build_note_content_empty_when_no_rows():
    """Zero matched rows still renders something, not an empty string."""
    assert mapping.build_note_content([]) != ""


def test_build_note_abstract_reports_the_count():
    """The abstract must include the exact count of matched findings."""
    assert (
        mapping.build_note_abstract([{}, {}, {}])
        == "VS scanner enrichment (3 finding(s))"
    )


def test_build_external_references_includes_only_url_looking_see_also():
    """Free-text see_also/xref with no confirmed format -- only real URLs become a reference."""
    rows = [
        {"id": "v1", "see_also": "https://example.com/advisory/1"},
        {"id": "v2", "see_also": "not a url, just scanner notes"},
        {"id": "v3", "see_also": None},
    ]
    refs = mapping.build_external_references(rows)
    assert len(refs) == 1
    assert refs[0].url == "https://example.com/advisory/1"


def test_build_external_references_returns_none_when_nothing_url_shaped():
    """No URL-shaped see_also values means None, not an empty list."""
    rows = [{"id": "v1", "see_also": "just text"}]
    assert mapping.build_external_references(rows) is None


def test_build_note_reuses_existing_id_when_pinned():
    """A pinned id must be returned verbatim, not recomputed from content.

    §10a idempotency: pycti.Note.generate_id() hashes content, so recomputing on every
    re-enrichment would produce a *different* Note id the moment scanner data changes at all.
    """
    rows = [{"id": "v1", "plugin_name": "Finding A"}]
    # A real, differently-computed note id -- proves build_note() returns *this* id verbatim.
    # Third-Party Libraries
    from pycti import Note as OpenCTINote

    pinned_id = OpenCTINote.generate_id(created=None, content="something else entirely")
    note = mapping.build_note(
        _ENTITY_ID, rows, _AUTHOR_ID, _MARKING_ID, existing_id=pinned_id
    )
    assert note.id == pinned_id


def test_build_note_id_changes_with_content_when_not_pinned():
    """Shows generate_id() alone WOULD change id when content changes -- why connector.py pins it."""
    rows_a = [{"id": "v1", "plugin_name": "Finding A"}]
    rows_b = [{"id": "v1", "plugin_name": "Finding A -- rescored"}]
    note_a = mapping.build_note(_ENTITY_ID, rows_a, _AUTHOR_ID, _MARKING_ID)
    note_b = mapping.build_note(_ENTITY_ID, rows_b, _AUTHOR_ID, _MARKING_ID)
    assert note_a.id != note_b.id  # not pinned here -- connector.py is what pins it


def test_build_note_object_refs_points_at_the_triggered_entity():
    """object_refs is what actually attaches this Note to the enriched entity."""
    rows = [{"id": "v1", "plugin_name": "Finding A"}]
    note = mapping.build_note(_ENTITY_ID, rows, _AUTHOR_ID, _MARKING_ID)
    assert note.object_refs == [_ENTITY_ID]


def test_dedupe_bundle_objects_collapses_repeated_ids():
    """Two STIX objects sharing an id must collapse to one in dedupe_bundle_objects()."""
    a = stix2.IPv4Address(value="10.0.0.1")
    a_again = stix2.IPv4Address(value="10.0.0.1")
    b = stix2.IPv4Address(value="10.0.0.2")
    result = mapping.dedupe_bundle_objects([a, a_again, b])
    assert len(result) == 2
