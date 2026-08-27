"""Tests for WAS assignee data access."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.data import assignees


class FakeCursor:
    """Small cursor test double for assignee tests."""

    def __init__(self, row=None):
        """Initialize captured query state."""
        self.row = row
        self.query = None
        self.parameters = None

    def __enter__(self):
        """Return this cursor for context manager usage."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""

    def execute(self, query, parameters=None):
        """Capture query and parameters."""
        self.query = query
        self.parameters = parameters

    def fetchone(self):
        """Return the configured row."""
        return self.row

    def fetchall(self):
        """Return the configured rows."""
        return self.row


class FakeConnection:
    """Small connection test double for assignee tests."""

    def __init__(self, row=None):
        """Initialize fake connection state."""
        self.cursor_instance = FakeCursor(row=row)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        """Return the fake cursor."""
        return self.cursor_instance

    def commit(self):
        """Record commit usage."""
        self.committed = True

    def rollback(self):
        """Record rollback usage."""
        self.rolled_back = True


class AssigneeTests(unittest.TestCase):
    """Validate assignee persistence helpers."""

    def test_normalize_assignee_name_rejects_empty_value(self) -> None:
        """Reject blank assignee names."""
        with self.assertRaises(ValueError):
            assignees.normalize_assignee_name(" ")

    def test_get_assignee_by_name_returns_assignee(self) -> None:
        """Read an assignee by normalized name."""
        conn = FakeConnection(row=(3, "Mina Salehi", "mina@example.gov", True, True))

        assignee = assignees.get_assignee_by_name(" Mina Salehi ", conn)

        self.assertEqual(assignee.id, 3)
        self.assertEqual(assignee.name, "Mina Salehi")
        self.assertEqual(assignee.email, "mina@example.gov")
        self.assertEqual(conn.cursor_instance.parameters, ("Mina Salehi",))

    def test_get_assignee_by_name_returns_none_when_missing(self) -> None:
        """Return none when an assignee is not present."""
        conn = FakeConnection(row=None)

        assignee = assignees.get_assignee_by_name("New Person", conn)

        self.assertIsNone(assignee)

    def test_upsert_assignee_returns_inserted_or_existing_assignee(self) -> None:
        """Insert or return an existing assignee."""
        conn = FakeConnection(row=(7, "Tenesa Ellis", None, True, True))

        assignee = assignees.upsert_assignee(" Tenesa Ellis ", conn)

        self.assertEqual(assignee.id, 7)
        self.assertEqual(assignee.name, "Tenesa Ellis")
        self.assertTrue(conn.committed)
        self.assertIn("ON CONFLICT", conn.cursor_instance.query)
        self.assertEqual(conn.cursor_instance.parameters, ("Tenesa Ellis", None))

    def test_list_active_assignee_names_orders_by_database_id(self) -> None:
        """Return active assignee names in database order."""
        conn = FakeConnection(row=[("Mina Salehi",), ("Tenesa Ellis",)])

        names = assignees.list_active_assignee_names(conn)

        self.assertEqual(names, ["Mina Salehi", "Tenesa Ellis"])
        self.assertIn("ORDER BY id ASC", conn.cursor_instance.query)


if __name__ == "__main__":
    unittest.main()
