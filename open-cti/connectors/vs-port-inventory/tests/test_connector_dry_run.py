"""Loop 2 (OpenCTI-connector.md §9b): the real poll->diff->bundle pipeline against fixtures.

Uses a stub in place of OpenCTIConnectorHelper so no network/queue is touched at all. Proves the
redesigned watermark + local-aging-sweep loop (2026-08-31, see connector.py's module docstring):
a bootstrap poll pulls in currently-active rows regardless of age, a second identical poll sends
nothing, a port aging past the cutoff *without ever being refetched* still gets closed by the
aging sweep alone, and a port reopening clears stop_time while keeping its original start_time.

Timestamps here are computed relative to test-execution time (`_now()`), not hardcoded calendar
dates -- this connector's own logic depends on elapsed time relative to `time_scanned`, so a
fixed date would silently drift out of the cutoff window as real time passes and make these
tests flaky months later, exactly the kind of live-vs-fixture gap §10i keeps calling out.
"""

# Standard Python Libraries
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti.utils.opencti_logger import logger as pycti_logger

# First-Party
from src.config import Config  # noqa: E402
from src.connector import VsPortInventoryConnector  # noqa: E402
from src.db import PortInventoryData  # noqa: E402


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


def build_test_connector(cutoff_days=14):
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
                "latest_port_scan_cutoff_days": str(cutoff_days),
            }
        }
    )
    return VsPortInventoryConnector(config=config, helper=StubHelper())


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _row(**overrides):
    row = {
        "id": "ps-1",
        "port_scan_id": "ps-1",
        "ip_string": "198.51.100.5",
        "port": 443,
        "protocol": "tcp",
        "state": "open",
        "time_scanned": _now().isoformat(),
        "service_name": "https",
        "service_cpe": None,
        "service_product": "Apache httpd",
        "service_version": "2.4.41",
        "source": "nmap",
        "nmi_service_group": "web",
        "risky_service_group": None,
        "current": True,
        "organization_acronym": "TESTORG1",
        "organization_name": "Test Organization One",
    }
    row.update(overrides)
    return row


def test_first_run_against_fixtures_produces_expected_object_shape():
    """A single run against the fixtures should produce the object types §7c's design expects."""
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None, include_current=True)
    state = {}

    connector._process(data, state)

    assert len(connector.helper.sent_bundles) == 1
    bundle = json.loads(connector.helper.sent_bundles[0])
    types = [obj["type"] for obj in bundle["objects"]]
    assert (
        types.count("identity") == 1
    )  # author only -- org Identity is looked up, not created
    assert types.count("marking-definition") == 1
    assert types.count("ipv4-addr") == 1  # 198.51.100.5, shared by two fixture rows
    assert types.count("ipv6-addr") == 1  # 2001:db8::5
    assert (
        types.count("network-traffic") == 3
    )  # 443/tcp, 23/tcp, 22/tcp -- all distinct
    assert (
        types.count("software") == 2
    )  # Apache httpd, OpenSSH -- the telnet row has none
    # 3 lifecycle relationships + 2 deduped org->ip relationships + 2 network-traffic->software
    assert types.count("relationship") == 7
    # The "vs-open" label must mirror the fixtures' own `state` field, not recency -- all three
    # fixture rows report state="open" (port 23's telnet row is old enough to be locally
    # non-"current", fetched via include_current, but the scanner still last confirmed it open).
    nt_by_port = {
        obj["src_port"]: "vs-open" in obj.get("labels", [])
        for obj in bundle["objects"]
        if obj["type"] == "network-traffic"
    }
    assert nt_by_port == {443: True, 23: True, 22: True}


def test_a_pure_state_flip_still_triggers_a_resend():
    """A rescan that only changes state=open->closed (nothing else) must still be sent.

    port_state_open is in _process_row()'s changed-fields check specifically so this doesn't
    silently get swallowed by the "nothing changed" queue-discipline shortcut.
    """
    connector = build_test_connector()
    state = {}
    connector._process(PortInventoryData(port_scans=[_row(state="open")]), state)
    sent_before = len(connector.helper.sent_bundles)

    connector._process(PortInventoryData(port_scans=[_row(state="closed")]), state)

    assert len(connector.helper.sent_bundles) == sent_before + 1
    key = connector._key(_row())
    assert state["port_scan_state"][key]["port_state_open"] is False
    bundle = json.loads(connector.helper.sent_bundles[-1])
    nt_id = state["port_scan_state"][key]["network_traffic_id"]
    nt_obj = next(obj for obj in bundle["objects"] if obj.get("id") == nt_id)
    assert "vs-open" not in nt_obj.get("labels", [])


