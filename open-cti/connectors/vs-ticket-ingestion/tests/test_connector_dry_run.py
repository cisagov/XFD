"""Loop 2 (OpenCTI-connector.md §9b): the real poll->map->bundle pipeline against fixtures.

Uses a stub in place of OpenCTIConnectorHelper so no network/queue is touched at all. Also proves
the false-positive revocation path (§7a) and the §9 queue-discipline rule (a revocation-only run
sends no bundle) -- both built in from the start per §10i, not discovered by a live crash.
"""

# Standard Python Libraries
import copy
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti.utils.opencti_logger import logger as pycti_logger

# First-Party
from src.config import Config  # noqa: E402
from src.connector import VsTicketIngestionConnector  # noqa: E402


class _StubRelationshipApi:
    """Stands in for helper.api.stix_core_relationship.

    Captures delete() calls instead of actually calling the OpenCTI GraphQL API.
    """

    def __init__(self):
        """Start with an empty capture list -- nothing has been "deleted" yet."""
        self.deleted_ids = []

    def delete(self, **kwargs):
        """Capture a revocation the way pycti's real API entity would apply it."""
        self.deleted_ids.append(kwargs.get("id"))


class _StubApi:
    """Just enough of helper.api's surface for the revocation path (§7a) to run against."""

    def __init__(self):
        """Build the one sub-API this connector actually touches."""
        self.stix_core_relationship = _StubRelationshipApi()


class StubHelper:
    """Just enough of OpenCTIConnectorHelper's surface for _process() to run against.

    connector_logger deliberately uses pycti's *real* AppLogger, not a plain stdlib
    logging.getLogger() -- connector D's dry-run tests only caught its two AppLogger-signature
    bugs (§10i) once they switched to this; using it from the start here means those bug classes
    can't slip through un-caught in the first place.
    """

    def __init__(self):
        """Start with empty capture state -- nothing sent or deleted yet."""
        self.connector_logger = pycti_logger(level=20, json_logging=False)(
            "stub_helper"
        )
        self.sent_bundles = []
        self.api = _StubApi()
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
    """Build a VsTicketIngestionConnector wired to fixtures and a StubHelper, for the tests below."""
    config = Config(
        raw={
            "vs_ticket_ingestion": {
                "org_acronym_allowlist": "TESTORG1,TESTORG2-CHILD",
                "is_local": True,
                "local_fixture_dir": os.path.join(
                    os.path.dirname(__file__), "fixtures"
                ),
                "tlp_marking": "TLP:AMBER",
            }
        }
    )
    return VsTicketIngestionConnector(config=config, helper=StubHelper())


def test_first_run_produces_expected_objects():
    """A single run against the fixtures should produce exactly the objects §7a's design expects."""
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    state = {}

    watermark = connector._process(data, state)

    # Max COALESCE(closed_timestamp, updated_timestamp) across ALL fetched tickets, including
    # the false-positive one -- it still needs to move the watermark past it (§7a/§10i).
    assert watermark == "2026-08-22T00:00:00+00:00"
    assert len(connector.helper.sent_bundles) == 1

    bundle = json.loads(connector.helper.sent_bundles[0])
    types = [obj["type"] for obj in bundle["objects"]]
    assert (
        types.count("identity") == 1
    )  # author only -- org Identity is looked up, not created
    assert types.count("marking-definition") == 1
    assert types.count("ipv4-addr") == 2  # 198.51.100.5, 198.51.100.6
    assert types.count("ipv6-addr") == 1  # 2001:db8::5
    assert (
        types.count("vulnerability") == 3
    )  # 2 CVEs + 1 nmap/service_name fallback ("telnet")
    # 3 ticket relationships (the false-positive ticket contributes none) + 3 org->ip
    # relationships (TESTORG1 x2 distinct ips, TESTORG2-CHILD x1)
    assert types.count("relationship") == 6

    # The closed ticket's relationship should carry a stop_time; the two still-open ones shouldn't.
    ticket_rels = [
        obj
        for obj in bundle["objects"]
        if obj["type"] == "relationship"
        and obj.get("target_ref", "").startswith("vulnerability--")
    ]
    assert len(ticket_rels) == 3
    assert sum(1 for rel in ticket_rels if "stop_time" in rel) == 1
    # updated_timestamp must survive fixture -> mapping -> real bundle serialization for every
    # ticket relationship, not just in the unit-level mapping.py tests.
    assert all("x_opencti_updated_timestamp" in rel for rel in ticket_rels)


def test_false_positive_ticket_is_never_sent_and_leaves_no_relationship_recorded():
    """A ticket that's already false_positive=True on first sight is a no-op, not an error."""
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    state = {}

    connector._process(data, state)

    assert "cyhy-ticket-0004" not in state["ticket_relationship_ids"]
    assert (
        connector.helper.api.stix_core_relationship.deleted_ids == []
    )  # never ingested, nothing to revoke


