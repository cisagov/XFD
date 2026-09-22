"""Read-only schedule parity harness regression tests."""

import importlib.util
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

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

    def test_archive_loader_executes_only_pinned_function(self):
        """Never execute archive module setup and reject modified source bytes."""
        source = b"raise RuntimeError('module setup executed')\ndef search_schedules():\n return 7\n"
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "fixture.zip"
            with ZipFile(archive_path, "w") as archive:
                archive.writestr(HARNESS.LEGACY_MEMBER, source)
            with patch.object(HARNESS, "LEGACY_ARCHIVE", archive_path):
                with self.assertRaisesRegex(ValueError, "hash"):
                    HARNESS.load_legacy_function({})
                with patch.object(HARNESS, "LEGACY_SOURCE_SHA256", hashlib.sha256(source).hexdigest()):
                    self.assertEqual(HARNESS.load_legacy_function({})(), 7)

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
        self.assertEqual(result["legacy_provenance"]["baseline_lookback_hours"], 48)
        self.assertEqual(result["legacy_selected"][0]["schedule_id"], 2)
        # The original archive deliberately sets Stakeholder.launched_date to
        # INPUT_DATE, unlike the subsequently modified extracted legacy tree.
        self.assertEqual(result["legacy_selected"][0]["launched_date"], "2026-09-16T00:00:00Z")
        self.assertEqual(len(result["current_selected"]), 3)

    def test_replay_refuses_other_endpoints(self):
        """Prevent accidental use of non-allowlisted operations."""
        with self.assertRaises(ValueError):
            HARNESS.ReplayClient([]).request("delete/was/webapp")

    def test_null_pull_dates_and_exact_tracker_cutoff(self):
        """Null dates never match and same-day rows before cutoff remain excluded."""
        snapshot = {
            "anchor": "2026-09-18T12:00:00+00:00",
            "tracker_rows": [
                [1, "2026-09-17", None],
                [2, "2026-09-17", "2026-09-16"],
                [3, "2026-09-17", "2026-09-16T12:00:00+00:00"],
                [None, None, "2026-09-17"],
            ],
            "schedules": [schedule(1, "NULLDATE"), schedule(2, "BEFORE"), schedule(3, "AT")],
        }
        result = HARNESS.compare(snapshot)
        self.assertEqual({item["tag"] for item in result["legacy_selected"]},
                         {"NULLDATE", "BEFORE"})
        self.assertTrue(result["current_only"][0]["legacy_excluded_schedule_id"])

    def test_empty_legacy_page_reports_failure_not_proven_zero(self):
        """The archived empty-page defect is evidence, not a successful zero count."""
        result = HARNESS.compare({
            "anchor": "2026-09-18T00:00:00+00:00", "tracker_rows": [], "schedules": []
        })
        self.assertFalse(result["legacy_valid"])
        self.assertEqual(result["legacy_evaluation_error"], "AttributeError")
        self.assertIsNone(result["legacy_tags"])
        self.assertIsNone(result["current_only"])
        self.assertEqual(result["current_executions"], 0)

    def test_capture_includes_legacy_date_only_lower_boundary(self):
        """A timed anchor must not truncate schedules from the legacy cutoff day."""
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchall.return_value = []
        client = MagicMock()
        client.request.return_value = "<ServiceResponse><data/></ServiceResponse>"
        with patch.object(HARNESS, "connect", return_value=connection), patch.object(
            HARNESS, "latest_tracker_pull_date",
            return_value=datetime(2026, 9, 18, 12, 30, tzinfo=timezone.utc),
        ), patch.object(HARNESS, "create_qualys_client", return_value=client):
            HARNESS.capture()
        payload = etree.fromstring(client.request.call_args.args[0].payload.encode())
        launch_filter = payload.find("./filters/Criteria[@field='lastScan.launchedDate']")
        self.assertEqual(launch_filter.text, "2026-09-15")
        connection.set_session.assert_called_once_with(
            readonly=True, isolation_level="REPEATABLE READ"
        )

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
