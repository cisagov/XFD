"""Loop 2 (OpenCTI-connector.md §9b): the real poll->map->bundle pipeline against fixtures.

Uses a stub in place of OpenCTIConnectorHelper so no network/queue is touched at all -- this *is*
the dry-run pattern §9b describes, made concrete and actually exercised in CI/dev.

Also the executable proof behind the §10a idempotency claim: run the pipeline twice in a row and
assert relationship ids are stable across runs when nothing changed, the way OpenCTI needs them
to be for updates (like a CIDR retiring) to land on the same object instead of a duplicate.
"""

# Standard Python Libraries
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti.utils.opencti_logger import logger as pycti_logger

# First-Party
from src.config import Config  # noqa: E402
from src.connector import VsOrgBootstrapConnector  # noqa: E402


class StubHelper:
    """Just enough of OpenCTIConnectorHelper's surface for _process() to run against.

    send_stix2_bundle captures instead of transmitting -- the network/queue boundary itself.

    connector_logger deliberately uses pycti's *real* AppLogger, not a plain stdlib
    logging.getLogger() -- a stdlib logger would have silently accepted the old
    connector_logger.error(msg, exc_info=True) and connector_logger.info(msg, %s-args) calls
    that crashed for real on a live run (AppLogger.error/info only take (message, meta=None), no
    lazy %%-formatting, no exc_info kwarg). Using the real class here means this dry-run test
    would have caught both bugs before they ever reached a real connector run.
    """

    def __init__(self):
        """Start with an empty capture list -- nothing has been "sent" yet."""
        self.connector_logger = pycti_logger(level=20, json_logging=False)(
            "stub_helper"
        )
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


def test_process_watermark_is_json_serializable_for_real_datetime_objects():
    """Prove the watermark fix against what psycopg2 actually returns, not just fixture strings.

    organization.updated_at is a timestamptz column -- psycopg2 hands back a real
    datetime.datetime for it on a live run, but every fixture in this suite stores it as an
    already-JSON-safe ISO string, so this specific bug ("Object of type datetime is not JSON
    serializable" from pycti's set_state() -> json.dumps()) was invisible to every other test
    here. Override the fixture data with a real datetime, the way live data actually looks.
    """
    # Standard Python Libraries
    import datetime
    import json

    connector = build_test_connector()
    data = connector.repository.fetch(since_updated_at=None)
    for org in data.organizations:
        org["updated_at"] = datetime.datetime(
            2026, 8, 21, 9, 30, tzinfo=datetime.timezone.utc
        )

    watermark = connector._process(data, {})

    assert isinstance(watermark, str)
    json.dumps({"last_updated_at_watermark": watermark})  # must not raise


def test_one_bad_cidr_does_not_abort_the_whole_run():
    """§10e's row-isolation promise, actually exercised.

    One malformed CIDR previously aborted _process() entirely -- at full production scale, a
    single bad row meant *zero* orgs got sent that run, not just the offending one. Uses an
    invalid network string here (a different failure mode than the stop_time bug that first
    surfaced this) specifically to prove the isolation is general-purpose, not a fix narrowly
    scoped to that one bug.
    """
    # Standard Python Libraries
    import json

    connector = build_test_connector()
    data = connector.repository.fetch(since_updated_at=None)
    data.cidrs.append(
        {
            "network": "not-a-valid-cidr",
            "organization_acronym": data.organizations[0]["acronym"],
            "first_seen": "2026-01-01",
            "last_seen": "2026-01-01",
            "current": True,
        }
    )

    watermark = connector._process(data, {})

    assert watermark is not None  # the run completed, it didn't raise
    bundle = json.loads(connector.helper.sent_bundles[-1])
    networks_sent = [
        obj["value"]
        for obj in bundle["objects"]
        if obj["type"] in ("ipv4-addr", "ipv6-addr")
    ]
    assert "not-a-valid-cidr" not in networks_sent  # the bad one was skipped
    assert "198.51.100.0/24" in networks_sent  # the good ones still went out


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
