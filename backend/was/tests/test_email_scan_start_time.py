"""Verify customer email dates use the persisted scan start instant only."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock

from was_mailer.message import build_report_email, eastern_timestamp
from was_reports.data.report_runs import get_report_run_email


class EmailScanStartTimeTests(unittest.TestCase):
    """Protect start-time selection and Eastern daylight-saving conversion."""

    def test_customer_email_uses_scan_start_not_scan_completion(self) -> None:
        """Render 05:00 UTC as 01:00 Eastern, without substituting 06:01 completion."""
        start_epoch = int(datetime(2026, 9, 23, 5, tzinfo=timezone.utc).timestamp())
        end_epoch = int(datetime(2026, 9, 23, 6, 1, tzinfo=timezone.utc).timestamp())
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (
            1, "TAG", "/unused/TAG_report_2026-09-23.pdf", None,
            "poc@example.gov", None, "Sample POC", 2, "pdf", "Results",
            "Sample Analyst", None, None, None, None, start_epoch, None, None,
            "customer",
        )
        delivery = get_report_run_email(1, conn)
        query = cursor.execute.call_args.args[0]
        self.assertIn("EXTRACT(EPOCH FROM tracker.scan_started_at)::bigint", query)
        self.assertNotIn("scan_ended_at", query)
        self.assertNotIn("stakeholders.last_scanned", query)
        self.assertEqual(delivery.last_scanned, start_epoch)
        with TemporaryDirectory() as directory:
            report = Path(directory) / "TAG_report_2026-09-23.pdf"
            report.write_bytes(b"%PDF test-only attachment")
            message = build_report_email(
                "reports@example.gov", ["poc@example.gov"], "TAG", report,
                poc_name=delivery.was_report_poc, last_scanned=delivery.last_scanned,
            )
        for subtype in ("plain", "html"):
            with self.subTest(subtype=subtype):
                body = message.get_body(preferencelist=(subtype,)).get_content()
                self.assertIn("September 23, 2026 at 01:00 AM Eastern Time", body)
                self.assertNotIn(eastern_timestamp(end_epoch), body)
                self.assertNotIn("completed at", body)

    def test_eastern_time_respects_daylight_saving_and_standard_time(self) -> None:
        """Use the timezone offset applicable to each stored UTC instant."""
        cases = (
            (datetime(2026, 9, 23, 5, tzinfo=timezone.utc),
             "September 23, 2026 at 01:00 AM Eastern Time"),
            (datetime(2026, 12, 23, 5, tzinfo=timezone.utc),
             "December 23, 2026 at 12:00 AM Eastern Time"),
            (datetime(2026, 9, 23, 2, tzinfo=timezone.utc),
             "September 22, 2026 at 10:00 PM Eastern Time"),
        )
        for instant, expected in cases:
            with self.subTest(instant=instant):
                self.assertEqual(eastern_timestamp(int(instant.timestamp())), expected)

    def test_missing_start_is_not_invented_from_calendar_date(self) -> None:
        """Missing launch timestamps remain explicitly unavailable."""
        self.assertEqual(eastern_timestamp(None), "Not available")
