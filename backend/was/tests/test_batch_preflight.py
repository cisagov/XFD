"""Safety regressions for the counts-only batch inspection command."""

# Standard Python Libraries
import argparse
import unittest
from unittest.mock import MagicMock, patch

# First-Party Libraries
from was_reports.commands import batch_preflight


class BatchPreflightTests(unittest.TestCase):
    """Check window validation and database-enforced read-only inspection."""

    def test_window_values(self) -> None:
        """Allow deliberate unlimited history and reject invalid bounds."""
        self.assertIsNone(batch_preflight.parse_window("all"))
        self.assertEqual(batch_preflight.parse_window("7"), 7)
        for value in ("0", "-1", "invalid"):
            with self.assertRaises(argparse.ArgumentTypeError):
                batch_preflight.parse_window(value)

    @patch.object(batch_preflight, "close")
    @patch.object(batch_preflight, "connect")
    @patch.object(batch_preflight, "inspect_exclusions")
    @patch.object(batch_preflight, "list_ready_report_candidates")
    def test_inspection_sets_readonly_before_queries(
        self, candidates, exclusions, connect, close
    ) -> None:
        """Use a consistent read-only transaction and close it without commit."""
        candidates.return_value = []
        exclusions.return_value = [("already sent", 2)]
        conn = connect.return_value
        candidates.side_effect = lambda *args, **kwargs: (
            self.assertEqual(conn.set_session.call_count, 1) or []
        )
        self.assertEqual(batch_preflight.main(["--days-back", "all"]), 0)
        conn.set_session.assert_called_once_with(
            readonly=True, isolation_level="REPEATABLE READ"
        )
        conn.commit.assert_not_called()
        close.assert_called_once_with(conn)

    def test_exclusions_are_select_only_and_parameterized(self) -> None:
        """Keep tags as parameters and explicitly classify imported overlaps."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [("eligible", 3)]
        self.assertEqual(
            batch_preflight.inspect_exclusions(conn, 7, "TAG"),
            [("eligible", 3)],
        )
        query, parameters = cursor.execute.call_args.args
        self.assertEqual(parameters, ("TAG", "TAG", 7, 7, 7, 7, 7))
        self.assertIn("legacy-import:%%", query)
        self.assertIn("legacy.scan_start_date = tracker.scan_start_date", query)
        self.assertIn("old scans pulled inside window", query)
        self.assertIn("otherwise eligible legacy schedule/date overlap", query)
        self.assertIn("NULL historical key", query)
        self.assertIn("legacy.report_sent_date IS NOT NULL", query)
        self.assertIn("same scan run already claimed or sent", query)
        self.assertIn("sibling.scan_name = tracker.scan_name", query)
        self.assertIn("NOT IN ('finished', 'error')", query)
        for command in ("INSERT ", "UPDATE ", "DELETE ", "LOCK "):
            self.assertNotIn(command, query)


if __name__ == "__main__":
    unittest.main()