def test_ticket_flipping_to_false_positive_on_a_later_poll_gets_revoked():
    """A previously-ingested ticket that flips false_positive=True must get revoked.

    §7a: the relationship needs to be actually removed, not just silently dropped from future
    bundles.
    """
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    # Make ticket 0004 a normal, real ticket for the first run, so it actually gets ingested.
    ticket_4 = next(t for t in data.tickets if t["id"] == "cyhy-ticket-0004")
    ticket_4["false_positive"] = False
    state = {}

    connector._process(data, state)
    assert "cyhy-ticket-0004" in state["ticket_relationship_ids"]
    recorded_rel_id = state["ticket_relationship_ids"]["cyhy-ticket-0004"]

    # Now it flips to false_positive=True on the next poll.
    ticket_4["false_positive"] = True
    connector._process(data, state)

    assert "cyhy-ticket-0004" not in state["ticket_relationship_ids"]
    assert connector.helper.api.stix_core_relationship.deleted_ids == [recorded_rel_id]


def test_revocation_only_run_sends_no_bundle():
    """A run whose only work is revoking a false positive must send no bundle at all.

    §9 queue discipline: nothing new to add to the graph shouldn't put an author+marking-only
    bundle on the queue.
    """
    # Third-Party Libraries
    from src.db import TicketIngestionData

    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    ticket_4 = next(t for t in data.tickets if t["id"] == "cyhy-ticket-0004")
    ticket_4["false_positive"] = False
    state = {}
    connector._process(data, state)
    sent_before = len(connector.helper.sent_bundles)

    # A later poll where the only ticket in scope this run is 0004, now flipped -- nothing new
    # needs to go out, only a revocation via the API.
    ticket_4_flipped = copy.deepcopy(ticket_4)
    ticket_4_flipped["false_positive"] = True
    connector._process(TicketIngestionData(tickets=[ticket_4_flipped]), state)

    assert len(connector.helper.sent_bundles) == sent_before  # no new bundle sent
    assert "cyhy-ticket-0004" not in state["ticket_relationship_ids"]


def test_relationship_ids_are_stable_across_consecutive_runs():
    """Prove the §10a claim executably: re-running against unchanged data must be a no-op."""
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)

    state = {}
    connector._process(data, state)
    first_run_ticket_rel_ids = dict(state["ticket_relationship_ids"])
    first_run_org_ip_rel_ids = dict(state["org_ip_relationship_ids"])

    connector._process(data, state)

    assert state["ticket_relationship_ids"] == first_run_ticket_rel_ids
    assert state["org_ip_relationship_ids"] == first_run_org_ip_rel_ids


def test_ticket_relationship_id_stays_pinned_when_ticket_closes():
    """Same §10a contract connector D proved for CIDR retirement, here for ticket closure."""
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    open_ticket = next(t for t in data.tickets if t["id"] == "cyhy-ticket-0001")

    state = {}
    connector._process(data, state)
    open_id = state["ticket_relationship_ids"]["cyhy-ticket-0001"]

    # Simulate the ticket closing on the next poll.
    open_ticket["closed_timestamp"] = "2026-08-25T00:00:00+00:00"
    open_ticket["is_open"] = False
    connector._process(data, state)

    closed_id = state["ticket_relationship_ids"]["cyhy-ticket-0001"]
    assert closed_id == open_id  # pinned, as designed

    bundle = json.loads(connector.helper.sent_bundles[-1])
    rel_obj = next(obj for obj in bundle["objects"] if obj.get("id") == closed_id)
    assert (
        "stop_time" in rel_obj
    )  # ...and the content that changed rides along on that same id


def test_process_watermark_is_json_serializable_for_real_datetime_objects():
    """Prove the watermark fix against what psycopg2 actually returns, not just fixture strings.

    Ticket.updated_timestamp/closed_timestamp are timestamptz columns -- psycopg2 hands back real
    datetime.datetime objects on a live run, but every fixture here stores them as already-JSON
    -safe ISO strings. Override with a real datetime the way live data actually looks (same class
    of bug connector D hit -- "Object of type datetime is not JSON serializable" -- caught here
    from day one instead of at full production scale).
    """
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    for ticket in data.tickets:
        ticket["updated_timestamp"] = datetime.datetime(
            2026, 8, 22, 0, 0, tzinfo=datetime.timezone.utc
        )
        ticket["closed_timestamp"] = None

    watermark = connector._process(data, {})

    assert isinstance(watermark, str)
    json.dumps({"last_seen_watermark": watermark})  # must not raise


