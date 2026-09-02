"""Tests for WAS stakeholder data access."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.data import stakeholders


class FakeCursor:
    """Small cursor test double for stakeholder operations."""

    def __init__(self, row=None, rows=None):
        """Initialize configured query results."""
        self.row = row
        self.rows = rows or []
        self.query = None
        self.parameters = None

    def __enter__(self):
        """Return this cursor for context manager usage."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the cursor context manager."""

    def execute(self, query, parameters=None):
        """Capture the executed query and parameters."""
        self.query = query
        self.parameters = parameters

    def fetchone(self):
        """Return one configured row."""
        return self.row

    def fetchall(self):
        """Return configured rows."""
        return self.rows


class FakeConnection:
    """Small connection test double for stakeholder operations."""

    def __init__(self, row=None, rows=None):
        """Initialize fake connection state."""
        self.cursor_instance = FakeCursor(row=row, rows=rows)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        """Return the fake cursor."""
        return self.cursor_instance

    def commit(self):
        """Record transaction commit."""
        self.committed = True

    def rollback(self):
        """Record transaction rollback."""
        self.rolled_back = True


class StakeholderDataTests(unittest.TestCase):
    """Validate stakeholder maintenance and export helpers."""

    def test_update_stakeholder_contacts_updates_only_selected_fields(self) -> None:
        """Update selected contacts with parameterized values."""
        conn = FakeConnection(row=("TAG1",))

        stakeholders.update_stakeholder_contacts(
            tag=" TAG1 ",
            updates={
                "was_report_poc": "Analyst Name",
                "distro_email": "distro@example.gov",
            },
            conn=conn,
        )

        self.assertTrue(conn.committed)
        self.assertIn("distro_email = %s", conn.cursor_instance.query)
        self.assertIn("was_report_poc = %s", conn.cursor_instance.query)
        self.assertNotIn("report_password", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            ("distro@example.gov", "Analyst Name", "TAG1"),
        )

    def test_list_stakeholders_for_export_excludes_password_by_default(self) -> None:
        """Keep report passwords out of normal stakeholder exports."""
        conn = FakeConnection(rows=[("TAG1",)])

        columns, rows = stakeholders.list_stakeholders_for_export(conn=conn)

        self.assertEqual(rows, [("TAG1",)])
        self.assertNotIn("report_password", columns)
        self.assertNotIn("report_password", conn.cursor_instance.query)
        self.assertIn("ORDER BY tag ASC", conn.cursor_instance.query)

    def test_list_stakeholders_for_export_can_include_password(self) -> None:
        """Support an explicitly authorized complete stakeholder export."""
        conn = FakeConnection(rows=[])

        columns, _ = stakeholders.list_stakeholders_for_export(
            conn=conn,
            include_report_passwords=True,
        )

        self.assertIn("report_password", columns)
        self.assertIn("report_password", conn.cursor_instance.query)


if __name__ == "__main__":
    unittest.main()
