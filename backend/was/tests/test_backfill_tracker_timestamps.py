"""Verify preview-only default, exact matching, and guarded timestamp backfill."""

from dataclasses import replace
from datetime import date, datetime, timezone
import unittest
from unittest.mock import MagicMock, patch

from lxml import etree

from was_reports.commands import backfill_tracker_timestamps as backfill


class BackfillTests(unittest.TestCase):
    """Exercise all external boundaries with deterministic test doubles."""

    def setUp(self):
        """Create one precise candidate and actual scan record."""
        self.start = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
        self.end = datetime(2026, 9, 1, 13, tzinfo=timezone.utc)
        self.candidate = backfill.TimestampCandidate(
            7, 4, "TAG", "WAVS - TAG - Customer Run #1", date(2026, 9, 1), "key", None, None
        )
        self.scan = etree.fromstring(
            "<WasScan><id>123</id><name>WAVS - TAG - Customer Run #1</name>"
            "<status>FINISHED</status><multi>true</multi>"
            "<launchedDate>2026-09-01T12:00:00Z</launchedDate>"
            "<endScanDate>2026-09-01T13:00:00Z</endScanDate></WasScan>"
        )

    def test_conflicts_ambiguity_and_wrong_tag_are_skipped(self):
        """Never fill an end against conflicting existing start or ambiguous scan."""
        for candidate, scans in (
            (replace(self.candidate, scan_started_at=self.end), [self.scan]),
            (replace(self.candidate, tag="OTHER"), [self.scan]),
            (self.candidate, [self.scan, self.scan]),
            (self.candidate, []),
        ):
            self.assertIsNone(backfill.proposed_timestamps(candidate, scans, (self.start, self.end)))
        self.assertEqual(backfill.proposed_timestamps(
            self.candidate, [self.scan], (self.start, self.end)
        ), (self.start, self.end))

    @patch.object(backfill, "load_candidates")
    def test_apply_requires_explicit_match_confirmation_before_connections(self, load):
        """Operator approval of unverified schedule mapping cannot be implicit."""
        with self.assertRaisesRegex(ValueError, "confirm-name-date-matches"):
            backfill.run_backfill(date(2026, 9, 1), None, 100, apply=True)
        load.assert_not_called()

    @patch.object(backfill, "apply_proposals")
    @patch.object(backfill, "create_qualys_client")
    @patch.object(backfill, "search_matching_scans")
    @patch.object(backfill, "load_candidates")
    def test_default_preview_never_writes(self, load, search, client, apply):
        """A preview reports exact proposed values but never enters write path."""
        load.return_value = [self.candidate]
        search.return_value = {(self.candidate.scan_name, self.candidate.scan_start_date): [self.scan]}
        result = backfill.run_backfill(date(2026, 9, 1), None, 100)
        self.assertEqual(result["proposed"], 1)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["next_after_id"], 7)
        self.assertEqual(result["proposals"][0][1:], (self.start, self.end))
        apply.assert_not_called()

    @patch.object(backfill, "close")
    @patch.object(backfill, "connect")
    def test_conditional_update_preserves_concurrent_changes(self, connect, close):
        """Optimistic guards skip changed identities and commit only matching rows."""
        connection = connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        self.assertEqual(backfill.apply_proposals([(self.candidate, self.start, self.end)]), [])
        query = cursor.execute.call_args.args[0]
        for field in ("scan_execution_key", "scan_started_at", "scan_ended_at", "scan_name"):
            self.assertIn("{} IS NOT DISTINCT FROM".format(field), query)
        self.assertIn("COALESCE(scan_started_at", query)
        connection.commit.assert_called_once()
        cursor.execute.side_effect = RuntimeError("failure")
        with self.assertRaises(RuntimeError):
            backfill.apply_proposals([(self.candidate, self.start, self.end)])
        connection.rollback.assert_called_once()

    def test_search_skips_slices_and_requires_success(self):
        """Only explicit parent/single exact named same-day scans may match."""
        client = MagicMock()
        client.request.return_value = (
            "<ServiceResponse><responseCode>SUCCESS</responseCode><count>1</count>"
            "<data>{}</data></ServiceResponse>"
        ).format(etree.tostring(self.scan, encoding="unicode"))
        matches = backfill.search_matching_scans(client, date(2026, 9, 1), date(2026, 9, 1),
                                                 {self.candidate.scan_name})
        self.assertEqual(len(matches), 1)
        payload = etree.fromstring(client.request.call_args.args[0].payload.encode())
        self.assertEqual(payload.findtext("./preferences/limitResults"), "1000")
        client.request.return_value = "<ServiceResponse><responseCode>FAILURE</responseCode></ServiceResponse>"
        with self.assertRaises(RuntimeError):
            backfill.search_matching_scans(client, date(2026, 9, 1), date(2026, 9, 1), set())
