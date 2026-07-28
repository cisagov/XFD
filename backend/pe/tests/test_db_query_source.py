"""Unit tests for PE data collection database/API query helpers."""

# Standard Python Libraries
from datetime import datetime
from decimal import Decimal
import json
import os
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
import pandas as pd
from requests.exceptions import ConnectionError

# Configure values required when db_query_source is imported. The production
# module resolves its connection dictionary at import time.
os.environ.setdefault("PE_DB_NAME", "test_pe")
os.environ.setdefault("PE_DB_USERNAME", "test_user")
os.environ.setdefault("PE_DB_PASSWORD", "test_password")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("PE_DB_PORT", "5432")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
# First-Party Libraries
from pe_source.data import db_query_source


class ConnectTests(unittest.TestCase):
    """Verify direct PostgreSQL connection handling."""

    @patch("pe_source.data.db_query_source.psycopg2.connect")
    def test_connect_uses_configured_parameters(self, connect_mock):
        """Pass the configured connection dictionary to psycopg2."""
        connection = MagicMock()
        connect_mock.return_value = connection

        result = db_query_source.connect()

        self.assertIs(result, connection)
        connect_mock.assert_called_once_with(**db_query_source.CONN_PARAMS_DIC)

    @patch("pe_source.data.db_query_source.show_psycopg2_exception")
    @patch("pe_source.data.db_query_source.psycopg2.connect")
    def test_connect_returns_none_on_operational_error(self, connect_mock, error_mock):
        """Log PostgreSQL operational errors and return None."""
        error = db_query_source.OperationalError("database unavailable")
        connect_mock.side_effect = error

        self.assertIsNone(db_query_source.connect())
        error_mock.assert_called_once_with(error)


class ReadQueryTests(unittest.TestCase):
    """Verify API-backed database read helpers."""

    @patch("pe_source.data.db_query_source.requests.get")
    def test_get_orgs_converts_database_types(self, get_mock):
        """Convert API strings into the types expected by scan scripts."""
        get_mock.return_value.json.return_value = [
            {
                "cyhy_db_name": "DHS",
                "date_first_reported": "2026-01-02",
                "cyhy_period_start": "2026-01-01",
                "county_fips": "001",
                "state_fips": "12",
            }
        ]

        result = db_query_source.get_orgs()

        self.assertEqual(result[0]["date_first_reported"], datetime(2026, 1, 2))
        self.assertEqual(result[0]["cyhy_period_start"], datetime(2026, 1, 1))
        self.assertEqual(result[0]["county_fips"], Decimal("001"))
        self.assertEqual(result[0]["state_fips"], Decimal("12"))
        get_mock.assert_called_once_with(
            db_query_source.pe_api_url + "organizations_demo_or_report_on",
            headers={
                "Content-Type": "application/json",
                "access_token": db_query_source.pe_api_key,
            },
            timeout=60,
        )

    @patch("pe_source.data.db_query_source.requests.get")
    def test_get_orgs_returns_none_on_connection_error(self, get_mock):
        """Do not propagate API connection failures to scan callers."""
        get_mock.side_effect = ConnectionError("offline")

        self.assertIsNone(db_query_source.get_orgs())

    @patch("pe_source.data.db_query_source.requests.post")
    def test_get_data_source_uid_returns_first_uid(self, post_mock):
        """Return the UID from the first matching data-source row."""
        post_mock.return_value.json.return_value = [
            {"data_source_uid": "source-uid", "name": "dnstwist"}
        ]

        result = db_query_source.get_data_source_uid("dnstwist")

        self.assertEqual(result, "source-uid")
        payload = json.loads(post_mock.call_args.kwargs["data"])
        self.assertEqual(payload, {"name": "dnstwist"})

    @patch("pe_source.data.db_query_source.requests.post")
    def test_get_subdomain_uid_returns_minus_one_for_no_rows(self, post_mock):
        """Use -1 as the existing missing-subdomain sentinel."""
        post_mock.return_value.json.return_value = []

        self.assertEqual(db_query_source.get_subdomain_uid("missing.gov"), -1)

    @patch("pe_source.data.db_query_source.requests.post")
    def test_org_root_domains_renames_foreign_key_fields(self, post_mock):
        """Normalize API field names for the dnstwist scan loop."""
        post_mock.return_value.json.return_value = [
            {
                "root_domain_uid": "root-uid",
                "organizations_uid": "org-uid",
                "root_domain": "example.gov",
            }
        ]

        result = db_query_source.org_root_domains("org-uid")

        self.assertEqual(
            result,
            [
                {
                    "root_uid": "root-uid",
                    "org_uid": "org-uid",
                    "root_domain": "example.gov",
                }
            ],
        )

    @patch("pe_source.data.db_query_source.requests.post")
    def test_get_dnsmonitor_domain_mapping_selects_expected_columns(self, post_mock):
        """Return only domain and organization columns."""
        post_mock.return_value.json.return_value = [
            {"domain": "example.gov", "organization": "DHS", "date": "2026-01-01"}
        ]

        result = db_query_source.get_dnsmonitor_domain_mapping()

        pd.testing.assert_frame_equal(
            result,
            pd.DataFrame([{"domain": "example.gov", "organization": "DHS"}]),
        )

    @patch("pe_source.data.db_query_source.requests.post")
    def test_get_dnsmonitor_domain_mapping_returns_empty_frame_on_error(
        self, post_mock
    ):
        """Return a stable empty schema when the API cannot be reached."""
        post_mock.side_effect = ConnectionError("offline")

        result = db_query_source.get_dnsmonitor_domain_mapping()

        self.assertEqual(list(result.columns), ["domain", "organization"])
        self.assertTrue(result.empty)


