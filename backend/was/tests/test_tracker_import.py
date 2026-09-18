"""Tests for combined daily tracker workbook conversion and import."""

# Standard Python Libraries
from datetime import date, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
from openpyxl import Workbook

# First-Party Libraries
from was_reports.tracker import tracker_import


def workbook_row(
    tag: str = "TAG1",
    assignee: str = "Analyst",
    report_sent_date: object = "09/09/2026",
    scan_start_date: object = "09/08/2026",
    schedule_id: object = 12345,
) -> tuple[object, ...]:
    """Return one representative legacy tracker workbook row."""
    return (
        "09/09/2026",
        tag,
        "WAVS - TAG1 - Monthly Run #1",
        assignee,
        "Finished",
        "Successful",
        report_sent_date,
        None,
        scan_start_date,
        "10/08/2026",
        "Customer POC",
        "poc@example.gov",
        None,
        "2",
        "Results",
        None,
        None,
        "STATIC PASSWORD",
        schedule_id,
        None,
    )


class TrackerImportTests(unittest.TestCase):
    """Validate conversion and duplicate-safe tracker imports."""

    def test_workbook_values_convert_dates_and_columns(self) -> None:
        """Map the legacy workbook row to the tracker database model."""
        row = tracker_import.workbook_values_to_row(workbook_row())

        self.assertEqual(row.data_pull_date, date(2026, 9, 9))
        self.assertEqual(row.report_sent_date, date(2026, 9, 9))
        self.assertEqual(row.scan_start_date, date(2026, 9, 8))
        self.assertEqual(row.next_scan_date, date(2026, 10, 8))
        self.assertEqual(row.schedule_id, 12345)
        self.assertEqual(row.legacy_password, "STATIC PASSWORD")

    def test_non_date_report_value_moves_to_notes(self) -> None:
        """Preserve legacy report-status text outside the date column."""
        row = tracker_import.workbook_values_to_row(
            workbook_row(report_sent_date="MANUAL")
        )

        self.assertIsNone(row.report_sent_date)
        self.assertEqual(
            row.report_scan_notes,
            "Legacy Report Sent Date value: MANUAL",
        )

    def test_read_workbook_validates_headers_and_skips_blank_rows(self) -> None:
        """Read the first worksheet and identify fully blank rows."""
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "tracker.xlsx"
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.append(list(tracker_import.WORKBOOK_HEADERS))
            worksheet.append([None] * len(tracker_import.WORKBOOK_HEADERS))
            worksheet.append(list(workbook_row()))
            workbook.save(input_path)

            rows = list(tracker_import.read_workbook_rows(input_path))

        self.assertEqual(rows[0], (2, ()))
        self.assertEqual(rows[1][0], 3)
        self.assertEqual(rows[1][1][1], "TAG1")

    def test_existing_rows_only_loads_legacy_imports(self) -> None:
        """Do not let XLSX imports overwrite live Qualys tracker rows."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchmany.side_effect = [
            [(91,) + workbook_row()],
            [],
        ]

        rows = tracker_import.existing_tracker_rows(connection)

        import_row = tracker_import.workbook_values_to_row(workbook_row())
        self.assertEqual(
            rows,
            {tracker_import.tracker_import_key(import_row): (91,)},
        )
        self.assertIn(
            "scan_execution_key LIKE 'legacy-import:%'",
            cursor.execute.call_args.args[0],
        )

    def test_existing_rows_rejects_unreconciled_legacy_duplicates(self) -> None:
        """Require cleanup before an import can overwrite ambiguous rows."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchmany.side_effect = [
            [(91,) + workbook_row(), (92,) + workbook_row()],
            [],
        ]

        with self.assertRaisesRegex(ValueError, "require reconciliation"):
            tracker_import.existing_tracker_rows(connection)

    @patch("was_reports.tracker.tracker_import.update_converted_rows")
    @patch("was_reports.tracker.tracker_import.insert_converted_rows")
    @patch("was_reports.tracker.tracker_import.read_workbook_rows")
    @patch("was_reports.tracker.tracker_import.assignee_identifiers")
    @patch("was_reports.tracker.tracker_import.existing_tracker_rows")
    @patch("was_reports.tracker.tracker_import.close")
    @patch("was_reports.tracker.tracker_import.connect")
    def test_import_overwrites_existing_and_workbook_duplicates(
        self,
        mock_connect,
        mock_close,
        mock_existing,
        mock_assignees,
        mock_read_rows,
        mock_insert,
        mock_update,
    ) -> None:
        """Overwrite matching executions and insert only unique new rows."""
        connection = MagicMock()
        mock_connect.return_value = connection
        stored_values = workbook_row(tag="BEFORE")
        existing_row = tracker_import.workbook_values_to_row(stored_values)
        mock_existing.return_value = {tracker_import.tracker_import_key(existing_row): (91,)}
        mock_assignees.return_value = {"analyst": 8}
        updated_values = workbook_row(tag="AFTER")
        new_values = workbook_row(schedule_id=12346)
        unknown_values = workbook_row(
            tag="UNKNOWN",
            assignee="Former Analyst",
            schedule_id=12347,
        )
        mock_read_rows.return_value = iter(
            [
                (2, updated_values),
                (3, new_values),
                (4, new_values),
                (5, unknown_values),
                (6, ()),
            ]
        )
        mock_insert.return_value = 2
        mock_update.return_value = 1

        result = tracker_import.import_tracker_workbook(Path("tracker.xlsx"))

        self.assertEqual(result.source_rows, 4)
        self.assertEqual(result.inserted_rows, 2)
        self.assertEqual(result.updated_rows, 1)
        self.assertEqual(result.workbook_duplicates, 1)
        self.assertEqual(result.database_duplicates, 0)
        self.assertEqual(result.blank_rows, 1)
        self.assertEqual(result.unknown_assignees, ("Former Analyst",))
        inserted_values = list(mock_insert.call_args.args[1])
        self.assertEqual(inserted_values[0][3], 8)
        self.assertEqual(inserted_values[1][3], None)
        self.assertTrue(inserted_values[0][20].startswith("legacy-import:"))
        self.assertEqual(inserted_values[0][22], "held")
        self.assertIn("status_callback", mock_insert.call_args.kwargs)
        staged_updates = list(mock_update.call_args.args[1])
        self.assertEqual(len(staged_updates), 1)
        self.assertEqual(staged_updates[0][1], "AFTER")
        self.assertEqual(staged_updates[0][-1], 91)
        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        mock_close.assert_called_once_with(connection)

    @patch("was_reports.tracker.tracker_import.read_workbook_rows")
    @patch("was_reports.tracker.tracker_import.assignee_identifiers")
    @patch("was_reports.tracker.tracker_import.existing_tracker_rows")
    @patch("was_reports.tracker.tracker_import.close")
    @patch("was_reports.tracker.tracker_import.connect")
    def test_import_rolls_back_invalid_row(
        self,
        mock_connect,
        mock_close,
        mock_existing,
        mock_assignees,
        mock_read_rows,
    ) -> None:
        """Roll back the complete import when one row cannot be converted."""
        connection = MagicMock()
        mock_connect.return_value = connection
        mock_existing.return_value = {}
        mock_assignees.return_value = {}
        invalid_values = list(workbook_row())
        invalid_values[0] = "not-a-date"
        mock_read_rows.return_value = iter([(22, tuple(invalid_values))])

        with self.assertRaisesRegex(ValueError, "Workbook row 22"):
            tracker_import.import_tracker_workbook(Path("tracker.xlsx"))

        connection.rollback.assert_called_once_with()
        connection.commit.assert_not_called()
        mock_close.assert_called_once_with(connection)

    def test_fingerprint_is_stable_for_equivalent_dates(self) -> None:
        """Produce the same key after equivalent workbook date conversion."""
        string_row = tracker_import.workbook_values_to_row(workbook_row())
        datetime_values = list(workbook_row())
        datetime_values[0] = datetime(2026, 9, 9, 14, 30)
        datetime_row = tracker_import.workbook_values_to_row(datetime_values)

        self.assertEqual(
            tracker_import.tracker_fingerprint(string_row),
            tracker_import.tracker_fingerprint(datetime_row),
        )

    def test_import_key_distinguishes_recurring_schedule_executions(self) -> None:
        """Treat separate run dates for one recurring schedule as separate rows."""
        first_row = tracker_import.workbook_values_to_row(workbook_row())
        second_row = tracker_import.workbook_values_to_row(
            workbook_row(scan_start_date="10/08/2026")
        )

        self.assertNotEqual(
            tracker_import.tracker_import_key(first_row),
            tracker_import.tracker_import_key(second_row),
        )

    def test_import_key_ignores_fields_that_workbook_can_overwrite(self) -> None:
        """Match an execution when imported business data has changed."""
        original_row = tracker_import.workbook_values_to_row(
            workbook_row(tag="OLD")
        )
        changed_row = tracker_import.workbook_values_to_row(
            workbook_row(tag="UPDATED", assignee="New Analyst")
        )

        self.assertEqual(
            tracker_import.tracker_import_key(original_row),
            tracker_import.tracker_import_key(changed_row),
        )
        self.assertNotEqual(
            tracker_import.tracker_fingerprint(original_row),
            tracker_import.tracker_fingerprint(changed_row),
        )

    @patch("was_reports.tracker.tracker_import.execute_values")
    def test_update_preserves_stored_sent_date_when_import_is_blank(
        self,
        mock_execute_values,
    ) -> None:
        """Do not erase delivery history when the XLSX sent date is blank."""
        mock_execute_values.return_value = [(91,)]
        row = tracker_import.workbook_values_to_row(
            workbook_row(report_sent_date=None)
        )
        values = tracker_import.database_values(
            row,
            assignee_id=8,
            fingerprint=tracker_import.tracker_fingerprint(row),
        )
        update_values = tuple(
            values[tracker_import.DATABASE_COLUMNS.index(column)]
            for column in tracker_import.IMPORT_UPDATE_COLUMNS
        ) + (91,)

        updated_count = tracker_import.update_converted_rows(
            MagicMock(),
            [update_values],
        )

        self.assertEqual(updated_count, 1)
        query = mock_execute_values.call_args.args[1]
        self.assertIn(
            "COALESCE(imported.report_sent_date, tracker.report_sent_date)",
            query,
        )

    @patch("was_reports.tracker.tracker_import.execute_values")
    def test_insert_uses_atomic_conflict_overwrite(
        self,
        mock_execute_values,
    ) -> None:
        """Overwrite XLSX fields if a canonical import key already exists."""
        mock_execute_values.return_value = [(91,)]
        row = tracker_import.workbook_values_to_row(workbook_row())
        values = tracker_import.database_values(
            row,
            assignee_id=8,
            fingerprint=tracker_import.tracker_fingerprint(row),
        )

        inserted_count = tracker_import.insert_converted_rows(
            MagicMock(),
            [values],
        )

        self.assertEqual(inserted_count, 1)
        query = mock_execute_values.call_args.args[1]
        self.assertIn("DO UPDATE SET", query)
        self.assertIn(
            "COALESCE(EXCLUDED.report_sent_date, "
            "was_daily_report_tracker.report_sent_date)",
            query,
        )


if __name__ == "__main__":
    unittest.main()
