"""Read-only schedule parity harness regression tests."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

from lxml.builder import E
from lxml import etree

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compare_tracker_selection.py"
SPEC = importlib.util.spec_from_file_location("compare_tracker_selection", SCRIPT)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def schedule(identifier: int, tag: str, status: str = "FINISHED") -> str:
    """Build a schedule response with all required selection fields."""
    return etree.tostring(E.WasScanSchedule(
        E.id(str(identifier)), E.name("Monthly - {} - Example - Scan".format(tag)),
        E.type("VULNERABILITY"),
        E.lastScan(E.launchedDate("2026-09-17T12:00:00Z"), E.status(status)),
        E.scheduling(E.occurrenceType("MONTHLY")),
        E.nextLaunchDate("2026-10-17T12:00:00Z"),
        E.target(E.tags(E.included(E.tagList(E.list(E.Tag(E.id(str(identifier))))))))
    ), encoding="unicode")


class ComparisonTests(unittest.TestCase):
    """Compare real selection functions without live connections."""

    def test_legacy_excludes_recorded_schedule_and_running(self):
        """Expose the two known candidate differences with shared inputs."""
        snapshot = {"anchor": "2026-09-18T00:00:00+00:00",
                    "tracker_rows": [[1, "2026-09-16", "2026-09-17"]],
                    "schedules": [schedule(1, "OLD"), schedule(2, "NEW"),
                                  schedule(3, "RUN", "RUNNING")]}
        result = HARNESS.compare(snapshot, 2)
        self.assertEqual(result["legacy_tags"], 1)
        self.assertEqual(result["current_executions"], 3)
        self.assertEqual(result["both_tag_schedule_pairs"], 1)
        excluded = {item["tag"]: item for item in result["current_only"]}
        self.assertTrue(excluded["OLD"]["legacy_excluded_schedule_id"])
        self.assertFalse(excluded["OLD"]["same_scan_day_recorded"])

    def test_replay_refuses_other_endpoints(self):
        """Prevent accidental use of non-allowlisted operations."""
        with self.assertRaises(ValueError):
            HARNESS.ReplayClient([]).request("delete/was/webapp")

    def test_date_boundary_and_missing_projected_type(self):
        """Exclude exact midnight while honoring server's omitted type guarantee."""
        record = etree.fromstring(schedule(2, "NEW").encode())
        record.remove(record.find("type"))
        record.find("./lastScan/launchedDate").text = "2026-09-17T00:00:00Z"
        client = HARNESS.ReplayClient([etree.tostring(record, encoding="unicode")])
        request = E.ServiceRequest(E.filters(
            E.Criteria("2026-09-17", field="lastScan.launchedDate", operator="GREATER"),
            E.Criteria("VULNERABILITY", field="type", operator="EQUALS")))
        response = etree.fromstring(client.request("search/was/wasscanschedule", request).encode())
        self.assertEqual(response.findtext("count"), "0")
        request.find("./filters/Criteria").text = "2026-09-16"
        response = etree.fromstring(client.request("search/was/wasscanschedule", request).encode())
        self.assertEqual(response.findtext("count"), "1")

    def test_private_output_does_not_overwrite(self):
        """Protect snapshots and prevent silent replacement of evidence."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            HARNESS.save_private(output, {"safe": True})
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                HARNESS.save_private(output, {})
