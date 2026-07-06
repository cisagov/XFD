"""Unit tests for dnsmonitor data collection script."""

# Standard Python Libraries
import datetime
import os
import unittest

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from pe_source.data.config_source import get_dnsmonitor_token
from pe_source.dnsmonitor.dnsmonitor_helpers import (
    get_dns_records,
    get_domain_alerts,
    get_monitored_domains,
)


class DnsmonitorHelperTests(unittest.TestCase):
    """Verify dnsmonitor helper function behavior."""

    def test_get_dnsmonitor_token(self):
        """Test get_dnsmonitor_token function."""
        # Unable to test extensively without calling the real DNSMonitor API
        token = get_dnsmonitor_token()
        self.assertIsNone(token)

    def test_get_monitored_domains(self):
        """Test get_monitored_domains function."""
        # Unable to test extensively without calling the real DNSMonitor API
        token = "asdf"  # nosec
        result = get_monitored_domains(token)
        self.assertIsNone(result)

    def test_get_domain_alerts(self):
        """Test get_domain_alerts function."""
        # Unable to test extensively without calling the real DNSMonitor API
        now = datetime.datetime.now()
        days_back = datetime.timedelta(days=20)
        day = datetime.timedelta(days=1)
        start_date = now - days_back
        end_date = now + day
        token = "asdf"  # nosec
        org_domain_ids = ["44"]
        result = get_domain_alerts(token, org_domain_ids, start_date, end_date)
        self.assertIsNone(result)

    def test_get_dns_records(self):
        """Test the get_dns_records function."""
        # Unable to test real domain due to constantly changing MX/NS/A/AAAA records
        mx_1, ns_1, ipv4_1, ipv6_1 = get_dns_records("asdf")
        self.assertEqual(mx_1, "[]")
        self.assertEqual(ns_1, "[]")
        self.assertEqual(ipv4_1, "")
        self.assertEqual(ipv6_1, "")


if __name__ == "__main__":
    unittest.main()
