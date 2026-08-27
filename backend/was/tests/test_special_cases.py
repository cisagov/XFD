"""Tests for WAS special case data access."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.data import special_cases


class FakeCursor:
    """Small cursor test double for special case tests."""

    def __init__(self, row=None, rows=None, rowcount=0):
        """Initialize fake cursor state."""
        self.row = row
        self.rows = rows or []
        self.rowcount = rowcount
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
        """Return one configured row."""
        return self.row

    def fetchall(self):
        """Return configured rows."""
        return self.rows


class FakeConnection:
    """Small connection test double for special case tests."""

    def __init__(self, row=None, rows=None, rowcount=0):
        """Initialize fake connection state."""
        self.cursor_instance = FakeCursor(
            row=row,
            rows=rows,
            rowcount=rowcount,
        )
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


class SpecialCaseTests(unittest.TestCase):
    """Validate WAS special case helpers."""

    def test_normalize_special_case_value_uppercases_value(self) -> None:
        """Normalize special case values for stable matching."""
        value = special_cases.normalize_special_case_value(" crossfeed ")

        self.assertEqual(value, "CROSSFEED")

    def test_list_active_special_case_names_returns_values(self) -> None:
        """List active special case values."""
        conn = FakeConnection(rows=[("CBOE",), ("CROSSFEED",)])

        values = special_cases.list_active_special_case_names(conn)

        self.assertEqual(values, ["CBOE", "CROSSFEED"])
        self.assertIsNone(conn.cursor_instance.parameters)

    def test_upsert_special_case_reactivates_existing_value(self) -> None:
        """Insert or reactivate a special case."""
        conn = FakeConnection(row=(3, "SCCCS", True))

        special_case = special_cases.upsert_special_case(
            value="scccs",
            conn=conn,
        )

        self.assertEqual(special_case.value, "SCCCS")
        self.assertTrue(special_case.active)
        self.assertTrue(conn.committed)
        self.assertIn("ON CONFLICT", conn.cursor_instance.query)

    def test_deactivate_special_case_returns_changed_status(self) -> None:
        """Deactivate one active special case."""
        conn = FakeConnection(rowcount=1)

        changed = special_cases.deactivate_special_case("CBOE", conn)

        self.assertTrue(changed)
        self.assertTrue(conn.committed)
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("CBOE",),
        )


if __name__ == "__main__":
    unittest.main()
