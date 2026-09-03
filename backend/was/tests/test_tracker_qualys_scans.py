"""Tests for production tracker Qualys discovery helpers."""

# Standard Python Libraries
import unittest

# Third-Party Libraries
from lxml import etree

# First-Party Libraries
from was_reports.tracker.models import TrackerStakeholder
from was_reports.tracker.qualys_scans import (
    base_stakeholder_tag,
    normalize_schedule_name,
    parse_stakeholder_schedule_name,
    response_count,
    response_has_more_records,
    scan_matches_stakeholder,
)


class TrackerQualysScansTests(unittest.TestCase):
    """Validate tracker schedule parsing and matching."""

    def test_normalize_schedule_name_replaces_unicode_dash(self) -> None:
        """Normalize schedule punctuation without regular expressions."""
        normalized = normalize_schedule_name("WAVS – TAG -- Customer")

        self.assertEqual(normalized, "WAVS - TAG - Customer")

    def test_parse_stakeholder_schedule_name(self) -> None:
        """Extract the stakeholder tag and name from a schedule name."""
        tag, name = parse_stakeholder_schedule_name(
            "WAVS - CROSSFEED - Crossfeed Program - Monthly"
        )

        self.assertEqual(tag, "CROSSFEED")
        self.assertEqual(name, "Crossfeed Program")

    def test_base_stakeholder_tag_removes_adhoc_suffix(self) -> None:
        """Resolve the primary tag from an ad hoc child tag."""
        self.assertEqual(base_stakeholder_tag("CROSSFEED_ADHOC"), "CROSSFEED")

    def test_response_pagination_fields(self) -> None:
        """Parse Qualys pagination metadata defensively."""
        root = etree.fromstring(
            b"<ServiceResponse><count>50</count>"
            b"<hasMoreRecords>true</hasMoreRecords></ServiceResponse>"
        )

        self.assertEqual(response_count(root), 50)
        self.assertTrue(response_has_more_records(root))

    def test_scan_matches_expected_stakeholder_and_cadence(self) -> None:
        """Match a scan only to its stakeholder and configured cadence."""
        stakeholder = TrackerStakeholder(
            name="Crossfeed Program",
            tag_id=1,
            next_scan_date="2026-09-10T00:00:00Z",
            launched_date="2026-09-01T00:00:00Z",
            schedule_id=2,
            cadence="MONTHLY",
        )

        self.assertTrue(
            scan_matches_stakeholder(
                "WAVS - CROSSFEED - Crossfeed Program - Monthly Run #1",
                "CROSSFEED",
                stakeholder,
            )
        )
        self.assertFalse(
            scan_matches_stakeholder(
                "WAVS - CROSSFEED - Crossfeed Program - Ad-Hoc Run #1",
                "CROSSFEED",
                stakeholder,
            )
        )


if __name__ == "__main__":
    unittest.main()
