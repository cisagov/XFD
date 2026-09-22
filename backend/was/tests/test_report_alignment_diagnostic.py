"""Read-only alignment capture and offline replay boundary tests."""

from contextlib import redirect_stdout
from dataclasses import asdict
from datetime import date, datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from was_reports.data.daily_report_tracker import TrackerReportCandidate
from was_reports.tracker.models import TrackerStakeholder

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
    SPEC = importlib.util.spec_from_file_location(
        "diagnose_report_alignment", SCRIPTS / "diagnose_report_alignment.py"
    )
    DIAGNOSTIC = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(DIAGNOSTIC)


def captured_snapshot() -> dict:
    """Provide minimal safe captured eligibility metadata."""
    return {
        "schema_version": 1, "transaction_read_only": "on",
        "discovery_days": 3, "report_days": 7, "early_tracker_rows": [],
        "database_timestamp": "2026-09-22T12:00:00+00:00",
        "database_day": "2026-09-22", "captured_at": "2026-09-22T12:00:01+00:00",
        "code_at_capture": {}, "eligible_reports": [
            {"tracker_id": 11, "tag": "OLD", "schedule_id": 1,
             "template": "Results", "scan_start_date": "2026-09-20"},
            {"tracker_id": 12, "tag": "NEW", "schedule_id": 2,
             "template": "Results", "scan_start_date": "2026-09-20"},
            {"tracker_id": 13, "tag": "STORED", "schedule_id": 3,
             "template": "Results", "scan_start_date": "2026-09-20"},
        ], "report_summary": {}, "exclusions": [],
    }


class ReportAlignmentDiagnosticTests(unittest.TestCase):
    """Prevent diagnostic execution from mutating operational state."""

    def test_build_report_keeps_independent_stored_candidates(self):
        """Discovery sets annotate, never remove stored eligible report IDs."""
        stakeholder = TrackerStakeholder(
            "Example", 2, "2026-10-20T12:00:00Z", "2026-09-20T12:00:00Z",
            2, "MONTHLY", "NEW", latest_scan_name="Example Run #2",
        )
        selection = {"execution_key": "execution", **asdict(stakeholder)}
        comparison = {"legacy_selected": [{"tag": "OLD", "schedule_id": 1}],
                      "current_selected": [selection], "legacy_tags": 1}
        with patch.object(DIAGNOSTIC, "compare", return_value=comparison), \
                patch.object(DIAGNOSTIC, "source_fingerprints", return_value={}), \
                patch("was_reports.tracker.service.connect") as connect:
            report = DIAGNOSTIC.build_report(captured_snapshot())
        self.assertEqual([item["tracker_id"] for item in report["eligible_reports"]],
                         [11, 12, 13])
        self.assertEqual(report["legacy_only_after_new_early_filter"], [("OLD", 1)])
        self.assertEqual(report["new_only_after_early_filter"], [("NEW", 2)])
        self.assertTrue(report["eligible_reports"][0]["same_tag_schedule_in_legacy_discovery"])
        self.assertFalse(
            report["eligible_reports"][0]["same_tag_schedule_in_new_pending_discovery"]
        )
        self.assertTrue(
            report["eligible_reports"][1]["same_tag_schedule_in_new_pending_discovery"]
        )
        self.assertIn("not full outcome parity", report["scope"])
        connect.assert_not_called()

    def test_capture_uses_one_readonly_snapshot_and_only_schedule_endpoint(self):
        """Use actual capture orchestration with database and vendor boundaries mocked."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (
            datetime(2026, 9, 22, tzinfo=timezone.utc), date(2026, 9, 22), "on"
        )
        cursor.fetchall.side_effect = [[], [], [(11, date(2026, 9, 20), "Run #2")]]
        candidate = TrackerReportCandidate(
            11, "TAG", date(2026, 9, 21), 2, 1, template="Results",
            remove_nws="PRIVATE_TARGET", qualys_error="PRIVATE_ERROR_TARGET",
        )
        client = MagicMock()
        client.request.return_value = (
            "<ServiceResponse><data><WasScanSchedule><id>2</id><name>Example</name>"
            "<lastScan><name>Example Run #2</name><launchedBy>PRIVATE_USER</launchedBy>"
            "<status>FINISHED</status></lastScan>"
            "<target><password>PRIVATE_CREDENTIAL</password></target>"
            "</WasScanSchedule></data></ServiceResponse>"
        )
        with patch.object(DIAGNOSTIC, "load_legacy_function"), \
                patch.object(DIAGNOSTIC, "connect", return_value=connection) as connect, \
                patch.object(DIAGNOSTIC, "latest_tracker_pull_date",
                             return_value=datetime(2026, 9, 21, tzinfo=timezone.utc)), \
                patch.object(DIAGNOSTIC, "list_ready_report_candidates",
                             return_value=[candidate]), \
                patch.object(DIAGNOSTIC, "inspect_exclusions", return_value=[]), \
                patch.object(DIAGNOSTIC, "source_fingerprints", return_value={}), \
                patch.object(DIAGNOSTIC, "create_qualys_client", return_value=client):
            snapshot = DIAGNOSTIC.capture(7, 3)
        connect.assert_called_once_with()
        connection.set_session.assert_called_once_with(
            readonly=True, isolation_level="REPEATABLE READ"
        )
        connection.commit.assert_not_called()
        connection.close.assert_called_once_with()
        for call in cursor.execute.call_args_list:
            self.assertTrue(call.args[0].lstrip().startswith("SELECT"))
        client.request.assert_called_once()
        self.assertEqual(client.request.call_args.args[0].endpoint,
                         "/search/was/wasscanschedule")
        self.assertNotIn("PRIVATE_TARGET", json.dumps(snapshot))
        self.assertNotIn("PRIVATE_ERROR_TARGET", json.dumps(snapshot))
        self.assertNotIn("PRIVATE_USER", json.dumps(snapshot))
        self.assertNotIn("PRIVATE_CREDENTIAL", json.dumps(snapshot))

    def test_failed_legacy_replay_is_not_reported_as_zero_or_a_difference(self):
        """An archived-code failure leaves comparative conclusions unavailable."""
        comparison = {
            "legacy_selected": [], "current_selected": [], "legacy_tags": None,
            "legacy_valid": False, "legacy_evaluation_error": "AttributeError",
        }
        with patch.object(DIAGNOSTIC, "compare", return_value=comparison):
            report = DIAGNOSTIC.build_report(captured_snapshot())
        self.assertIsNone(report["legacy_only_after_new_early_filter"])
        self.assertIsNone(report["new_only_after_early_filter"])
        self.assertIsNone(report["eligible_reports"][0]["same_tag_schedule_in_legacy_discovery"])

    def test_offline_main_is_private_and_refuses_overwrite(self):
        """Replay cannot connect, instantiate a vendor client, or overwrite results."""
        report = {**captured_snapshot(), "legacy_48_hour_comparison": {"legacy_tags": 1},
                  "early_filter_counts": {}}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "snapshot.json"
            output = Path(directory) / "report.json"
            DIAGNOSTIC.save_private(source, captured_snapshot())
            with patch.object(DIAGNOSTIC, "connect") as connect, \
                    patch.object(DIAGNOSTIC, "create_qualys_client") as client, \
                    patch.object(DIAGNOSTIC, "build_report", return_value=report), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(DIAGNOSTIC.main([
                    "--snapshot", str(source), "--output", str(output)
                ]), 0)
                original = output.read_bytes()
                with self.assertRaises(SystemExit):
                    DIAGNOSTIC.main(["--snapshot", str(source), "--output", str(output)])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(output.read_bytes(), original)
            connect.assert_not_called()
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
