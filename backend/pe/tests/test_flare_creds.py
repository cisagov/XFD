"""Unit tests for flare_creds_script.py."""

# Standard Python Libraries
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from venv import logger

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR / "src") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "src"))

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")
os.environ.setdefault("FLARE_TENANT_ID", "12345")
os.environ.setdefault("FLARE_API_KEY", "test-flare-key")

# Third-Party Libraries
import pandas as pd

from pe_source.flare_creds.flare_creds_script import (
    extract_stealer_log_creds,
    format_creds_for_db,
    get_ident_creds,
    get_ident_creds_chunk,
)


class FlareCredsChunkTests(unittest.TestCase):
    """Verify helper behavior for Flare credential feed retrieval."""

    @patch("pe_source.flare_creds.flare_creds_script.time.sleep")
    @patch("pe_source.flare_creds.flare_creds_script.requests.get")
    def test_get_ident_creds_chunk_retries_on_error(self, mock_get, mock_sleep):
        """A non-200 response should trigger retries and return parsed JSON."""
        first_response = MagicMock(status_code=500)
        second_response = MagicMock(status_code=200)
        second_response.json.return_value = {"items": [{"id": 1}], "next": None}
        mock_get.side_effect = [first_response, second_response]

        result = get_ident_creds_chunk("token-123", 42, {"size": 10, "from": 5})

        self.assertEqual(result["items"], [{"id": 1}])
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(10)

    @patch("pe_source.flare_creds.flare_creds_script.get_data_source_uid")
    @patch("pe_source.flare_creds.flare_creds_script.get_flare_token")
    @patch("pe_source.flare_creds.flare_creds_script.get_ident_creds_chunk")
    @patch("pe_source.flare_creds.flare_creds_script.time.sleep")
    def test_get_ident_creds_filters_and_formats_results(
        self, mock_sleep, mock_chunk, mock_token, mock_source_uid
    ):
        """The function should transform fetched items and filter them by date."""
        mock_token.return_value = "flare-token"
        mock_source_uid.return_value = "flare-source-uid"
        mock_chunk.side_effect = [
            {
                "items": [
                    {
                        "imported_at": "2024-01-15T12:00:00",
                        "identity_name": "user@example.com",
                        "hash": "secret",
                        "domain": "example.com",
                        "source": {"id": "breach-1", "description_en": "desc", "breached_at": "2024-01-10"},
                    }
                ],
                "next": "cursor-2",
            },
            {
                "items": [
                    {
                        "imported_at": "2024-02-01T12:00:00",
                        "identity_name": "old@example.com",
                        "hash": "stale",
                        "domain": "example.com",
                        "source": {"id": "breach-2", "description_en": "older", "breached_at": "2024-01-20"},
                    }
                ],
                "next": None,
            },
        ]

        result = get_ident_creds(99, "2024-01-01", "2024-01-31")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["email"], "user@example.com")
        self.assertEqual(result[0]["password"], "secret")
        self.assertEqual(result[0]["breach_name"], "breach-1")
        self.assertEqual(result[0]["data_source_uid"], "flare-source-uid")
        self.assertEqual(result[0]["related_identifier"], 99)
        self.assertEqual(mock_chunk.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)


class FlareStealerLogTests(unittest.TestCase):
    """Verify parsing helpers for stealer-log credentials."""

    @patch("pe_source.flare_creds.flare_creds_script.get_data_source_uid")
    def test_extract_stealer_log_creds_returns_matching_rows(self, mock_source_uid):
        """Only credentials tied to the org domains should be returned."""
        mock_source_uid.return_value = "flare-source-uid"
        event = {"identifiers": [{"id": "1", "name": "example.com"}]}
        event_details = {
            "activity": {
                "header": {"timestamp": "2024-01-02T03:04:05"},
                "data": {
                    "credentials": [
                        {
                            "username": "user@example.com",
                            "password": "secret",
                            "url": "https://login.example.com",
                        },
                        {
                            "username": "other@example.org",
                            "password": "ignored",
                            "url": "https://other.example.org",
                        },
                    ],
                    "user_information": {
                        "ip_address": "1.2.3.4",
                        "os": "Windows",
                        "username": "victim",
                    },
                },
            }
        }

        result = extract_stealer_log_creds(event, event_details, ["example.com"])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["email"], "user@example.com")
        self.assertEqual(result[0]["password"], "secret")
        self.assertEqual(result[0]["root_domain"], "example.com")
        self.assertEqual(result[0]["data_source_uid"], "flare-source-uid")
        self.assertIn("contained passwords", result[0]["breach_description"])


class FlareCredsFormattingTests(unittest.TestCase):
    """Verify formatting of raw Flare credential rows for database insertion."""

    def test_format_creds_for_db_filters_and_enriches_rows(self):
        """Rows should be deduplicated and prepared for DB payloads."""
        all_creds_df = pd.DataFrame(
            [
                {
                    "email": "user@example.com",
                    "breach_name": "Breach A",
                    "password": "secret",
                    "breach_description": "desc",
                    "modified_date": "2024-01-15",
                    "root_domain": "example.com",
                    "sub_domain": "example.com",
                    "data_source_uid": "flare-source-uid",
                },
                {
                    "email": "user@example.com",
                    "breach_name": "Breach A",
                    "password": "secret",
                    "breach_description": "desc",
                    "modified_date": "2024-01-15",
                    "root_domain": "example.com",
                    "sub_domain": "example.com",
                    "data_source_uid": "flare-source-uid",
                },
                {
                    "email": "bad-email",
                    "breach_name": "Breach B",
                    "password": "",
                    "breach_description": "desc",
                    "modified_date": "2024-01-15",
                    "root_domain": "example.com",
                    "sub_domain": "example.com",
                    "data_source_uid": "flare-source-uid",

                },
                {
                    "email": "second@example.com",
                    "breach_name": "",
                    "password": None,
                    "breach_description": "",
                    "modified_date": "2024-01-15",
                    "root_domain": "example.com",
                    "sub_domain": "example.com",
                    "data_source_uid": "flare-source-uid",

                },
            ]
        )

        creds_df, breaches_df = format_creds_for_db(all_creds_df, "org-uid")
      
        self.assertEqual(creds_df["email"].tolist(), ["user@example.com"])
        self.assertEqual(creds_df["sub_domain"].tolist(), ["example.com"])
        self.assertEqual(breaches_df["breach_name"].tolist(), ["Breach A"])
        self.assertEqual(breaches_df["exposed_cred_count"].tolist(), [1])
        self.assertEqual(breaches_df["password_included"].tolist(), [True])


if __name__ == "__main__":
    unittest.main()
