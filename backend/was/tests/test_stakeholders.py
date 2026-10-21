"""Tests for WAS stakeholder data access."""

# Standard Python Libraries
import unittest
from unittest.mock import ANY, call, patch

# Third-Party Libraries
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

    def test_stakeholder_tag_candidates_preserve_longest_parent_first(self) -> None:
        """Resolve nested child tags from the most specific boundary first."""
        self.assertEqual(
            stakeholders.stakeholder_tag_candidates(" PARENT_REGION_CHILD "),
            ("PARENT_REGION_CHILD", "PARENT_REGION", "PARENT"),
        )

    @patch.object(stakeholders, "get_stakeholder_details")
    def test_governing_stakeholder_uses_explicit_parent(self, get_details) -> None:
        """Honor a configured parent before attempting underscore inference."""
        child = stakeholders.StakeholderDetails(
            tag="PARENT_CHILD",
            parent_tag="PARENT",
        )
        parent = stakeholders.StakeholderDetails(tag="PARENT")
        get_details.side_effect = [child, parent]

        result = stakeholders.get_governing_stakeholder_details(
            "PARENT_CHILD", FakeConnection()
        )

        self.assertIs(result, parent)
        self.assertEqual(
            get_details.call_args_list,
            [
                call("PARENT_CHILD", ANY),
                call("PARENT", ANY),
            ],
        )

    @patch.object(stakeholders, "get_stakeholder_details")
    def test_governing_stakeholder_uses_longest_existing_prefix(
        self, get_details
    ) -> None:
        """Keep an enrolled underscore parent intact for an unenrolled child."""
        governing = stakeholders.StakeholderDetails(tag="PARENT_REGION")
        get_details.side_effect = [None, governing]

        result = stakeholders.get_governing_stakeholder_details(
            "PARENT_REGION_CHILD", FakeConnection()
        )

        self.assertIs(result, governing)
        self.assertEqual(get_details.call_count, 2)

    @patch.object(stakeholders, "get_stakeholder_details")
    def test_governing_stakeholder_preserves_restrictive_child_flags(
        self, get_details
    ) -> None:
        """Keep child manual and retired controls while using parent contacts."""
        child = stakeholders.StakeholderDetails(
            tag="ROOT_CHILD",
            parent_tag="ROOT",
            manual_report=True,
            retired=True,
        )
        root = stakeholders.StakeholderDetails(tag="ROOT", fceb=True)
        get_details.side_effect = [child, root]

        result = stakeholders.get_governing_stakeholder_details(
            "ROOT_CHILD", FakeConnection()
        )

        self.assertEqual(result.tag, "ROOT")
        self.assertTrue(result.manual_report)
        self.assertTrue(result.retired)
        self.assertTrue(result.fceb)
        self.assertEqual(get_details.call_count, 2)

    def test_create_stakeholder_takes_deletion_safety_lock(self) -> None:
        """Coordinate a new exact stakeholder with an active child deletion."""
        values: dict[str, object] = {
            column_name: None
            for column_name in stakeholders.STAKEHOLDER_CREATE_COLUMNS
            if column_name != "report_password"
        }
        values["tag"] = "TAG1"
        values["state"] = "DC"
        conn = FakeConnection(row=("TAG1",))

        with patch.object(stakeholders, "validate_required_fields"), patch.object(
            stakeholders,
            "validate_email_value",
        ), patch.object(
            stakeholders,
            "generate_report_password",
            return_value="generated-password",
        ), patch.object(
            stakeholders, "lock_tracker_tag"
        ) as lock_tag:
            created_tag = stakeholders.create_stakeholder(values, conn)

        self.assertEqual(created_tag, "TAG1")
        lock_tag.assert_called_once_with(conn, "TAG1")

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

    def test_get_stakeholder_record_masks_report_password(self) -> None:
        """Display all stakeholder columns without exposing the PDF password."""
        row = tuple(
            "<configured>" if column == "report_password" else column
            for column in stakeholders.STAKEHOLDER_VIEW_COLUMNS
        )
        conn = FakeConnection(row=row)

        record = stakeholders.get_stakeholder_record(" TAG1 ", conn)

        self.assertEqual(record["report_password"], "<configured>")
        self.assertIn(
            "THEN '<missing>' ELSE '<configured>' END AS report_password",
            conn.cursor_instance.query,
        )
        self.assertEqual(conn.cursor_instance.parameters, ("TAG1",))

    def test_update_stakeholder_fields_updates_only_allowlisted_columns(self) -> None:
        """Parameterize selected business-field updates and refresh updated_at."""
        conn = FakeConnection(row=("TAG1",))

        with patch.object(stakeholders, "lock_tracker_tag") as lock_tag:
            stakeholders.update_stakeholder_fields(
                tag=" TAG1 ",
                updates={"comments": None, "retired": True, "state": "OK"},
                conn=conn,
            )

        self.assertTrue(conn.committed)
        lock_tag.assert_called_once_with(conn, "TAG1")
        self.assertIn("comments = %s", conn.cursor_instance.query)
        self.assertIn("retired = %s", conn.cursor_instance.query)
        self.assertIn("state = %s", conn.cursor_instance.query)
        self.assertIn("updated_at = NOW()", conn.cursor_instance.query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (None, True, "OK", "TAG1"),
        )

    def test_nonsafety_stakeholder_update_does_not_take_deletion_lock(self) -> None:
        """Avoid serializing ordinary metadata changes with external deletion."""
        conn = FakeConnection(row=("TAG1",))

        with patch.object(stakeholders, "lock_tracker_tag") as lock_tag:
            stakeholders.update_stakeholder_fields(
                tag="TAG1",
                updates={"comments": "Updated"},
                conn=conn,
            )

        lock_tag.assert_not_called()

    def test_parent_reassignment_takes_generation_safety_lock(self) -> None:
        """Serialize parent changes with child report generation claims."""
        conn = FakeConnection(row=("TAG1",))

        with patch.object(stakeholders, "lock_tracker_tag") as lock_tag:
            stakeholders.update_stakeholder_fields(
                tag="TAG1",
                updates={"parent_tag": "PARENT"},
                conn=conn,
            )

        lock_tag.assert_called_once_with(conn, "TAG1")

    def test_scan_metadata_keeps_the_newest_parent_or_child_snapshot(self) -> None:
        """Update scan fields only when the incoming scan is newer."""
        conn = FakeConnection()

        stakeholders.update_scan_metadata(
            tag="PARENT",
            last_scanned=1788220800,
            next_scheduled=1790812800,
            num_web_apps=7,
            web_apps_last_updated=1788224400,
            qualys_tag_id=42,
            conn=conn,
        )

        query = str(conn.cursor_instance.query)
        self.assertEqual(
            query.count("last_scanned IS NULL OR last_scanned < %s"),
            4,
        )
        self.assertIn("ELSE last_scanned", query)
        self.assertIn("ELSE next_scheduled", query)
        self.assertIn("ELSE num_web_apps", query)
        self.assertIn("ELSE web_apps_last_updated", query)
        self.assertEqual(
            conn.cursor_instance.parameters,
            (
                1788220800,
                1788220800,
                1788220800,
                1790812800,
                1788220800,
                7,
                1788220800,
                1788224400,
                False,
                42,
                "PARENT",
            ),
        )
        self.assertTrue(conn.committed)

    def test_update_stakeholder_fields_rejects_protected_columns(self) -> None:
        """Prevent general updates to identifiers and report passwords."""
        conn = FakeConnection(row=("TAG1",))

        with self.assertRaisesRegex(ValueError, "protected"):
            stakeholders.update_stakeholder_fields(
                tag="TAG1",
                updates={"report_password": "replacement"},
                conn=conn,
            )

        self.assertFalse(conn.committed)

    def test_update_stakeholder_fields_rejects_invalid_state(self) -> None:
        """Reject invalid state codes before executing an update query."""
        conn = FakeConnection(row=("TAG1",))

        with self.assertRaisesRegex(ValueError, "uppercase"):
            stakeholders.update_stakeholder_fields(
                tag="TAG1",
                updates={"state": "wy"},
                conn=conn,
            )

        self.assertIsNone(conn.cursor_instance.query)
        self.assertFalse(conn.committed)

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
