"""Unit tests for IP status refresh script behavior."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import call, patch

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")
os.environ.setdefault("DATABASE_NAME", "test_cyhy")
os.environ.setdefault("DATABASE_USER", "test_user")
os.environ.setdefault("DATABASE_PASSWORD", "_".join(("test", "value")))

# Third-Party Libraries
import pandas as pd

from pe_source.ip_status_refresh.ip_status_refresh import run_ip_status_refresh


class IPStatusRefreshTests(unittest.TestCase):
    """Verify IP status refresh organization filtering and status updates."""

    def setUp(self):
        """Build reusable organization fixtures with mixed flags."""
        self.mock_all_orgs = [
            {
                "cyhy_db_name": "org_report_1",
                "report_on": True,
                "demo": False,
            },
            {
                "cyhy_db_name": "org_demo_1",
                "report_on": False,
                "demo": True,
            },
            {
                "cyhy_db_name": "org_disabled",
                "report_on": False,
                "demo": False,
            },
            {
                "cyhy_db_name": "org_report_2",
                "report_on": True,
                "demo": False,
            },
            {
                "cyhy_db_name": "org_demo_2",
                "report_on": False,
                "demo": True,
            },
        ]

    @patch("pe_source.ip_status_refresh.ip_status_refresh.update_ip_statuses")
    @patch(
        "pe_source.ip_status_refresh.ip_status_refresh."
        "get_current_ips_cidrs_by_org"
    )
    @patch("pe_source.ip_status_refresh.ip_status_refresh.get_orgs")
    def test_run_ip_status_refresh_all_filters_report_on_orgs(
        self,
        mock_get_orgs,
        mock_get_current_ips_cidrs_by_org,
        mock_update_ip_statuses,
    ):
        """All should process only organizations whose report_on flag is true."""
        mock_get_orgs.return_value = self.mock_all_orgs
        mock_get_current_ips_cidrs_by_org.return_value = pd.DataFrame()

        run_ip_status_refresh("all")

        mock_get_orgs.assert_called_once()
        mock_get_current_ips_cidrs_by_org.assert_has_calls(
            [
                call("org_report_1"),
                call("org_report_2"),
            ]
        )
        self.assertEqual(mock_get_current_ips_cidrs_by_org.call_count, 2)
        mock_update_ip_statuses.assert_not_called()

    @patch("pe_source.ip_status_refresh.ip_status_refresh.update_ip_statuses")
    @patch(
        "pe_source.ip_status_refresh.ip_status_refresh."
        "get_current_ips_cidrs_by_org"
    )
    @patch("pe_source.ip_status_refresh.ip_status_refresh.get_orgs")
    def test_run_ip_status_refresh_demo_filters_demo_orgs(
        self,
        mock_get_orgs,
        mock_get_current_ips_cidrs_by_org,
        mock_update_ip_statuses,
    ):
        """DEMO should process only organizations whose demo flag is true."""
        mock_get_orgs.return_value = self.mock_all_orgs
        mock_get_current_ips_cidrs_by_org.return_value = pd.DataFrame()

        run_ip_status_refresh("DEMO")

        mock_get_orgs.assert_called_once()
        mock_get_current_ips_cidrs_by_org.assert_has_calls(
            [
                call("org_demo_1"),
                call("org_demo_2"),
            ]
        )
        self.assertEqual(mock_get_current_ips_cidrs_by_org.call_count, 2)
        mock_update_ip_statuses.assert_not_called()

    @patch("pe_source.ip_status_refresh.ip_status_refresh.update_ip_statuses")
    @patch(
        "pe_source.ip_status_refresh.ip_status_refresh."
        "get_current_ips_cidrs_by_org"
    )
    @patch("pe_source.ip_status_refresh.ip_status_refresh._requested_org_names")
    @patch("pe_source.ip_status_refresh.ip_status_refresh.get_orgs")
    def test_run_ip_status_refresh_requested_orgs_uses_requested_names(
        self,
        mock_get_orgs,
        mock_requested_org_names,
        mock_get_current_ips_cidrs_by_org,
        mock_update_ip_statuses,
    ):
        """Specified organizations should be filtered using requested names."""
        mock_get_orgs.return_value = self.mock_all_orgs
        mock_requested_org_names.return_value = ["org_demo_1", "org_report_2"]
        mock_get_current_ips_cidrs_by_org.return_value = pd.DataFrame()

        run_ip_status_refresh("org_demo_1,org_report_2")

        mock_requested_org_names.assert_called_once_with("org_demo_1,org_report_2")
        mock_get_current_ips_cidrs_by_org.assert_has_calls(
            [
                call("org_demo_1"),
                call("org_report_2"),
            ]
        )
        self.assertEqual(mock_get_current_ips_cidrs_by_org.call_count, 2)
        mock_update_ip_statuses.assert_not_called()

    @patch("pe_source.ip_status_refresh.ip_status_refresh.update_ip_statuses")
    @patch(
        "pe_source.ip_status_refresh.ip_status_refresh."
        "get_current_ips_cidrs_by_org"
    )
    @patch("pe_source.ip_status_refresh.ip_status_refresh.get_orgs")
    def test_run_ip_status_refresh_updates_ips_outside_network(
        self,
        mock_get_orgs,
        mock_get_current_ips_cidrs_by_org,
        mock_update_ip_statuses,
    ):
        """IPs not contained by their associated network should be updated."""
        mock_get_orgs.return_value = [
            {
                "cyhy_db_name": "org_report_1",
                "report_on": True,
                "demo": False,
            }
        ]
        mock_get_current_ips_cidrs_by_org.return_value = pd.DataFrame(
            [
                {
                    "ip": "10.0.0.10",
                    "network": "10.0.0.0/24",
                    "ip_hash": "inside-network-hash",
                },
                {
                    "ip": "192.0.2.10",
                    "network": "10.0.0.0/24",
                    "ip_hash": "outside-network-hash-1",
                },
                {
                    "ip": "2001:db8::1",
                    "network": "2001:db8:1::/48",
                    "ip_hash": "outside-network-hash-2",
                },
            ]
        )

        run_ip_status_refresh("all")

        mock_get_current_ips_cidrs_by_org.assert_called_once_with("org_report_1")
        mock_update_ip_statuses.assert_has_calls(
            [
                call("outside-network-hash-1"),
                call("outside-network-hash-2"),
            ]
        )
        self.assertEqual(mock_update_ip_statuses.call_count, 2)

    @patch("pe_source.ip_status_refresh.ip_status_refresh.update_ip_statuses")
    @patch(
        "pe_source.ip_status_refresh.ip_status_refresh."
        "get_current_ips_cidrs_by_org"
    )
    @patch("pe_source.ip_status_refresh.ip_status_refresh.get_orgs")
    def test_run_ip_status_refresh_does_not_update_ips_inside_network(
        self,
        mock_get_orgs,
        mock_get_current_ips_cidrs_by_org,
        mock_update_ip_statuses,
    ):
        """IPs contained by their associated network should not be updated."""
        mock_get_orgs.return_value = [
            {
                "cyhy_db_name": "org_report_1",
                "report_on": True,
                "demo": False,
            }
        ]
        mock_get_current_ips_cidrs_by_org.return_value = pd.DataFrame(
            [
                {
                    "ip": "10.0.0.10",
                    "network": "10.0.0.0/24",
                    "ip_hash": "ipv4-inside-network-hash",
                },
                {
                    "ip": "2001:db8::10",
                    "network": "2001:db8::/64",
                    "ip_hash": "ipv6-inside-network-hash",
                },
            ]
        )

        run_ip_status_refresh("all")

        mock_get_current_ips_cidrs_by_org.assert_called_once_with("org_report_1")
        mock_update_ip_statuses.assert_not_called()

    @patch("pe_source.ip_status_refresh.ip_status_refresh.update_ip_statuses")
    @patch(
        "pe_source.ip_status_refresh.ip_status_refresh."
        "get_current_ips_cidrs_by_org"
    )
    @patch("pe_source.ip_status_refresh.ip_status_refresh._requested_org_names")
    @patch("pe_source.ip_status_refresh.ip_status_refresh.get_orgs")
    def test_run_ip_status_refresh_handles_no_matching_orgs(
        self,
        mock_get_orgs,
        mock_requested_org_names,
        mock_get_current_ips_cidrs_by_org,
        mock_update_ip_statuses,
    ):
        """No matching requested organizations should not query or update IPs."""
        mock_get_orgs.return_value = self.mock_all_orgs
        mock_requested_org_names.return_value = ["org_does_not_exist"]

        run_ip_status_refresh("org_does_not_exist")

        mock_requested_org_names.assert_called_once_with("org_does_not_exist")
        mock_get_current_ips_cidrs_by_org.assert_not_called()
        mock_update_ip_statuses.assert_not_called()


if __name__ == "__main__":
    unittest.main()