def test_one_bad_ticket_does_not_abort_the_whole_run():
    """A malformed row must not sink every other ticket in the same run.

    §10e/§10i row-isolation, built in from the start this time -- proven the same way
    connector D's regression was.
    """
    connector = build_test_connector()
    data = connector.repository.fetch(since_last_seen=None)
    data.tickets.append(
        {
            "id": "cyhy-ticket-bad",
            "cve_string": "CVE-2024-0000",
            "vuln_name": None,
            "service_name": None,
            "vuln_source": "nessus",
            "ip_string": "not-a-valid-ip",
            "opened_timestamp": "2026-08-01T00:00:00+00:00",
            "closed_timestamp": None,
            "updated_timestamp": "2026-08-23T00:00:00+00:00",
            "is_open": True,
            "is_kev": False,
            "is_kev_ransomware": False,
            "is_risky": False,
            "false_positive": False,
            "cvss_severity": None,
            "vuln_port": None,
            "port_protocol": None,
            "organization_acronym": "TESTORG1",
            "organization_name": "Test Organization One",
        }
    )

    watermark = connector._process(data, {})

    assert watermark is not None  # the run completed, it didn't raise
    bundle = json.loads(connector.helper.sent_bundles[-1])
    ips_sent = [
        obj["value"]
        for obj in bundle["objects"]
        if obj["type"] in ("ipv4-addr", "ipv6-addr")
    ]
    assert "not-a-valid-ip" not in ips_sent  # the bad one was skipped
    assert "198.51.100.5" in ips_sent  # the good ones still went out


def test_effective_since_is_unbounded_by_default_with_no_watermark():
    """§9c's lookback lever defaults to off -- unchanged behavior from before it existed."""
    connector = build_test_connector()
    assert connector.config.lookback_days is None

    assert connector._effective_since({}) is None


def test_effective_since_bounds_the_first_poll_when_lookback_days_is_set():
    """With no watermark yet, lookback_days bounds the poll to roughly now minus N days."""
    connector = build_test_connector()
    connector.config.lookback_days = 7

    before = datetime.datetime.now(datetime.timezone.utc)
    since = connector._effective_since({})
    after = datetime.datetime.now(datetime.timezone.utc)

    assert since is not None
    since_dt = datetime.datetime.fromisoformat(since)
    # Should land within [before - 7d, after - 7d] -- a tight window around "right now minus 7
    # days", not some other bound.
    assert (
        before - datetime.timedelta(days=7)
        <= since_dt
        <= after - datetime.timedelta(days=7)
    )


def test_effective_since_ignores_lookback_days_once_a_watermark_exists():
    """lookback_days must only ever apply to the first poll, never an in-progress one.

    A rolling lookback bound on every run would silently create a permanent gap -- see
    connector.py's _effective_since docstring.
    """
    connector = build_test_connector()
    connector.config.lookback_days = 7

    since = connector._effective_since(
        {"last_seen_watermark": "2020-01-01T00:00:00+00:00"}
    )

    assert since == "2020-01-01T00:00:00+00:00"


def test_config_lookback_days_empty_string_does_not_crash():
    """An empty (but present) env var must resolve to None, not raise.

    The `${VAR:-}` pattern docker-compose.yml uses for every other optional lever here sets the
    env var to an empty string, not unset -- verified directly against the installed pycti
    source that get_config_variable(isNumber=True) calls int('') before ever checking for an
    empty string, which raises. config.py reads this one manually instead specifically to avoid
    that crash.
    """
    config = Config(
        raw={
            "vs_ticket_ingestion": {
                "org_acronym_allowlist": "TESTORG1",
                "is_local": True,
                "tlp_marking": "TLP:AMBER",
                "lookback_days": "",
            }
        }
    )
    assert config.lookback_days is None


def test_config_lookback_days_parses_a_real_value():
    """A real numeric string must parse to the equivalent int."""
    config = Config(
        raw={
            "vs_ticket_ingestion": {
                "org_acronym_allowlist": "TESTORG1",
                "is_local": True,
                "tlp_marking": "TLP:AMBER",
                "lookback_days": "14",
            }
        }
    )
    assert config.lookback_days == 14


def test_run_marks_only_the_first_poll_as_bootstrap():
    """run() must only mark the very first poll (no watermark yet) as the bootstrap one.

    This is the actual fix for the 413,925-stale-open-ticket gap (§9c/§10i): the lookback bound
    alone only controls what counts as "recent," `include_stale_open` is what keeps
    currently-actionable-but-stale tickets from being permanently excluded. Spies on
    repository.fetch() rather than db.py's SQL directly -- the query-level behavior itself was
    verified against a real postgres:17 container (see connector.py's _effective_since
    docstring and db.py's _fetch_tickets_live comments).
    """
    connector = build_test_connector()
    calls = []
    original_fetch = connector.repository.fetch

    def spying_fetch(since_last_seen, include_stale_open=False):
        calls.append(include_stale_open)
        return original_fetch(since_last_seen, include_stale_open=include_stale_open)

    connector.repository.fetch = spying_fetch

    connector.run()  # no watermark yet -- bootstrap
    connector.run()  # watermark now set -- steady-state

    assert calls == [True, False]
