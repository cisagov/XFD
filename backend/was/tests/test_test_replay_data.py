"""Regression tests for isolated report replay persistence."""

import unittest
from unittest.mock import MagicMock, patch

from was_reports.data import test_replay


class ReplayDataTests(unittest.TestCase):
    """Ensure previews do not write and reservations preserve originals."""

    def setUp(self):
        """Install deterministic database boundaries."""
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.connect_patch = patch.object(test_replay, "connect", return_value=self.connection)
        self.close_patch = patch.object(test_replay, "close")
        self.connect_patch.start()
        self.close_patch.start()
        self.addCleanup(self.connect_patch.stop)
        self.addCleanup(self.close_patch.stop)
        self.candidate = test_replay.ReplayCandidate(
            1, "TAG", "resend", 2, "/archive/report.pdf", 3, "Customer", None)
        self.replay_id = "12345678-1234-1234-1234-123456789abc"

    def test_preview_is_read_only(self):
        """Preview excludes test originals and does not commit."""
        self.cursor.fetchall.return_value = []
        self.assertEqual([], test_replay.list_replay_candidates(7, (1,)))
        query, parameters = self.cursor.execute.call_args.args
        self.assertEqual((7, False, [1]), parameters)
        self.assertIn("runs.delivery_purpose = 'customer'", query)
        self.assertIn("Deactivated", query)
        self.assertIn("runs.email_status NOT IN ('held', 'sending', 'sent')", query)
        self.connection.commit.assert_not_called()

    def test_new_resend_is_separate_analyst_run(self):
        """Atomic child insert leaves original tracker and delivery history unchanged."""
        self.cursor.fetchone.side_effect = [("test@example.gov",), None, ("TAG",), ("TAG",), (9,)]
        report, created = test_replay.reserve_replay_run(
            self.replay_id, "test@example.gov", self.candidate)
        self.assertTrue(created)
        self.assertEqual(9, report.id)
        queries = [call.args[0] for call in self.cursor.execute.call_args_list]
        insert = next(query for query in queries if "INSERT INTO was_report_runs" in query)
        self.assertIn("'analyst'", insert)
        self.assertNotIn("source_tracker_id", insert)
        self.assertFalse(any("UPDATE was_daily_report_tracker" in query for query in queries))
        self.connection.commit.assert_called_once()

    def test_repeated_reservation_reuses_child(self):
        """A repeated UUID and source cannot generate or send a second child."""
        self.cursor.fetchone.side_effect = [
            ("test@example.gov",),
            (9, "TAG", "completed", "/archive/report.pdf", "pdf", "token", "resend", 2),
        ]
        report, created = test_replay.reserve_replay_run(
            self.replay_id, "test@example.gov", self.candidate)
        self.assertFalse(created)
        self.assertEqual(9, report.id)

    def test_recipient_cannot_change(self):
        """Replay UUID is bound to the original test destination."""
        self.cursor.fetchone.return_value = ("other@example.gov",)
        with self.assertRaisesRegex(ValueError, "different recipient"):
            test_replay.reserve_replay_run(self.replay_id, "test@example.gov", self.candidate)
        self.connection.rollback.assert_called_once()

    def test_stale_source_aborts(self):
        """Revalidate source eligibility inside the child transaction."""
        self.cursor.fetchone.side_effect = [("test@example.gov",), None, ("TAG",), None]
        with self.assertRaisesRegex(ValueError, "no longer eligible"):
            test_replay.reserve_replay_run(self.replay_id, "test@example.gov", self.candidate)
        self.connection.rollback.assert_called_once()

    def test_manual_cannot_overlap_active_generation(self):
        """Use the stakeholder lock before checking live generation ownership."""
        manual = test_replay.ReplayCandidate(1, "TAG", "manual", 2, None, 3, "Customer", None)
        self.cursor.fetchone.side_effect = [("test@example.gov",), None, ("TAG",), (42,)]
        with self.assertRaisesRegex(ValueError, "operation is active"):
            test_replay.reserve_replay_run(self.replay_id, "test@example.gov", manual)
        self.connection.rollback.assert_called_once()
        queries = [call.args[0] for call in self.cursor.execute.call_args_list]
        self.assertTrue(any("FOR UPDATE" in query and "was_stakeholders" in query
                            for query in queries))

    def test_existing_replay_cannot_change_action(self):
        """Do not reinterpret an existing manual child as a resend reservation."""
        self.cursor.fetchone.side_effect = [
            ("test@example.gov",),
            (9, "TAG", "completed", "/archive/report.pdf", "pdf", "token", "manual", 2),
        ]
        with self.assertRaisesRegex(ValueError, "source/action differs"):
            test_replay.reserve_replay_run(self.replay_id, "test@example.gov", self.candidate)

    def test_bad_window_does_not_connect(self):
        """Reject invalid lookback windows before any database access."""
        with self.assertRaises(ValueError):
            test_replay.list_replay_candidates(0)
        self.connection.cursor.assert_not_called()
