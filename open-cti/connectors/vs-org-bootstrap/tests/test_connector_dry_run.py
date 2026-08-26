"""Loop 2 (OpenCTI-connector.md §9b): the real poll->map->bundle pipeline against fixtures.

Uses a stub in place of OpenCTIConnectorHelper so no network/queue is touched at all -- this *is*
the dry-run pattern §9b describes, made concrete and actually exercised in CI/dev.

Also the executable proof behind the §10a idempotency claim: run the pipeline twice in a row and
assert relationship ids are stable across runs when nothing changed, the way OpenCTI needs them
to be for updates (like a CIDR retiring) to land on the same object instead of a duplicate.
"""

# Standard Python Libraries
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
# First-Party
from src.config import Config  # noqa: E402
from src.connector import VsOrgBootstrapConnector  # noqa: E402


class StubHelper:
    """Just enough of OpenCTIConnectorHelper's surface for _process() to run against.

    send_stix2_bundle captures instead of transmitting -- the network/queue boundary itself.
    """

    def __init__(self):
        """Start with an empty capture list -- nothing has been "sent" yet."""
        self.connector_logger = logging.getLogger("stub_helper")
        self.sent_bundles = []

    @staticmethod
    def stix2_create_bundle(items):
        """Delegate to pycti's real bundle serialization rather than reimplementing it."""
        # Real pycti behavior (verified against the installed version) -- reuse it directly
        # rather than reimplementing bundle serialization ourselves.
        # Third-Party Libraries
        from pycti import OpenCTIConnectorHelper

        return OpenCTIConnectorHelper.stix2_create_bundle(items)

    def send_stix2_bundle(self, bundle, **kwargs):
        """Capture the bundle instead of sending it -- this *is* the dry-run boundary."""
        self.sent_bundles.append(bundle)
        return [bundle]


def build_test_connector():
    """Build a VsOrgBootstrapConnector wired to fixtures and a StubHelper, for both tests below."""
    config = Config(
        raw={
            "vs_org_bootstrap": {
                "org_acronym_allowlist": "TESTORG1,TESTORG2-CHILD",
                "is_local": True,
                "local_fixture_dir": os.path.join(
                    os.path.dirname(__file__), "fixtures"
                ),
                "tlp_marking": "TLP:AMBER",
            }
        }
    )
    return VsOrgBootstrapConnector(config=config, helper=StubHelper())


def test_first_run_produces_expected_objects():
    """A single run against the fixtures should produce exactly the objects §7d's design expects."""
    connector = build_test_connector()
    data = connector.repository.fetch(since_updated_at=None)
    state = {}

    watermark = connector._process(data, state)

    assert (
        watermark == "2026-08-21T09:30:00+00:00"
    )  # max updated_at across both fixture orgs
    assert len(connector.helper.sent_bundles) == 1

    # Standard Python Libraries
    import json

    bundle = json.loads(connector.helper.sent_bundles[0])
    types = [obj["type"] for obj in bundle["objects"]]
    assert types.count("identity") == 4  # author + 2 orgs + 1 sector
    assert types.count("location") == 1
    assert types.count("ipv4-addr") == 1  # 198.51.100.0/24
    assert types.count("ipv6-addr") == 1  # 2001:db8::/32
    # org->sector, child->parent, 2x org->location (both orgs share one location), 2x org->cidr
    assert types.count("relationship") == 6
    assert types.count("marking-definition") == 1

    # The retired IPv6 CIDR's relationship should carry a stop_time; the active v4 one shouldn't.
    cidr_rels = [
        obj
        for obj in bundle["objects"]
        if obj["type"] == "relationship" and obj["relationship_type"] == "related-to"
    ]
    assert any("stop_time" in rel for rel in cidr_rels)
    assert any("stop_time" not in rel for rel in cidr_rels)


def test_relationship_ids_are_stable_across_consecutive_runs():
    """Prove the §10a claim executably: re-running against unchanged data must be a no-op.

    It must produce the *same* relationship ids, not new ones -- otherwise every poll would
    duplicate the graph.
    """
    connector = build_test_connector()
    data = connector.repository.fetch(since_updated_at=None)

    state = {}
    connector._process(data, state)
    first_run_cidr_rel_ids = dict(state["cidr_relationship_ids"])
    first_run_part_of_ids = dict(state["part_of_relationship_ids"])

    # Second run, same data, state carried forward exactly as run() would do it.
    connector._process(data, state)

    assert state["cidr_relationship_ids"] == first_run_cidr_rel_ids
    assert state["part_of_relationship_ids"] == first_run_part_of_ids


def test_cidr_relationship_id_stays_pinned_when_current_flips_but_stop_time_updates():
    """Prove the actual §10a contract at the connector level, not just the raw mapping function.

    test_mapping.py correctly shows generate_id() alone WOULD change the id -- the point of
    connector.py's state tracking is to prevent exactly that: once an external key has a
    recorded relationship id, every later write reuses that id verbatim, and the *new* stop_time
    is what constitutes the update OpenCTI applies to the existing object -- confirmed directly
    against send_stix2_bundle()'s own docstring ("OpenCTI always upserts data by standard id/hash
    regardless of [the update] flag").
    """
    connector = build_test_connector()
    data = connector.repository.fetch(since_updated_at=None)
    active_cidr = next(c for c in data.cidrs if c["current"])
    org_stix_id = mapping_org_id(connector, data, active_cidr["organization_acronym"])
    rel_key = f"{org_stix_id}:{active_cidr['network']}"

    state = {}
    connector._process(data, state)
    open_id = state["cidr_relationship_ids"][rel_key]

    # Simulate the CIDR retiring on the next poll.
    active_cidr["current"] = False
    active_cidr["last_seen"] = "2026-08-25"
    connector._process(data, state)

    closed_id = state["cidr_relationship_ids"][rel_key]
    assert closed_id == open_id  # pinned, as designed

    # Standard Python Libraries
    import json

    bundle = json.loads(connector.helper.sent_bundles[-1])
    rel_obj = next(obj for obj in bundle["objects"] if obj.get("id") == closed_id)
    assert (
        "stop_time" in rel_obj
    )  # ...and the content that changed rides along on that same id


def mapping_org_id(connector, data, acronym):
    """Recompute an org's Identity STIX id the same way connector.py does.

    Just for building the expected state-dict key in the test above.
    """
    # Third-Party Libraries
    from src import mapping

    org_row = next(o for o in data.organizations if o["acronym"] == acronym)
    return mapping.map_organization(
        org_row, connector.author.id, connector.marking.id
    ).id
