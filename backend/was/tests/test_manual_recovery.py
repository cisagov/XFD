"""Tests for guarded recovery of resolved historical report failures."""

# Standard Python Libraries
import unittest
from unittest.mock import MagicMock, patch

# First-Party Libraries
from was_reports.data import manual_recovery


def eligible_state(note: str, password: str = "Valid, password-with spaces") -> tuple:
    """Return a database row satisfying every recovery guard."""
    return (
        "TAG1",
        note,
        None,
        "Finished",
        None,
        "schedule:123:2026-09-24T01:00:00Z",
        password,
        False,
        False,
        77,
        "failed",
        "failed",
        None,
        "ValueError occurred during report generation.",
        "customer",
        True,
        True,
        True,
        True,
    )


class ManualRecoveryTests(unittest.TestCase):
    """Enforce all recovery safety boundaries."""

    def test_password_recovery_accepts_intentionally_allowed_characters(self) -> None:
        """Allow existing spaces, commas, and hyphens without changing the value."""
        note = next(iter(manual_recovery.FAILURE_NOTES[manual_recovery.PASSWORD_VALIDATION]))
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = eligible_state(note)

        result = manual_recovery.check_manual_report_recovery(
            conn, 42, manual_recovery.PASSWORD_VALIDATION
        )

        self.assertTrue(result.eligible)
        self.assertEqual(result.report_run_id, 77)
        query = cursor.execute.call_args.args[0]
        self.assertIn("NOT EXISTS", query)

    def test_preview_does_not_lock_rows(self) -> None:
        """Keep the default eligibility preview read-only."""
        note = next(iter(manual_recovery.FAILURE_NOTES[manual_recovery.QUALYS_READ_TIMEOUT]))
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = eligible_state(note)
        manual_recovery.check_manual_report_recovery(
            conn, 42, manual_recovery.QUALYS_READ_TIMEOUT
        )
        self.assertNotIn("FOR UPDATE", cursor.execute.call_args.args[0])
        conn.commit.assert_not_called()

    def test_mismatched_note_is_blocked(self) -> None:
        """Do not use a selected cause to bypass an unrelated manual reason."""
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = eligible_state("MANUAL")
        result = manual_recovery.check_manual_report_recovery(
            conn, 42, manual_recovery.PASSWORD_VALIDATION
        )
        self.assertFalse(result.eligible)
        self.assertIn("failure note", result.reason)

    def test_held_or_uncertain_run_is_blocked(self) -> None:
        """Require reconciliation rather than retrying uncertain side effects."""
        note = next(iter(manual_recovery.FAILURE_NOTES[manual_recovery.QUALYS_READ_TIMEOUT]))
        for index, value in (
            (11, "held"),
            (13, "QualysReportCreationUncertainError"),
        ):
            with self.subTest(index=index):
                state = list(eligible_state(note))
                state[index] = value
                conn = MagicMock()
                cursor = conn.cursor.return_value.__enter__.return_value
                cursor.fetchone.return_value = tuple(state)
                result = manual_recovery.check_manual_report_recovery(
                    conn, 42, manual_recovery.QUALYS_READ_TIMEOUT
                )
                self.assertFalse(result.eligible)

    def test_claim_reuses_run_and_clears_only_exact_failure_note(self) -> None:
        """Reclaim the same run and remove only the verified blocker atomically."""
        note = next(iter(manual_recovery.FAILURE_NOTES[manual_recovery.PASSWORD_VALIDATION]))
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            eligible_state(note),
            (77, "TAG1", "running"),
            (42,),
        ]

        result = manual_recovery.claim_manual_report_recovery(
            conn, 42, manual_recovery.PASSWORD_VALIDATION
        )

        self.assertEqual(result.id, 77)
        self.assertEqual(result.status, "running")
        conn.commit.assert_called_once_with()
        queries = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn("FOR UPDATE OF tracker, stakeholders, runs", queries[0])
        self.assertIn("emailed_at IS NULL", queries[1])
        self.assertIn("email_status", queries[1])
        self.assertIn("report_scan_notes = %s", queries[2])
        self.assertEqual(cursor.execute.call_args_list[2].args[1], (42, note))

    @patch("was_reports.data.manual_recovery._fetch_recovery_state")
    def test_claim_rolls_back_when_state_changes(self, fetch_state) -> None:
        """Do not partially reclaim a row that fails atomic revalidation."""
        state = list(eligible_state("MANUAL"))
        fetch_state.return_value = tuple(state)
        conn = MagicMock()
        self.assertIsNone(
            manual_recovery.claim_manual_report_recovery(
                conn, 42, manual_recovery.PASSWORD_VALIDATION
            )
        )
        conn.rollback.assert_called_once_with()
        conn.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