def test_second_identical_run_sends_no_bundle():
    """§9 queue discipline: nothing changed means nothing worth putting on the queue."""
    connector = build_test_connector()
    data = PortInventoryData(port_scans=[_row()])
    state = {}
    connector._process(data, state)

    connector._process(data, state)

    assert (
        len(connector.helper.sent_bundles) == 1
    )  # only the first run actually sent anything


def test_is_current_is_computed_locally_not_trusted_from_the_row():
    """The row's own `current` field must be ignored -- only time_scanned + cutoff decide.

    A row claiming current=False but scanned moments ago must be treated as open; a row
    claiming current=True but scanned long before the cutoff must be treated as stale.
    """
    connector = build_test_connector(cutoff_days=14)
    stale_but_claims_current = _row(
        id="ps-old",
        current=True,
        time_scanned=(_now() - datetime.timedelta(days=30)).isoformat(),
    )
    fresh_but_claims_closed = _row(
        id="ps-new",
        port=22,
        current=False,
        time_scanned=_now().isoformat(),
    )
    state = {}

    connector._process(PortInventoryData(port_scans=[stale_but_claims_current]), state)
    connector._process(PortInventoryData(port_scans=[fresh_but_claims_closed]), state)

    old_key = connector._key(stale_but_claims_current)
    new_key = connector._key(fresh_but_claims_closed)
    assert state["port_scan_state"][old_key]["current"] is False
    assert state["port_scan_state"][old_key]["stop_time"] is not None
    assert state["port_scan_state"][new_key]["current"] is True
    assert state["port_scan_state"][new_key]["stop_time"] is None


def test_watermark_is_the_max_time_scanned_across_fetched_rows():
    """The new watermark must be the latest time_scanned actually seen this run."""
    connector = build_test_connector()
    earlier = _row(
        id="ps-1",
        port=443,
        time_scanned=(_now() - datetime.timedelta(days=1)).isoformat(),
    )
    later = _row(id="ps-2", port=22, time_scanned=_now().isoformat())

    watermark = connector._process(PortInventoryData(port_scans=[earlier, later]), {})

    assert watermark == connector._compute_watermark([earlier, later])
    assert watermark == later["time_scanned"]


def test_watermark_is_none_when_nothing_was_fetched():
    """No fetched rows means nothing to advance the watermark past."""
    connector = build_test_connector()
    assert connector._process(PortInventoryData(port_scans=[]), {}) is None


def test_aging_sweep_closes_a_port_that_ages_past_cutoff_without_ever_being_refetched():
    """The core point of the redesign: no fresh row is needed to detect staleness.

    §7c's original gotcha (mark_stale_latest_port_scans() never bumps time_scanned) is solved by
    computing the same rule locally instead of re-polling for it -- this proves that path.
    """
    connector = build_test_connector(cutoff_days=14)
    row = _row()
    state = {}
    connector._process(PortInventoryData(port_scans=[row]), state)
    key = connector._key(row)
    assert state["port_scan_state"][key]["current"] is True
    assert state["port_scan_state"][key]["stop_time"] is None
    open_id = state["port_scan_state"][key]["relationship_id"]

    # Simulate real elapsed time without a fresh row -- push the stored time_scanned back past
    # the cutoff directly in state, the same way waiting 15 real days would.
    long_ago = _now() - datetime.timedelta(days=15)
    state["port_scan_state"][key]["time_scanned"] = long_ago.isoformat()

    watermark = connector._process(PortInventoryData(port_scans=[]), state)

    assert (
        watermark is None
    )  # nothing was fetched -- the closure came from the aging sweep alone
    assert state["port_scan_state"][key]["current"] is False
    assert state["port_scan_state"][key]["stop_time"] is not None
    assert (
        state["port_scan_state"][key]["relationship_id"] == open_id
    )  # pinned, as designed
    # Scanner-confirmed state is untouched by going stale -- see mapping.py's module docstring.
    assert state["port_scan_state"][key]["port_state_open"] is True
    bundle = json.loads(connector.helper.sent_bundles[-1])
    rel_obj = next(obj for obj in bundle["objects"] if obj.get("id") == open_id)
    assert "stop_time" in rel_obj
    # The SCO itself must NOT be resent by the aging sweep alone -- its vs-state-*/vs-open
    # labels track the scanner's confirmed state, not recency, so there's nothing new to say
    # about it here.
    nt_id = state["port_scan_state"][key]["network_traffic_id"]
    assert not any(obj.get("id") == nt_id for obj in bundle["objects"])


