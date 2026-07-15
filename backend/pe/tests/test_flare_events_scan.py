"""Unit tests for flare_events data collection."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")
os.environ.setdefault("FLARE_TENANT_ID", "12345")
os.environ.setdefault("FLARE_API_KEY", "test-flare-key")

# Third-Party Libraries
from pe_source.flare.flare_config import parse_flare_api_keys
from pe_source.flare.flare_events_script import (
    _requested_org_names,
    parse_default_event_fields,
    parse_related_identifiers,
    parse_stealer_log_event_fields,
)
from pe_source.flare.flare_helpers import remove_emoji, validate_flare_api_key


class FlareOrgFilterTests(unittest.TestCase):
    """Verify explicit org filtering uses exact cyhy_db_name matches."""

    def test_single_org(self):
        """A single org name should resolve to one entry."""
        requested = _requested_org_names("DHS_CISA")
        self.assertEqual(requested, {"DHS_CISA"})

    def test_comma_separated_orgs(self):
        """Comma-separated org lists should split into distinct names."""
        requested = _requested_org_names("DHS,DHS_CISA")
        self.assertEqual(requested, {"DHS", "DHS_CISA"})


class FlareConfigTests(unittest.TestCase):
    """Verify Flare API key parsing helpers."""

    def test_parse_flare_api_keys_splits_and_strips(self):
        """Comma-separated keys should be split and trimmed."""
        self.assertEqual(
            parse_flare_api_keys(" key1 , key2,, key3 "),
            ["key1", "key2", "key3"],
        )

    @patch("pe_source.flare.flare_helpers.get_flare_token", return_value="token")
    def test_validate_flare_api_key_true_when_token_returned(self, _token_mock):
        """validate_flare_api_key should return True when a token is returned."""
        self.assertTrue(validate_flare_api_key("good-key", tenant_id="123"))

    @patch("pe_source.flare.flare_helpers.get_flare_token", return_value=None)
    def test_validate_flare_api_key_false_when_token_missing(self, _token_mock):
        """validate_flare_api_key should return False when token generation fails."""
        self.assertFalse(validate_flare_api_key("bad-key", tenant_id="123"))


class FlareHelperTests(unittest.TestCase):
    """Verify flare helper utilities."""

    def test_remove_emoji_strips_emoticons(self):
        """Emoji characters should be removed from content strings."""
        self.assertEqual(remove_emoji("hello 😀 world"), "hello  world")

    def test_parse_related_identifiers_ids(self):
        """Related identifier IDs should be returned as a list."""
        event = {
            "identifiers": [
                {"id": "ident-1", "name": "example.gov"},
                {"id": "ident-2", "name": "other.gov"},
            ]
        }
        self.assertEqual(
            parse_related_identifiers(event),
            ["ident-1", "ident-2"],
        )

    def test_parse_related_identifiers_text(self):
        """Related identifier names should be returned when text=True."""
        event = {
            "identifiers": [
                {"id": "ident-1", "name": "example.gov"},
            ]
        }
        self.assertEqual(
            parse_related_identifiers(event, True),
            ["example.gov"],
        )


class FlareParseEventTests(unittest.TestCase):
    """Verify event parsing helpers produce PE-ready rows."""

    def test_parse_default_event_fields_chat_message(self):
        """chat_message events should use message content and conversation link."""
        event = {
            "event_uid": "evt-1",
            "event_type": "chat_message",
            "event_date": "2026-07-01",
            "severity": "medium",
            "identifiers": [{"id": "1", "name": "example.gov"}],
        }
        event_details = {
            "activity": {
                "header": {
                    "title": "ignored",
                    "content_hash": "hash",
                    "actor": "actor",
                    "category_name": "cat",
                    "risk": {"score": 1},
                },
                "metadata": {"source": "forum"},
                "data": {
                    "url": "http://example.com",
                    "message": "hello there",
                    "conversation_link": "http://example.com/thread",
                },
            }
        }
        row = parse_default_event_fields(event, event_details, "org-uid", "source-uid")
        self.assertEqual(row["content"], "hello there")
        self.assertEqual(row["url"], "http://example.com/thread")
        self.assertEqual(row["data_source_uid"], "source-uid")

    def test_parse_stealer_log_event_fields_skips_irrelevant_creds(self):
        """stealer_log events without relevant credentials should return -1."""
        event = {
            "event_uid": "evt-2",
            "event_type": "stealer_log",
            "event_date": "2026-07-01",
            "severity": "high",
            "identifiers": [{"id": "1", "name": "example.gov"}],
        }
        event_details = {
            "activity": {
                "header": {
                    "content_preview": "3 credentials",
                    "content_hash": "hash",
                    "actor": "actor",
                    "category_name": "cat",
                    "risk": None,
                },
                "metadata": {"source": "market"},
                "data": {
                    "url": "http://example.com",
                    "credentials": [
                        {
                            "username": "user",
                            "password": "pass",
                            "url": "http://other.com",
                        }
                    ],
                    "user_information": {
                        "ip_address": "1.2.3.4",
                        "os": "Windows",
                        "username": "user",
                    },
                },
            }
        }
        # Third-Party Libraries
        import pandas as pd

        org_idents_df = pd.DataFrame(
            [{"id": "1", "value": "example.gov", "type": "domain"}]
        )
        result = parse_stealer_log_event_fields(
            event, event_details, "org-uid", org_idents_df, "source-uid"
        )
        self.assertEqual(result, -1)


class FlareEventsScriptTests(unittest.TestCase):
    """Verify run_flare_events orchestration with mocked dependencies."""

    @patch("pe_source.flare.flare_events_script.insert_flare_events")
    @patch("pe_source.flare.flare_events_script.get_all_event_details")
    @patch("pe_source.flare.flare_events_script.get_ident_group_events")
    @patch("pe_source.flare.flare_events_script.get_all_ident_by_group_id")
    @patch("pe_source.flare.flare_events_script.get_ident_group_info")
    @patch("pe_source.flare.flare_events_script.get_data_source_uid")
    @patch("pe_source.flare.flare_events_script.get_orgs")
    def test_run_flare_events_inserts_parsed_rows(
        self,
        mock_get_orgs,
        mock_get_source_uid,
        mock_get_ident_group_info,
        mock_get_all_ident,
        mock_get_ident_group_events,
        mock_get_all_event_details,
        mock_insert_flare_events,
    ):
        """run_flare_events should insert deduplicated event rows for one org."""
        # Third-Party Libraries
        from pe_source.flare.flare_events_script import run_flare_events

        mock_get_orgs.return_value = [
            {
                "organizations_uid": "org-uid-1",
                "cyhy_db_name": "DHS",
                "report_on": True,
            }
        ]
        mock_get_source_uid.return_value = "flare-source-uid"
        mock_get_ident_group_info.return_value = {"name": "DHS", "id": 99}
        mock_get_all_ident.return_value = [
            {"id": "1", "value": "dhs.gov", "type": "domain"}
        ]
        mock_get_ident_group_events.return_value = [
            {
                "event_uid": "evt-1",
                "event_type": "chat_message",
                "severity": "low",
                "identifiers": [{"id": "1", "name": "dhs.gov"}],
                "event_date": "2026-07-01",
            }
        ]
        mock_get_all_event_details.return_value = [
            {
                "organizations_uid": "org-uid-1",
                "flare_uid": "evt-1",
                "event_type": "chat_message",
                "event_date": "2026-07-01",
                "collection_date": "2026-07-13",
                "title": "title",
                "content": "content",
                "content_hash": "hash",
                "actor": "actor",
                "category": "cat",
                "source": "forum",
                "url": "http://example.com",
                "risk_scores": "{'score': 1}",
                "related_identifiers": ["1"],
                "related_identifiers_txt": ["dhs.gov"],
                "data_source_uid": "flare-source-uid",
                "severity": "low",
            }
        ]

        run_flare_events("DHS")

        mock_insert_flare_events.assert_called_once()
        inserted = mock_insert_flare_events.call_args.args[0]
        self.assertEqual(len(inserted), 1)
        self.assertEqual(inserted[0]["flare_uid"], "evt-1")


if __name__ == "__main__":
    unittest.main()
