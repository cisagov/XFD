"""Tests for production tracker Qualys discovery helpers."""

# Standard Python Libraries
from datetime import datetime
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
from lxml import etree
from was_reports.tracker.item_builder import create_multiscan, previous_run_name

# First-Party Libraries
from was_reports.tracker.models import TrackerStakeholder, scheduled_execution_key
from was_reports.tracker.qualys_scans import (
    base_stakeholder_tag,
    get_previous_nws,
    normalize_schedule_name,
    parse_stakeholder_schedule_name,
    parse_xml,
    response_count,
    response_has_more_records,
    scan_matches_stakeholder,
    search_scans,
    search_schedules,
)


class TrackerQualysScansTests(unittest.TestCase):
    """Validate tracker schedule parsing and matching."""

    def test_xml_entities_are_not_expanded(self) -> None:
        """Leave declared entities unresolved rather than exposing their contents."""
        root = parse_xml(
            '<!DOCTYPE response [<!ENTITY private "private-payload">]>'
            "<response>&private;</response>",
            "test parsing",
        )
        self.assertNotIn("private-payload", etree.tostring(root, encoding="unicode"))

    def test_xml_external_entity_is_not_loaded(self) -> None:
        """External network entities remain unresolved without network access."""
        root = parse_xml(
            '<!DOCTYPE response [<!ENTITY remote SYSTEM "https://example.invalid/private">]>'
            "<response>&remote;</response>",
            "test parsing",
        )
        self.assertEqual(root[0].name, "remote")

    def test_malformed_xml_has_bounded_error(self) -> None:
        """Invalid XML raises an operation-only error without response contents."""
        with self.assertRaises(RuntimeError) as raised:
            parse_xml("<private-payload>", "test parsing")
        self.assertEqual(
            str(raised.exception), "Qualys returned invalid XML during test parsing."
        )

    def test_execution_key_normalizes_timezone(self) -> None:
        """Equivalent instants deduplicate without merging separate runs."""
        first = scheduled_execution_key(2, "2026-09-01T00:00:00Z")
        self.assertEqual(first, scheduled_execution_key(2, "2026-08-31T20:00:00-04:00"))
        self.assertNotEqual(first, scheduled_execution_key(2, "2026-09-02T00:00:00Z"))
        with self.assertRaises(ValueError):
            scheduled_execution_key(2, "2026-09-01T00:00:00")

    @patch("was_reports.tracker.qualys_scans.get_tag_id", return_value="1")
    def test_recurring_schedule_uses_actual_launch(self, mock_tag) -> None:
        """Previously recorded schedules remain eligible for later executions."""
        client = Mock()
        client.request.return_value = (
            "<ServiceResponse><data><WasScanSchedule><id>2</id>"
            "<name>WAVS - TAG - Customer - Monthly</name>"
            "<lastScan><launchedDate>2026-09-03T00:00:00Z</launchedDate></lastScan>"
            "<nextLaunchDate>2026-10-03T00:00:00Z</nextLaunchDate>"
            "</WasScanSchedule></data></ServiceResponse>"
        )
        candidates = search_schedules(client, datetime(2026, 9, 1), {2})
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            next(iter(candidates.values())).launched_date, "2026-09-03T00:00:00Z"
        )

    def test_separate_executions_for_same_tag(self) -> None:
        """Different actual launches produce distinct groups for the same tag."""
        client = Mock()
        client.request.return_value = "<ServiceResponse><data>{}</data></ServiceResponse>".format(
            "".join(
                "<WasScan><name>WAVS - TAG - Customer - Monthly Run #{} Slice 1</name>"
                "<status>FINISHED</status><launchedDate>2026-09-0{}T00:00:00Z</launchedDate></WasScan>".format(
                    number, number
                )
                for number in (1, 2)
            )
        )
        stakeholders = {
            "TAG": TrackerStakeholder(
                "Customer",
                1,
                "2026-10-01T00:00:00Z",
                "2026-09-02T00:00:00Z",
                2,
                "MONTHLY",
                "TAG",
                "WAVS - TAG - Customer - Monthly",
            )
        }
        groups = search_scans(client, stakeholders, datetime(2026, 9, 1))
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(len(scans) == 1 for scans in groups.values()))
        client.request.return_value = client.request.return_value.replace(
            "<status>FINISHED</status>", "<status>RUNNING</status>", 1
        )
        groups = search_scans(client, stakeholders, datetime(2026, 9, 1))
        self.assertEqual(len(groups), 1)

    def test_previous_run_matches_full_name(self) -> None:
        """Run one must not match run ten or another schedule."""
        previous = previous_run_name("WAVS - TAG - Customer - Monthly Run #2")
        client = Mock()
        client.request.return_value = "<ServiceResponse><data>{}</data></ServiceResponse>".format(
            "".join(
                "<WasScan><name>{}</name><summary><resultsStatus>NO_WEB_SERVICE</resultsStatus>"
                "</summary><target><webApp><url>{}</url></webApp></target></WasScan>".format(
                    name, url
                )
                for name, url in (
                    (previous + " Slice 1", "accepted"),
                    (previous + "0 Slice 1", "excluded"),
                )
            )
        )
        self.assertEqual(
            get_previous_nws(
                client, "TAG", "Customer", previous, "2026-09-02T00:00:00Z"
            ),
            ["accepted"],
        )

    @patch(
        "was_reports.tracker.item_builder.stakeholder_flags", return_value=("", False)
    )
    @patch("was_reports.tracker.item_builder.get_previous_nws")
    def test_exempt_tags_retain_inaccessible_data(
        self, mock_previous, mock_flags
    ) -> None:
        """Deletion exemptions retain inaccessible URLs without removal candidates."""
        scan = etree.fromstring(
            b"<WasScan><status>FINISHED</status><summary><resultsStatus>NO_WEB_SERVICE</resultsStatus>"
            b"</summary><target><webApp><url>https://example.gov</url></webApp></target></WasScan>"
        )
        fields = create_multiscan(
            Mock(),
            "TAG",
            "Customer",
            "Customer Run #2",
            [scan],
            "2026-09-02T00:00:00Z",
            {"TAG"},
        )
        self.assertTrue(fields[2])
        self.assertIn("https://example.gov", fields[3])
        self.assertEqual(fields[4], "")
        mock_previous.assert_not_called()

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