def test_aging_sweep_leaves_a_still_fresh_port_alone():
    """A port well within the cutoff window must not get touched by the aging sweep."""
    connector = build_test_connector(cutoff_days=14)
    row = _row()
    state = {}
    connector._process(PortInventoryData(port_scans=[row]), state)
    sent_before = len(connector.helper.sent_bundles)

    connector._process(PortInventoryData(port_scans=[]), state)

    key = connector._key(row)
    assert state["port_scan_state"][key]["current"] is True
    assert (
        len(connector.helper.sent_bundles) == sent_before
    )  # nothing to send -- still current


def test_reopened_port_clears_stop_time_but_keeps_original_start_time():
    """A port that reopens after going stale must clear stop_time without resetting start_time."""
    connector = build_test_connector(cutoff_days=14)
    row = _row()
    state = {}

    connector._process(PortInventoryData(port_scans=[row]), state)
    key = connector._key(row)
    original_start = state["port_scan_state"][key]["start_time"]

    # Age it out locally, same as the dedicated aging-sweep test.
    state["port_scan_state"][key]["time_scanned"] = (
        _now() - datetime.timedelta(days=15)
    ).isoformat()
    connector._process(PortInventoryData(port_scans=[]), state)
    assert state["port_scan_state"][key]["stop_time"] is not None

    # Reopens: a fresh row for the same key, rescanned just now.
    reopened_row = _row(time_scanned=_now().isoformat())
    connector._process(PortInventoryData(port_scans=[reopened_row]), state)

    assert state["port_scan_state"][key]["stop_time"] is None
    assert (
        state["port_scan_state"][key]["start_time"] == original_start
    )  # unchanged, not reset


def test_run_threads_since_and_include_current_like_connector_as_bootstrap_flag():
    """run() must pass include_current=True only on the first poll.

    Matches connector A's is_first_run/include_stale_open pattern applied to this table.
    """
    connector = build_test_connector()
    calls = []
    original_fetch = connector.repository.fetch

    def spying_fetch(since_last_seen, include_current=False):
        calls.append((since_last_seen, include_current))
        return original_fetch(since_last_seen, include_current=include_current)

    connector.repository.fetch = spying_fetch

    connector.run()  # no watermark yet -- bootstrap
    connector.run()  # watermark now set -- steady-state

    assert calls[0] == (None, True)
    assert calls[1][1] is False


def test_state_persists_even_when_a_run_sends_nothing():
    """State must persist every successful poll, not just when something changed."""
    connector = build_test_connector()

    connector.run()
    first_state_keys = set(connector.helper.get_state().get("port_scan_state", {}))
    connector.run()

    assert (
        set(connector.helper.get_state().get("port_scan_state", {})) == first_state_keys
    )
    assert connector.helper.get_state() != {}


def test_one_bad_row_does_not_abort_the_whole_run():
    """A malformed row must not sink every other row in the same poll.

    §10e/§10i row-isolation, built in from the start.
    """
    connector = build_test_connector()
    good_row = _row()
    bad_row = _row(
        id="bad-row",
        port_scan_id="ps-bad",
        ip_string="198.51.100.9",
        protocol=None,  # malformed -- mapping.build_network_traffic() must raise on this
    )
    state = {}

    connector._process(
        PortInventoryData(port_scans=[good_row, bad_row]), state
    )  # must not raise

    bundle = json.loads(connector.helper.sent_bundles[-1])
    ips_sent = [
        obj["value"]
        for obj in bundle["objects"]
        if obj["type"] in ("ipv4-addr", "ipv6-addr")
    ]
    assert "198.51.100.9" not in ips_sent  # the bad one was skipped
    assert "198.51.100.5" in ips_sent  # the good one still went out
