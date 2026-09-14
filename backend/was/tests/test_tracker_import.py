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
        "09/08/2026",
        "10/08/2026",
        "Customer POC",
        "poc@example.gov",
        None,
        "2",
        "Results",
        None,
        None,
        "STATIC PASSWORD",
        12345,
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

    @patch("was_reports.tracker.tracker_import.insert_converted_rows")
    @patch("was_reports.tracker.tracker_import.read_workbook_rows")
    @patch("was_reports.tracker.tracker_import.assignee_identifiers")
    @patch("was_reports.tracker.tracker_import.existing_tracker_fingerprints")
    @patch("was_reports.tracker.tracker_import.close")
    @patch("was_reports.tracker.tracker_import.connect")
    def test_import_skips_existing_and_workbook_duplicates(
        self,
        mock_connect,
        mock_close,
        mock_existing,
        mock_assignees,
        mock_read_rows,
        mock_insert,
    ) -> None:
        """Insert only unique new rows and preserve unknown assignee names."""
        connection = MagicMock()
        mock_connect.return_value = connection
        existing_values = workbook_row(tag="EXISTING")
        existing_row = tracker_import.workbook_values_to_row(existing_values)
        mock_existing.return_value = {
            tracker_import.tracker_fingerprint(existing_row)
        }
        mock_assignees.return_value = {"analyst": 8}
        unknown_values = workbook_row(tag="UNKNOWN", assignee="Former Analyst")
        mock_read_rows.return_value = iter(
            [
                (2, existing_values),
                (3, workbook_row()),
                (4, workbook_row()),
                (5, unknown_values),
                (6, ()),
            ]
        )
        mock_insert.return_value = 2

        result = tracker_import.import_tracker_workbook(Path("tracker.xlsx"))

        self.assertEqual(result.source_rows, 4)
        self.assertEqual(result.inserted_rows, 2)
        self.assertEqual(result.existing_rows, 1)
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
        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        mock_close.assert_called_once_with(connection)

    @patch("was_reports.tracker.tracker_import.read_workbook_rows")
    @patch("was_reports.tracker.tracker_import.assignee_identifiers")
    @patch("was_reports.tracker.tracker_import.existing_tracker_fingerprints")
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
        mock_existing.return_value = set()
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


if __name__ == "__main__":
    unittest.main()
