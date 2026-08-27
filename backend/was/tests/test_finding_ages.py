"""Tests for Qualys maximum finding-age retrieval."""

# Standard Python Libraries
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

# First-Party Libraries
from was_reports.qualys import finding_ages

CURRENT_TIME = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)


def finding_response(first_detected: str) -> str:
    """Return a minimal Qualys finding response."""
    return """<ServiceResponse><data><Finding><firstDetectedDate>{}</firstDetectedDate>
</Finding></data></ServiceResponse>""".format(first_detected)


class FindingAgeTests(unittest.TestCase):
    """Validate critical and urgent Qualys finding-age behavior."""

    def test_payload_preserves_legacy_filters(self) -> None:
        """Filter by tag, active statuses, severity, and false-positive state."""
        payload = finding_ages.build_oldest_finding_payload("CUSTOMER", "4")

        self.assertIn("CUSTOMER", payload)
        self.assertIn("ACTIVE, NEW, REOPENED", payload)
        self.assertIn('field="severity"', payload)
        self.assertIn(">4<", payload)
        self.assertIn("FALSE_POSITIVE", payload)
        self.assertIn("<limitResults>1</limitResults>", payload)

    def test_retrieve_finding_ages_returns_independent_values(self) -> None:
        """Calculate critical and urgent ages from separate Qualys responses."""
        client = Mock()
        client.request.side_effect = [
            finding_response("2026-08-17T13:00:00Z"),
            finding_response("2026-08-07T13:00:00Z"),
        ]

        result = finding_ages.retrieve_finding_ages(
            client,
            "CUSTOMER",
            CURRENT_TIME,
        )

        self.assertEqual(result.critical_days, 10)
        self.assertEqual(result.urgent_days, 20)
        self.assertEqual(client.request.call_count, 2)

    def test_missing_severity_returns_zero_without_hiding_other_age(self) -> None:
        """Keep an available age when the other severity has no findings."""
        client = Mock()
        client.request.side_effect = [
            "<ServiceResponse><data /></ServiceResponse>",
            finding_response("2026-08-07T13:00:00Z"),
        ]

        result = finding_ages.retrieve_finding_ages(
            client,
            "CUSTOMER",
            CURRENT_TIME,
        )

        self.assertEqual(result.critical_days, 0)
        self.assertEqual(result.urgent_days, 20)


if __name__ == "__main__":
    unittest.main()
