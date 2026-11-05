"""Loop 2 (OpenCTI-connector.md §9b): the real lookup->map->bundle pipeline against fixtures.

Uses a stub in place of OpenCTIConnectorHelper so no network/queue is touched at all. Calls
`connector.process_message()` directly with a synthetic event dict shaped exactly like what
pycti's `ListenQueue._data_handler` hands a real INTERNAL_ENRICHMENT connector (confirmed
against the installed pycti source) -- this *is* the dry-run equivalent of a real "Enrich" click,
since `listen()` itself just blocks on RabbitMQ and can't be exercised here.
"""

# Standard Python Libraries
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Third-Party Libraries
from pycti import Vulnerability as OpenCTIVulnerability  # noqa: E402
from pycti.utils.opencti_logger import logger as pycti_logger  # noqa: E402
import pytest  # noqa: E402

# First-Party
from src.config import Config  # noqa: E402
from src.connector import VsVulnscanEnrichmentConnector  # noqa: E402
import stix2  # noqa: E402

# stix2 validates id shape strictly (<type>--<uuid>) -- these need to be real, well-formed ids
# for anything that becomes a Note's object_refs entry (found by running these tests, same
# lesson as connector A's test_mapping.py).
_IP_ENTITY_ID = stix2.IPv4Address(value="198.51.100.5").id
_VULN_ENTITY_ID = stix2.Vulnerability(
    id=OpenCTIVulnerability.generate_id("CVE-2024-1234"), name="CVE-2024-1234"
).id


class StubHelper:
    """Just enough of OpenCTIConnectorHelper's surface for process_message() to run against.

    connector_logger deliberately uses pycti's *real* AppLogger, not a plain stdlib
    logging.getLogger() -- same reasoning as connectors A/D's stubs (§10i): a stdlib logger
    would silently tolerate call-signature mistakes this dry-run test is specifically meant to
    catch.
    """

    def __init__(self):
        """Start with empty capture state -- nothing sent yet, no state stored yet."""
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


class FailingSendHelper(StubHelper):
    """StubHelper whose send_stix2_bundle() raises instead of capturing, on demand.

    Models the failed-send/retry path: `fail_sends` starts True so the first
    process_message() call fails after state has already been read but before any bundle
    is actually accepted, then flips to False so a subsequent retry goes through normally.
    """

    def __init__(self):
        """Start in failing mode -- the first send this test drives must raise."""
        super().__init__()
        self.fail_sends = True

    def send_stix2_bundle(self, bundle, **kwargs):
        """Raise instead of capturing while `fail_sends` is set, else behave like the base stub."""
        if self.fail_sends:
            raise RuntimeError("simulated OpenCTI bundle submission failure")
        return super().send_stix2_bundle(bundle, **kwargs)


def build_test_connector(helper=None):
    """Build a VsVulnscanEnrichmentConnector wired to fixtures and the given (or a fresh) stub."""
    config = Config(
        raw={
            "vs_vulnscan_enrichment": {
                "is_local": True,
                "local_fixture_dir": os.path.join(
                    os.path.dirname(__file__), "fixtures"
                ),
                "tlp_marking": "TLP:AMBER",
            }
        }
    )
    return VsVulnscanEnrichmentConnector(config=config, helper=helper or StubHelper())


def _ip_event(entity_id=_IP_ENTITY_ID):
    """Build a synthetic enrichment event dict shaped like pycti's real ListenQueue output."""
    return {
        "entity_id": entity_id,
        "entity_type": "IPv4-Addr",
        "stix_entity": {"id": entity_id, "type": "ipv4-addr", "value": "198.51.100.5"},
    }


def _vulnerability_event(entity_id=_VULN_ENTITY_ID):
    """Build a synthetic enrichment event dict for a Vulnerability-type trigger."""
    return {
        "entity_id": entity_id,
        "entity_type": "Vulnerability",
        "stix_entity": {
            "id": entity_id,
            "type": "vulnerability",
            "name": "CVE-2024-1234",
        },
    }


def test_ip_entity_enrichment_produces_a_note_with_both_matched_findings():
    """198.51.100.5 matches both fixture rows -- both must show up in one Note."""
    connector = build_test_connector()

    message = connector.process_message(_ip_event())

    assert "2 VS scanner finding" in message
    assert len(connector.helper.sent_bundles) == 1
    bundle = json.loads(connector.helper.sent_bundles[0])
    notes = [obj for obj in bundle["objects"] if obj["type"] == "note"]
    assert len(notes) == 1
    assert "Example Remote Code Execution" in notes[0]["content"]
    assert "Weak Telnet Auth" in notes[0]["content"]


def test_vulnerability_entity_enrichment_matches_only_the_right_cve():
    """CVE-2024-1234 should only pull in the one fixture row for that CVE, not both."""
    connector = build_test_connector()

    message = connector.process_message(_vulnerability_event())

    assert "1 VS scanner finding" in message
    bundle = json.loads(connector.helper.sent_bundles[-1])
    notes = [obj for obj in bundle["objects"] if obj["type"] == "note"]
    assert "Example Remote Code Execution" in notes[0]["content"]
    assert "Weak Telnet Auth" not in notes[0]["content"]


def test_no_matching_vuln_scans_sends_no_bundle():
    """§9 queue discipline: nothing found means nothing worth putting on the queue."""
    connector = build_test_connector()
    event = _ip_event()
    event["stix_entity"]["value"] = "203.0.113.9"  # matches no fixture row

    message = connector.process_message(event)

    assert "No VS scanner-level detail found" in message
    assert connector.helper.sent_bundles == []


def test_note_id_stays_pinned_across_repeated_enrichment():
    """§10a: re-enriching the same entity must update the same Note, not create a new one."""
    connector = build_test_connector()

    connector.process_message(_ip_event())
    first_note_id = connector.helper.get_state()["note_ids"][_IP_ENTITY_ID]

    connector.process_message(_ip_event())
    second_note_id = connector.helper.get_state()["note_ids"][_IP_ENTITY_ID]

    assert first_note_id == second_note_id


def test_failed_send_does_not_pin_a_note_id_and_retry_still_succeeds():
    """A failed send_stix2_bundle() must not leave state pointing at a Note that was never created.

    Otherwise a retry reuses that id assuming the object already exists (the bug this test
    guards against: state was previously persisted before the send was confirmed).
    """
    helper = FailingSendHelper()
    connector = build_test_connector(helper=helper)

    with pytest.raises(RuntimeError):
        connector.process_message(_ip_event())

    # The failed attempt must not have pinned a note id -- nothing was actually created.
    assert helper.get_state().get("note_ids", {}).get(_IP_ENTITY_ID) is None
    assert helper.sent_bundles == []

    # A retry (send now succeeding) must go through cleanly and pin a note id afterwards.
    helper.fail_sends = False
    message = connector.process_message(_ip_event())

    assert "2 VS scanner finding" in message
    assert len(helper.sent_bundles) == 1
    assert helper.get_state()["note_ids"][_IP_ENTITY_ID] is not None


def test_unexpected_entity_type_raises_rather_than_silently_no_ops():
    """A scope mismatch is a configuration problem worth surfacing, not swallowing."""
    connector = build_test_connector()
    event = {
        "entity_id": "domain-name--x",
        "entity_type": "Domain-Name",
        "stix_entity": {"value": "example.com"},
    }
    with pytest.raises(ValueError):
        connector.process_message(event)
