"""Loop 2 (OpenCTI-connector.md §9b): the real poll->diff->bundle pipeline against fixtures.

Uses a stub in place of OpenCTIConnectorHelper so no network/queue is touched at all. Also proves
the §7c reconciliation loop itself: a second identical poll sends nothing, a port going stale
sets stop_time on the *same* pinned relationship, and a port reopening clears stop_time while
keeping its original start_time.
"""

# Standard Python Libraries
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti.utils.opencti_logger import logger as pycti_logger

# First-Party
from src.config import Config  # noqa: E402
from src.connector import VsPortInventoryConnector  # noqa: E402


class StubHelper:
    """Just enough of OpenCTIConnectorHelper's surface for run()/_process() to run against.

    connector_logger deliberately uses pycti's *real* AppLogger, not a plain stdlib
    logging.getLogger() -- same reasoning as connectors A/B/D's stubs (§10i).
    """

    def __init__(self):
        """Start with empty capture state -- nothing sent or stored yet."""
        self.connector_logger = pycti_logger(level=20, json_logging=False)(
            "stub_helper"
        )
        self.sent_bundles = []
        self._state = {}

    def get_state(self):
        """Return the current stored state, mirroring the real helper's equivalent method."""
        return self._state

    def set_state(self, state):
        """Persist state, mirroring the real helper's equivalent method."""
        self._state = state

    @staticmethod
    def stix2_create_bundle(items):
        """Delegate to pycti's real bundle serialization rather than reimplementing it."""
        # Third-Party Libraries
        from pycti import OpenCTIConnectorHelper

        return OpenCTIConnectorHelper.stix2_create_bundle(items)

    def send_stix2_bundle(self, bundle, **kwargs):
        """Capture the bundle instead of sending it -- this *is* the dry-run boundary."""
        self.sent_bundles.append(bundle)
        return [bundle]


def build_test_connector():
    """Build a VsPortInventoryConnector wired to fixtures and a StubHelper."""
    config = Config(
        raw={
            "vs_port_inventory": {
                "org_acronym_allowlist": "TESTORG1,TESTORG2-CHILD",
                "is_local": True,
                "local_fixture_dir": os.path.join(
                    os.path.dirname(__file__), "fixtures"
                ),
                "tlp_marking": "TLP:AMBER",
            }
        }
    )
    return VsPortInventoryConnector(config=config, helper=StubHelper())


def test_first_run_produces_expected_objects():
    """A single run against the fixtures should produce exactly the objects §7c's design expects."""
    connector = build_test_connector()
    data = connector.repository.fetch()
    state = {}

    connector._process(data, state)

    assert len(connector.helper.sent_bundles) == 1
    bundle = json.loads(connector.helper.sent_bundles[0])
    types = [obj["type"] for obj in bundle["objects"]]
    assert (
        types.count("identity") == 1
    )  # author only -- org Identity is looked up, not created
    assert types.count("marking-definition") == 1
    assert types.count("ipv4-addr") == 1  # 198.51.100.5, shared by two rows
    assert types.count("ipv6-addr") == 1  # 2001:db8::5
    assert (
        types.count("network-traffic") == 3
    )  # 443/tcp, 23/tcp, 22/tcp -- all distinct
    assert (
        types.count("software") == 2
    )  # Apache httpd, OpenSSH -- the telnet row has none
    # 3 lifecycle relationships + 2 deduped org->ip relationships + 2 network-traffic->software
    assert types.count("relationship") == 7

    # The already-stale-on-first-sight telnet row should carry a stop_time; the two open ones
    # shouldn't.
    lifecycle_rels = [
        obj
        for obj in bundle["objects"]
        if obj["type"] == "relationship"
        and obj.get("target_ref", "").startswith("network-traffic--")
    ]
    assert len(lifecycle_rels) == 3
    assert sum(1 for rel in lifecycle_rels if "stop_time" in rel) == 1


