"""Unit tests for dnsmonitor data collection script."""

# Standard Python Libraries
import datetime
import os
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
import pandas as pd
from pandas.testing import assert_frame_equal

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from pe_source.data.config_source import get_dnsmonitor_token
from pe_source.dnsmonitor.dnsmonitor_helpers import (
    dnsmonitor_domains,
    get_dns_records,
    get_domain_alerts,
    get_monitored_domains,
)


class DnsmonitorHelperTests(unittest.TestCase):
    """Verify dnsmonitor helper function behavior."""

    @patch("pe_source.data.config_source.create_retry_session")
    @patch.dict(
        os.environ,
        {
            "DNSMONITOR_CLIENT_ID": "fake_dnsmonitor_client_id",
            "DNSMONITOR_CLIENT_SECRET": "fake_dnsmonitor_client_secret",
        },
    )
    def test_get_dnsmonitor_token(self, mock_create_session):
        """Test get_dnsmonitor_token function."""
        # Mock API response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_token = "mock_dnsmonitor_token"  # nosec
        mock_response.json.return_value = {
            "access_token": mock_token,
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "DNSMonitorAPI",
        }
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        token = get_dnsmonitor_token()
        # Assert
        self.assertEqual(token, mock_token)
        mock_session.post.assert_called_once_with(
            "https://argosecure.com/dhs/connect/token",
            headers={},
            data={
                "client_id": "fake_dnsmonitor_client_id",
                "client_secret": "fake_dnsmonitor_client_secret",
                "grant_type": "client_credentials",
                "scope": "DNSMonitorAPI",
            },
            files=[],
            timeout=60,
        )

    @patch("pe_source.dnsmonitor.dnsmonitor_helpers.create_retry_session")
    def test_get_monitored_domains(self, mock_create_session):
        """Test get_monitored_domains function."""
        # Mock API response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_token = "mock_dnsmonitor_token"  # nosec
        mock_return_data = [
            {"domainId": 1, "domainName": "test1.gov"},
            {"domainId": 2, "domainName": "test2.gov"},
            {"domainId": 3, "domainName": "test3.gov"},
        ]
        mock_response.json.return_value = mock_return_data
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        result = get_monitored_domains(mock_token)
        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        assert_df = pd.DataFrame(mock_return_data)
        assert_frame_equal(result, assert_df)
        mock_session.get.assert_called_once_with(
            "https://dns.argosecure.com/dhs/api/GetDomains",
            headers={"authorization": f"Bearer {mock_token}"},
            data={},
            timeout=60,
        )

    @patch("pe_source.dnsmonitor.dnsmonitor_helpers.get_dnsmonitor_domain_mapping")
    @patch("pe_source.dnsmonitor.dnsmonitor_helpers.get_monitored_domains")
    def test_dnsmonitor_domains(self, mock_get_domains, mock_get_mapping):
        """Test dnsmonitor_domains function."""
        # Mock function responses
        mock_domains_data = [
            {"domainId": 1, "domainName": "test1.gov"},
            {"domainId": 2, "domainName": "test1.gov"},
            {"domainId": 3, "domainName": "test2.gov"},
        ]
        mock_get_domains.return_value = pd.DataFrame(mock_domains_data)
        mock_mapping_data = [
            {"domain": "test1.gov", "organization": "Org B"},
            {"domain": "test2.gov", "organization": "Org A"},
            {"domain": "test3.gov", "organization": "Org C"},
        ]
        mock_get_mapping.return_value = pd.DataFrame(mock_mapping_data)
        mock_token = "mock_dnsmonitor_token"  # nosec
        # Call function
        result = dnsmonitor_domains(mock_token)
        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "org"], "Org A")
        self.assertEqual(result.loc[0, "domainName"], "test2.gov")
        self.assertEqual(result.loc[0, "domainId"], 3)
        self.assertEqual(result.loc[1, "org"], "Org B")
        self.assertEqual(result.loc[1, "domainName"], "test1.gov")
        self.assertEqual(result.loc[1, "domainId"], 1)
        self.assertEqual(result["domainId"].dtype, "int64")
        mock_get_domains.assert_called_once_with(mock_token)
        mock_get_mapping.assert_called_once()

    @patch("pe_source.dnsmonitor.dnsmonitor_helpers.create_retry_session")
    def test_get_domain_alerts(self, mock_create_session):
        """Test get_domain_alerts function."""
        # Mock API response
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_token = "mock_dnsmonitor_token"  # nosec
        mock_domain_ids = [1, 2]
        mock_start_date = datetime.datetime(2026, 1, 1)
        mock_end_date = datetime.datetime(2026, 1, 15)
        mock_return_data = [
            {
                "domainId": 1,
                "rootDomain": "test1.gov",
                "domainPermutation": "test12.gov",
                "alertType": "MX Change",
                "message": "MX Record altered",
                "previousValue": "://old.gov",
                "newValue": "://new.gov",
                "dateCreated": "2026-07-09",
            }
        ]
        mock_payload = '{\r\n  "domainIds": [1, 2],\r\n  "fromDate": "2026-01-01 00:00:00",\r\n  "toDate": "2026-01-15 00:00:00",\r\n  "alertType": null,\r\n  "showBufferPeriod": false\r\n}'
        mock_response.json.return_value = mock_return_data
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        result = get_domain_alerts(
            mock_token, mock_domain_ids, mock_start_date, mock_end_date
        )
        # Assert
        self.assertIsInstance(result, pd.DataFrame)
        assert_df = pd.DataFrame(mock_return_data)
        assert_frame_equal(result, assert_df)
        mock_session.get.assert_called_once_with(
            "https://dns.argosecure.com/dhs/api/GetAlerts",
            headers={
                "authorization": f"Bearer {mock_token}",
                "Content-Type": "application/json",
            },
            json=mock_payload,
            timeout=60,
        )

    @patch("pe_source.dnsmonitor.dnsmonitor_helpers.socket.gethostbyname")
    @patch("pe_source.dnsmonitor.dnsmonitor_helpers.dns.resolver.resolve")
    def test_get_dns_records(self, mock_resolve, mock_gethostbyname):
        """Test get_dns_records function."""
        # Mock function responses
        mock_ns_data1 = MagicMock()
        mock_ns_data1.target = "://test1.gov."
        mock_ns_data2 = MagicMock()
        mock_ns_data2.target = "://test1.gov."
        mock_mx_data = MagicMock()
        mock_mx_data.exchange = "://test1.gov."

        def side_effect(qname, rdtype):
            if rdtype == "NS":
                return [mock_ns_data1, mock_ns_data2]
            elif rdtype == "MX":
                return [mock_mx_data]
            raise ValueError(f"Unexpected record type: {rdtype}")

        mock_resolve.side_effect = side_effect
        mock_gethostbyname.return_value = "192.0.2.1"
        # Call function
        mx, ns, ipv4, ipv6 = get_dns_records("test1.gov")
        # Assert
        self.assertEqual(mx, "['://test1.gov.']")
        self.assertEqual(ns, "['://test1.gov.', '://test1.gov.']")
        self.assertEqual(ipv4, "192.0.2.1")
        self.assertEqual(ipv6, "")
        mock_resolve.assert_any_call("test1.gov", "NS")
        mock_resolve.assert_any_call("test1.gov", "MX")
        mock_gethostbyname.assert_called_once_with("test1.gov")


if __name__ == "__main__":
    unittest.main()
