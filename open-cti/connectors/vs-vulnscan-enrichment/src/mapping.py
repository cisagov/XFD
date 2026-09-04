"""Pure row -> STIX mapping functions for the VS VulnScan Enrichment connector.

Deliberately dependency-free beyond stix2/pycti and the standard library -- no DB, no OpenCTI
API, no network. This is "Loop 1" from OpenCTI-connector.md §9b. See tests/test_mapping.py.

STIX mapping decisions here are documented in OpenCTI-connector.md §7b: enrichment is additive
(a `Note` attached to the triggered entity), never overwriting the `Vulnerability` SDO's own
CVSS fields -- those belong to `connector-cve`/`connector-vulncheck`, not this connector.
"""

# Standard Python Libraries
from typing import Dict, List, Optional

# Third-Party Libraries
from pycti import Identity as OpenCTIIdentity
from pycti import Note as OpenCTINote
import stix2

VS_EXTERNAL_SOURCE = "VS-VulnScan"


def build_author(name: str) -> stix2.Identity:
    """Build the single system Identity every VS-sourced object should cite as createdBy (§10c).

    Identical construction to connectors A/D's build_author() -- same name, same identity_class
    -- so all three connectors' Identity(class="system") objects resolve to the one shared author.
    """
    return stix2.Identity(
        id=OpenCTIIdentity.generate_id(name, "system"),
        name=name,
        identity_class="system",
    )


def _format_row(row: Dict) -> str:
    """Render one VulnScan row as a short, readable section of the enrichment Note's content.

    `cvss_base_score`/`cvss_vector` (CVSS v2) are plain CharFields; `cvss3_base_score`/
    `cvss3_temporal_score` are DecimalFields (verified against a real postgres:17 container,
    §9b Loop 4, before this ever touched the live box) -- both just get stringified for display
    here, never used numerically, so the live-vs-fixture type gap that mattered for Ticket's
    cvss_severity (§10i) doesn't bite the same way for this connector.
    """
    lines = [f"### {row.get('plugin_name') or row.get('plugin_id') or 'Finding'}"]
    port = row.get("port")
    if port:
        lines.append(
            f"- Port/service: {port}/{row.get('port_protocol') or '?'} ({row.get('service') or 'unknown'})"
        )
    if row.get("cvss_base_score"):
        lines.append(
            f"- CVSS v2: {row['cvss_base_score']} ({row.get('cvss_vector') or 'no vector'})"
        )
    if row.get("cvss3_base_score") is not None:
        lines.append(
            f"- CVSS v3: {row['cvss3_base_score']} ({row.get('cvss3_vector') or 'no vector'})"
        )
    if row.get("risk_factor"):
        lines.append(f"- Risk factor: {row['risk_factor']}")
    if row.get("exploit_available"):
        lines.append(
            f"- Exploit available: {row['exploit_available']} "
            f"({row.get('exploitability_ease') or 'ease unknown'})"
        )
    if row.get("synopsis"):
        lines.append(f"- Synopsis: {row['synopsis']}")
    if row.get("solution"):
        lines.append(f"- Solution: {row['solution']}")
    if row.get("source") or row.get("owner"):
        lines.append(
            f"- Source: {row.get('source') or 'unknown'} (owner: {row.get('owner') or 'unknown'})"
        )
    if row.get("vuln_detection_timestamp"):
        # Plain display text, not a STIX timestamp property -- no TimestampProperty validation
        # involved, so str() is enough regardless of whether this is a real psycopg2 datetime
        # (live) or an ISO string (IS_LOCAL fixture). Unlike mapping.normalize_timestamp() in
        # connectors A/D, there's nothing here for stix2 to reject.
        lines.append(f"- Last detected: {row['vuln_detection_timestamp']}")
    return "\n".join(lines)


def build_note_content(vuln_scans: List[Dict]) -> str:
    """Render every matched VulnScan row into one Note's content, oldest logic first.

    Bounded by db.py's own LIMIT (VS_VULNSCAN_ENRICHMENT_MAX_ROWS_PER_ENTITY, §9c) before this
    ever runs -- no further truncation needed here.
    """
    if not vuln_scans:
        return "No VS scanner-level detail found for this entity."
    return "\n\n".join(_format_row(row) for row in vuln_scans)


def build_note_abstract(vuln_scans: List[Dict]) -> str:
    """One-line summary shown in OpenCTI's Note list view."""
    return f"VS scanner enrichment ({len(vuln_scans)} finding(s))"


def build_external_references(
    vuln_scans: List[Dict],
) -> Optional[List[stix2.ExternalReference]]:
    """Build one External Reference per VulnScan row that has a usable see_also URL.

    `see_also`/`xref` are free-text TextFields with no confirmed format (models.py's own
    docstrings don't specify one) -- deliberately conservative here: only rows where `see_also`
    looks like an actual URL become a clickable External Reference; everything else is already
    captured in the Note's own content via _format_row, not lost, just not double-represented as
    a reference. Worth revisiting once real `see_also`/`xref` values from mini_data_lake are
    inspected, same as connector A's severity-bucket caveat -- flagged, not guessed past.
    """
    refs = []
    for row in vuln_scans:
        see_also = (row.get("see_also") or "").strip()
        row_id = row.get("id")
        if row_id and (
            see_also.startswith("http://") or see_also.startswith("https://")
        ):
            refs.append(
                stix2.ExternalReference(
                    source_name=VS_EXTERNAL_SOURCE,
                    external_id=row_id,
                    url=see_also,
                )
            )
    return refs or None


def _note_id(content: str, existing_id: Optional[str]) -> str:
    """Apply the §10a idempotency pattern to a Note, for a different reason than relationships.

    Same as every relationship builder in connectors A/D, but worth spelling out why it applies
    to a Note too.

    pycti.Note.generate_id() hashes `content` (and `created`/`abstract`) directly -- verified
    against the installed pycti source -- so recomputing it fresh on every re-enrichment would
    produce a *different* id the moment scanner data changes even slightly, the same failure
    mode §10a already documented for relationships' start_time/stop_time. Pinning the first-seen
    id in connector state (keyed by the triggered entity's id -- see connector.py) and reusing it
    verbatim is what turns every re-trigger into an update-in-place on one Note, instead of a
    pile of near-duplicate Notes accumulating on the same entity.
    """
    if existing_id:
        return existing_id
    return OpenCTINote.generate_id(created=None, content=content)


def build_note(
    entity_stix_id: str,
    vuln_scans: List[Dict],
    author_id: str,
    marking_id: str,
    existing_id: Optional[str] = None,
) -> stix2.Note:
    """Build the enrichment Note attached to the triggered entity.

    Additive, not overwriting (§7b): this never touches the Vulnerability SDO's own CVSS fields
    -- connector-cve/connector-vulncheck already own those. object_refs is what actually attaches
    this Note to the entity that was enriched.
    """
    content = build_note_content(vuln_scans)
    return stix2.Note(
        id=_note_id(content, existing_id),
        abstract=build_note_abstract(vuln_scans),
        content=content,
        object_refs=[entity_stix_id],
        created_by_ref=author_id,
        object_marking_refs=[marking_id],
        external_references=build_external_references(vuln_scans),
    )


def dedupe_bundle_objects(objects: List) -> List:
    """Collapse a list of STIX objects to one per id, keeping the last occurrence of each.

    Same rationale as connectors A/D -- the author/marking objects are shared across every
    invocation, and this keeps that consistent even as this connector's own object list grows
    in the future.
    """
    seen = {}
    for obj in objects:
        seen[obj["id"]] = obj
    return list(seen.values())