def test_second_identical_run_sends_no_bundle():
    """§9 queue discipline: nothing changed means nothing worth putting on the queue."""
    connector = build_test_connector()
    data = connector.repository.fetch()
    state = {}
    connector._process(data, state)

    connector._process(data, state)

    assert (
        len(connector.helper.sent_bundles) == 1
    )  # only the first run actually sent anything


def test_port_going_stale_sets_stop_time_on_the_same_pinned_relationship():
    """§7c: current flipping True -> False must update the *same* relationship, not a new one."""
    connector = build_test_connector()
    data = connector.repository.fetch()
    open_row = next(
        r for r in data.port_scans if r["id"] == "11111111-1111-1111-1111-111111111111"
    )
    state = {}

    connector._process(data, state)
    key = connector._key(open_row)
    open_id = state["port_scan_state"][key]["relationship_id"]
    assert state["port_scan_state"][key]["stop_time"] is None

    open_row["current"] = False
    connector._process(data, state)

    assert (
        state["port_scan_state"][key]["relationship_id"] == open_id
    )  # pinned, as designed
    assert state["port_scan_state"][key]["stop_time"] is not None

    bundle = json.loads(connector.helper.sent_bundles[-1])
    rel_obj = next(obj for obj in bundle["objects"] if obj.get("id") == open_id)
    assert "stop_time" in rel_obj


def test_reopened_port_clears_stop_time_but_keeps_original_start_time():
    """A port that reopens after going stale must clear stop_time without resetting start_time."""
    connector = build_test_connector()
    data = connector.repository.fetch()
    open_row = next(
        r for r in data.port_scans if r["id"] == "11111111-1111-1111-1111-111111111111"
    )
    state = {}

    connector._process(data, state)
    key = connector._key(open_row)
    original_start = state["port_scan_state"][key]["start_time"]

    open_row["current"] = False
    connector._process(data, state)
    assert state["port_scan_state"][key]["stop_time"] is not None

    open_row["current"] = True
    connector._process(data, state)

    assert state["port_scan_state"][key]["stop_time"] is None
    assert (
        state["port_scan_state"][key]["start_time"] == original_start
    )  # unchanged, not reset


def test_state_persists_even_when_a_run_sends_nothing():
    """State must persist every successful poll, not just when something changed.

    Unlike connectors A/D's watermark, next run's diff depends on having seen this run's full
    picture.
    """
    connector = build_test_connector()

    connector.run()
    first_state = copy.deepcopy(connector.helper.get_state())
    connector.run()  # nothing changed the second time -- no bundle, but state must still exist

    assert connector.helper.get_state() == first_state
    assert connector.helper.get_state() != {}


def test_one_bad_row_does_not_abort_the_whole_run():
    """A malformed row must not sink every other row in the same poll.

    §10e/§10i row-isolation, built in from the start.
    """
    connector = build_test_connector()
    data = connector.repository.fetch()
    data.port_scans.append(
        {
            "id": "bad-row",
            "port_scan_id": "ps-bad",
            "ip_string": "198.51.100.9",
            "port": 8080,
            "protocol": None,  # malformed -- mapping.build_network_traffic() must raise on this
            "state": "open",
            "time_scanned": "2026-08-20T00:00:00+00:00",
            "service_name": None,
            "service_cpe": None,
            "service_product": None,
            "service_version": None,
            "source": "nmap",
            "nmi_service_group": None,
            "risky_service_group": None,
            "current": True,
            "organization_acronym": "TESTORG1",
            "organization_name": "Test Organization One",
        }
    )
    state = {}

    connector._process(data, state)  # must not raise

    bundle = json.loads(connector.helper.sent_bundles[-1])
    ips_sent = [
        obj["value"]
        for obj in bundle["objects"]
        if obj["type"] in ("ipv4-addr", "ipv6-addr")
    ]
    assert "198.51.100.9" not in ips_sent  # the bad one was skipped
    assert "198.51.100.5" in ips_sent  # the good ones still went out
