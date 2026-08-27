"""Tests for WAS tracker assignment helpers."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.tracker.assignments import round_robin_assignee


class AssignmentTests(unittest.TestCase):
    """Validate WAS assignment distribution helpers."""

    def test_round_robin_assignee_splits_evenly(self) -> None:
        """Assign rows evenly across assignees."""
        assignees = ["A", "B", "C"]

        assignments = [
            round_robin_assignee(assignees, item_index)
            for item_index in range(8)
        ]

        self.assertEqual(assignments, ["C", "B", "A", "C", "B", "A", "C", "B"])

    def test_round_robin_assignee_can_preserve_order(self) -> None:
        """Assign rows in supplied order when reverse order is disabled."""
        assignees = ["A", "B", "C"]

        assignments = [
            round_robin_assignee(
                assignees,
                item_index,
                reverse_order=False,
            )
            for item_index in range(5)
        ]

        self.assertEqual(assignments, ["A", "B", "C", "A", "B"])

    def test_round_robin_assignee_rejects_empty_assignees(self) -> None:
        """Reject assignment when no assignees exist."""
        with self.assertRaises(ValueError):
            round_robin_assignee([], 0)

    def test_round_robin_assignee_rejects_negative_index(self) -> None:
        """Reject negative item indexes."""
        with self.assertRaises(ValueError):
            round_robin_assignee(["A"], -1)


if __name__ == "__main__":
    unittest.main()
