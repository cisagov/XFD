"""Tests for WAS tracker CLI utilities."""

# Standard Python Libraries
from contextlib import redirect_stdout
import csv
from datetime import date, datetime, timedelta, timezone
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import tracker_cli
from was_reports.data.daily_report_tracker import DailyReportTrackerRow, TrackerTableRow
from was_reports.data.report_runs import ReportRunError
from was_reports.tracker.tracker_csv import (
    CSV_HEADERS,
    tracker_row_to_csv,
    write_tracker_csv,
)


class TrackerCliTests(unittest.TestCase):
    """Validate tracker CSV export helpers."""

    def test_tracker_row_to_csv_preserves_daily_tracker_order(self) -> None:
        """Map database rows to legacy tracker CSV column order."""
        row = DailyReportTrackerRow(
            data_pull_date=date(2026, 8, 26),
            tag="TAG1",
            scan_name="Scan 1",
            assignee="Analyst",
            status="Finished",
            result="Successful",
            report_sent_date=date(2026, 8, 27),
            report_scan_notes="Sent",
            scan_start_date=date(2026, 8, 25),
            next_scan_date=date(2026, 9, 25),
            poc="POC",
            poc_email="poc@example.gov",
            customer_notes="Notes",
            nws="1",
            template="Results",
            recent_nws="",
            remove_nws="",
            legacy_password="STATIC PASSWORD",
            schedule_id=123,
            qualys_error=None,
        )

        values = tracker_row_to_csv(row)

        self.assertEqual(values[0], date(2026, 8, 26))
        self.assertEqual(values[1], "TAG1")
        self.assertEqual(values[3], "Analyst")
        self.assertEqual(values[17], "STATIC PASSWORD")
        self.assertEqual(values[18], 123)

    def test_write_tracker_csv_writes_headers_and_rows(self) -> None:
        """Write tracker rows as CSV."""
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "tracker.csv"
            row = DailyReportTrackerRow(
                data_pull_date=date(2026, 8, 26),
                tag="TAG1",
                scan_name="Scan 1",
            )

            write_tracker_csv(rows=[row], output_path=output_path)

            with output_path.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.reader(csv_file))

        self.assertEqual(rows[0], CSV_HEADERS)
        self.assertEqual(rows[1][0], "2026-08-26")
        self.assertEqual(rows[1][1], "TAG1")

    @patch("was_reports.commands.tracker_cli.write_tracker_csv")
    @patch("was_reports.commands.tracker_cli.list_tracker_rows_for_export_from_db")
    def test_export_csv_queries_database_and_writes_file(
        self,
        mock_list_rows,
        mock_write_csv,
    ) -> None:
        """Export tracker rows from the database."""
        mock_list_rows.return_value = [DailyReportTrackerRow(tag="TAG1")]
        args = tracker_cli.parse_args(
            [
                "export-csv",
                "--data-pull-date",
                "2026-08-26",
                "--assignee-id",
                "3",
                "--limit",
                "10",
                "--output",
                "/tmp/tracker.csv",
            ]
        )

        exit_code = tracker_cli.export_csv(args)

        self.assertEqual(exit_code, 0)
        mock_list_rows.assert_called_once_with(
            data_pull_date=date(2026, 8, 26),
            assignee_id=3,
            days_back=None,
            assignee_name=None,
            limit=10,
        )
        mock_write_csv.assert_called_once()

    @patch("was_reports.commands.tracker_cli.write_tracker_csv")
    @patch("was_reports.commands.tracker_cli.list_tracker_rows_for_export_from_db")
    def test_export_csv_filters_by_assignee_and_days(
        self,
        mock_list_rows,
        mock_write_csv,
    ) -> None:
        """Export a recent CSV for one exact assignee name."""
        mock_list_rows.return_value = [DailyReportTrackerRow(tag="TAG1")]
        args = tracker_cli.parse_args(
            [
                "export-csv",
                "--days-back",
                "7",
                "--assignee",
                "Mina Salehi",
                "--output",
                "/tmp/tracker.csv",
            ]
        )

        exit_code = tracker_cli.export_csv(args)

        self.assertEqual(exit_code, 0)
        mock_list_rows.assert_called_once_with(
            data_pull_date=None,
            assignee_id=None,
            days_back=7,
            assignee_name="Mina Salehi",
            limit=None,
        )
        mock_write_csv.assert_called_once()

    @patch("was_reports.commands.tracker_cli.list_tracker_table_rows_from_db")
    def test_show_table_displays_live_assignee_rows(self, mock_list_rows) -> None:
        """Display recent Postgres tracker data without creating a CSV."""
        mock_list_rows.return_value = [
            TrackerTableRow(
                tracker_id=7,
                data_pull_date=date(2026, 9, 1),
                tag="TAG1",
                scan_name="Scan 1",
                assignee="Analyst",
                scan_status="Finished",
                scan_result="Successful",
                report_status="SENT",
                report_sent_date=date(2026, 9, 1),
                notes=None,
                next_scan_date=date(2026, 9, 29),
            )
        ]
        args = tracker_cli.parse_args(
            [
                "show",
                "--days-back",
                "14",
                "--assignee",
                "Analyst",
                "--limit",
                "50",
            ]
        )
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = tracker_cli.show_table(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("TAG1", output.getvalue())
        self.assertIn("Displayed 1 tracker rows.", output.getvalue())
        mock_list_rows.assert_called_once_with(
            days_back=14,
            assignee_name="Analyst",
            report_status=None,
            limit=50,
        )

    @patch("was_reports.commands.tracker_cli.list_tracker_table_rows_from_db")
    def test_show_table_filters_manual_reports(self, mock_list_rows) -> None:
        """Request only tracker rows requiring manual handling."""
        mock_list_rows.return_value = []
        args = tracker_cli.parse_args(
            ["show", "--days-back", "7", "--report-status", "manual"]
        )

        exit_code = tracker_cli.show_table(args)

        self.assertEqual(exit_code, 0)
        mock_list_rows.assert_called_once_with(
            days_back=7,
            assignee_name=None,
            report_status="MANUAL",
            limit=200,
        )

    @patch("was_reports.commands.tracker_cli.list_report_run_errors_from_db")
    def test_show_errors_displays_persisted_failure(self, mock_list_errors) -> None:
        """Display persisted report failures without requiring runtime logs."""
        mock_list_errors.return_value = [
            ReportRunError(
                id=42,
                stakeholder_tag="TAG1",
                status="failed",
                email_status="pending",
                started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                completed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                error_message="Report generation failed.",
                email_error=None,
            )
        ]
        args = tracker_cli.parse_args(
            ["errors", "--days-back", "14", "--tag", "TAG1", "--limit", "25"]
        )
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = tracker_cli.show_errors(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("Report generation failed.", output.getvalue())
        self.assertIn("Displayed 1 report errors.", output.getvalue())
        mock_list_errors.assert_called_once_with(
            days_back=14,
            stakeholder_tag="TAG1",
            limit=25,
        )

    @patch(
        "was_reports.commands.tracker_cli.mark_manual_tracker_report_sent_by_id"
    )
    def test_mark_sent_updates_manual_tracker_row(self, mock_mark_sent) -> None:
        """Record a confirmed sent date for one manual tracker row."""
        args = tracker_cli.parse_args(
            [
                "mark-sent",
                "--tracker-id",
                "7",
                "--sent-date",
                "2026-09-02",
                "--confirm",
            ]
        )

        exit_code = tracker_cli.mark_sent(args)

        self.assertEqual(exit_code, 0)
        mock_mark_sent.assert_called_once_with(
            tracker_id=7,
            sent_date=date(2026, 9, 2),
        )

    def test_show_rejects_negative_days_back(self) -> None:
        """Reject an invalid negative tracker history window."""
        with self.assertRaises(SystemExit):
            tracker_cli.parse_args(
                [
                    "show",
                    "--days-back",
                    "-1",
                    "--assignee",
                    "Analyst",
                ]
            )

    def test_mark_sent_rejects_future_date(self) -> None:
        """Reject an accidental future manual report sent date."""
        future_date = date.today() + timedelta(days=1)

        with self.assertRaises(SystemExit):
            tracker_cli.parse_args(
                [
                    "mark-sent",
                    "--tracker-id",
                    "7",
                    "--sent-date",
                    future_date.isoformat(),
                    "--confirm",
                ]
            )


if __name__ == "__main__":
    unittest.main()
