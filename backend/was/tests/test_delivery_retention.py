"""Checks for the delivery-review retention command and safe row selection."""

# Standard Python Libraries
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
import unittest
from unittest.mock import patch

# Third-Party Libraries
from was_reports.commands import delivery_retention as retention_command
from was_reports.data import delivery_retention


class DeliveryRetentionTests(unittest.TestCase):
    """Verify preview safety and the configured 14-day cutoff."""

    def test_preview_does_not_apply_cleanup(self) -> None:
        """Keep the command read-only without the explicit apply flag."""
        counts = {
            "expired_retries": 2,
            "recipient_copies": 3,
            "event_recipient_copies": 4,
        }
        with patch.object(retention_command, "retention_counts", return_value=counts):
            with patch.object(retention_command, "apply_retention") as apply_cleanup:
                with redirect_stdout(StringIO()) as output:
                    self.assertEqual(retention_command.main([]), 0)
        apply_cleanup.assert_not_called()
        self.assertIn("Preview 14-day delivery retention", output.getvalue())
        self.assertNotIn("example.gov", output.getvalue())

    def test_apply_requires_flag_and_uses_fixed_cutoff(self) -> None:
        """Apply only when requested, using the approved 14-day period."""
        counts = {
            "expired_retries": 1,
            "recipient_copies": 1,
            "event_recipient_copies": 1,
        }
        with patch.object(retention_command, "apply_retention", return_value=counts):
            with patch.object(retention_command, "retention_counts") as preview:
                with redirect_stdout(StringIO()) as output:
                    self.assertEqual(retention_command.main(["--apply"]), 0)
        preview.assert_not_called()
        self.assertIn("Applied 14-day delivery retention", output.getvalue())
        cutoff = delivery_retention.retention_cutoff()
        cutoff_age = datetime.now(timezone.utc) - cutoff
        self.assertGreaterEqual(cutoff_age, timedelta(days=14))
        self.assertLess(cutoff_age, timedelta(days=14, minutes=1))