class WriteQueryTests(unittest.TestCase):
    """Verify API-backed database write helpers."""

    @patch("pe_source.data.db_query_source.requests.put")
    def test_insert_subdomain_sends_expected_payload(self, put_mock):
        """Send domain, organization UID, and root flag to the insert endpoint."""
        put_mock.return_value.json.return_value = {"status": "ok"}

        db_query_source.insert_subdomain("www.example.gov", "org-uid", False)

        payload = json.loads(put_mock.call_args.kwargs["data"])
        self.assertEqual(
            payload,
            {"domain": "www.example.gov", "pe_org_uid": "org-uid", "root": False},
        )

    @patch("pe_source.data.db_query_source.requests.put")
    def test_insert_domain_permu_serializes_dates_without_mutating_other_fields(
        self, put_mock
    ):
        """Serialize permutation dates before sending rows to the API."""
        put_mock.return_value.json.return_value = {"status": "ok"}
        frame = pd.DataFrame(
            [
                {
                    "domain_permutation": "examp1e.gov",
                    "date_observed": pd.Timestamp("2026-02-03"),
                    "ipv4": "192.0.2.1",
                }
            ]
        )

        db_query_source.insert_domain_permu(frame)

        payload = json.loads(put_mock.call_args.kwargs["data"])
        self.assertEqual(payload["insert_data"][0]["date_observed"], "2026-02-03")
        self.assertEqual(payload["insert_data"][0]["ipv4"], "192.0.2.1")

    @patch("pe_source.data.db_query_source.requests.put")
    def test_insert_domain_alert_fills_null_previous_value_on_copy(self, put_mock):
        """Replace null previous values without mutating the caller's DataFrame."""
        put_mock.return_value.json.return_value = {"status": "ok"}
        frame = pd.DataFrame(
            [{"date": pd.Timestamp("2026-02-03"), "previous_value": None}]
        )

        db_query_source.insert_domain_alert(frame)

        payload = json.loads(put_mock.call_args.kwargs["data"])
        self.assertEqual(payload["insert_data"][0]["date"], "2026-02-03")
        self.assertEqual(payload["insert_data"][0]["previous_value"], "")
        self.assertTrue(pd.isna(frame.loc[0, "previous_value"]))


if __name__ == "__main__":
    unittest.main()
