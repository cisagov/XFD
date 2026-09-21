"""Regression tests for the standalone read-only overlap experiment."""

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/inspect_schedule_overlaps.py"
SPECIFICATION = importlib.util.spec_from_file_location("overlap_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(AUDIT)


class OverlapClassificationTests(unittest.TestCase):
    """Ensure test deliveries and unresolved work are not called customer delivered."""

    def row(self, **changes: object) -> dict:
        """Build a complete, unsent example without sensitive fields."""
        result = dict(run_status=None, email_status=None, has_notes=False, sent=False,
                      emailed=False, delivery_purpose=None, status="Finished", result="Successful")
        result.update(changes)
        return result

    def test_unsent_completed_tracker_is_not_delivered(self) -> None:
        """Finished scanning does not mean email delivery."""
        self.assertEqual(AUDIT.classify([self.row()]), "tracker_complete_unsent")

    def test_customer_and_analyst_deliveries_differ(self) -> None:
        """Analyst tests must not be counted as successful customer delivery."""
        for purpose, expected in (("customer", "delivery_recorded"),
                                  ("analyst", "other_linked_report_run")):
            record = self.row(run_status="completed", emailed=True, delivery_purpose=purpose)
            self.assertEqual(AUDIT.classify([record]), expected)

    def test_unresolved_operations_remain_separate(self) -> None:
        """Failed, active, held, and noted records need different treatment."""
        examples = (({"run_status": "failed"}, "failed_report_or_delivery"),
                    ({"email_status": "sending"}, "active_report_run"),
                    ({"email_status": "held"}, "held_delivery"),
                    ({"has_notes": True}, "notes_require_review"),
                    ({"status": "Running"}, "incomplete_or_unknown"))
        for changes, expected in examples:
            self.assertEqual(AUDIT.classify([self.row(**changes)]), expected)

    def test_multiple_rows_and_missing_rows_are_not_handled(self) -> None:
        """A schedule-day collision must not become an automatic skip."""
        self.assertEqual(AUDIT.classify([]), "no_matching_day")
        self.assertEqual(AUDIT.classify([self.row(), self.row()]), "ambiguous_multiple_rows")
