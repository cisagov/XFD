"""Unit tests for Shodan helper functions."""

# Standard Python Libraries
import datetime
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from pe_source.shodan import shodan_helpers
import shodan


class ShodanHelpersUtilityTests(unittest.TestCase):
    """Verify deterministic utility helper behavior."""

    def test_get_shodan_dicts_contains_expected_keys(self):
        """Dictionaries should expose expected protocol and CVSS mapping keys."""
        (
            risky_ports,
            name_dict,
            risk_dict,
            av_dict,
            ac_dict,
            ci_dict,
        ) = shodan_helpers.get_shodan_dicts()

        self.assertIn("http", risky_ports)
        self.assertEqual(name_dict["ftp"], "File Transfer Protocol")
        self.assertEqual(risk_dict["smtp"], "SMTP")
        self.assertIn("NETWORK", av_dict)
        self.assertIn("LOW", ac_dict)
        self.assertIn("COMPLETE", ci_dict)

    def test_time_to_utc_with_naive_datetime(self):
        """Naive datetimes should be interpreted as local time and converted to UTC."""
        naive_time = datetime.datetime(2026, 1, 10, 12, 0, 0)

        utc_time = shodan_helpers.time_to_utc(naive_time)

        self.assertIsNotNone(utc_time.tzinfo)
        self.assertEqual(utc_time.tzinfo, datetime.timezone.utc)

    def test_time_to_utc_with_aware_datetime(self):
        """Timezone-aware datetimes should convert correctly to UTC."""
        eastern = datetime.timezone(datetime.timedelta(hours=-5))
        aware_time = datetime.datetime(2026, 1, 10, 12, 0, 0, tzinfo=eastern)

        utc_time = shodan_helpers.time_to_utc(aware_time)

        self.assertEqual(
            utc_time,
            datetime.datetime(2026, 1, 10, 17, 0, tzinfo=datetime.timezone.utc),
        )

    def test_get_dates_returns_utc_window(self):
        """Date window should be UTC-aware and span 31 days."""
        start, end = shodan_helpers.get_dates()

        self.assertEqual(start.tzinfo, datetime.timezone.utc)
        self.assertEqual(end.tzinfo, datetime.timezone.utc)
        self.assertEqual(end - start, datetime.timedelta(days=31))

    @patch("pe_source.shodan.shodan_helpers.requests.get")
    def test_search_circl_calls_expected_endpoint(self, mock_get):
        """CVE lookup should call Circl with expected URL and timeout."""
        mock_response = MagicMock()
        mock_get.return_value = mock_response

        result = shodan_helpers.search_circl("CVE-2026-12345")

        self.assertIs(result, mock_response)
        mock_get.assert_called_once_with(
            "https://cve.circl.lu/api/cve/CVE-2026-12345", timeout=60
        )


class ShodanThreadTests(unittest.TestCase):
    """Verify run_shodan_thread control flow."""

    @patch("pe_source.shodan.shodan_helpers.search_shodan")
    @patch("pe_source.shodan.shodan_helpers.get_ips")
    @patch("pe_source.shodan.shodan_helpers.get_dates")
    def test_run_shodan_thread_calls_search_per_org_with_ips(
        self, mock_get_dates, mock_get_ips, mock_search_shodan
    ):
        """Each org with IPs should call search_shodan once."""
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc)
        mock_get_dates.return_value = (start, end)
        mock_get_ips.side_effect = [["1.1.1.1"], ["2.2.2.2"]]
        mock_search_shodan.side_effect = [[], ["org_b chunk 1 failed"]]

        orgs = [
            {"cyhy_db_name": "org_a", "organizations_uid": "uid-a"},
            {"cyhy_db_name": "org_b", "organizations_uid": "uid-b"},
        ]
        api = object()

        shodan_helpers.run_shodan_thread(api, orgs, "Thread 1:")

        self.assertEqual(mock_search_shodan.call_count, 2)
        first_call_args = mock_search_shodan.call_args_list[0].args
        second_call_args = mock_search_shodan.call_args_list[1].args
        self.assertEqual(first_call_args[0], "Thread 1:")
        self.assertEqual(second_call_args[6], "org_b")

    @patch("pe_source.shodan.shodan_helpers.search_shodan")
    @patch("pe_source.shodan.shodan_helpers.get_ips")
    @patch("pe_source.shodan.shodan_helpers.get_dates")
    def test_run_shodan_thread_skips_org_when_no_ips(
        self, mock_get_dates, mock_get_ips, mock_search_shodan
    ):
        """No-IP orgs should be skipped without calling search_shodan."""
        mock_get_dates.return_value = (
            datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc),
        )
        mock_get_ips.return_value = []

        shodan_helpers.run_shodan_thread(
            object(),
            [{"cyhy_db_name": "org_a", "organizations_uid": "uid-a"}],
            "Thread 1:",
        )

        mock_search_shodan.assert_not_called()

    @patch("pe_source.shodan.shodan_helpers.search_shodan")
    @patch("pe_source.shodan.shodan_helpers.get_ips")
    @patch("pe_source.shodan.shodan_helpers.get_dates")
    def test_run_shodan_thread_continues_after_get_ips_exception(
        self, mock_get_dates, mock_get_ips, mock_search_shodan
    ):
        """A get_ips error for one org should not prevent processing later orgs."""
        mock_get_dates.return_value = (
            datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc),
        )

        def ips_side_effect(org_uid):
            if org_uid == "uid-a":
                raise RuntimeError("db down")
            return ["2.2.2.2"]

        mock_get_ips.side_effect = ips_side_effect
        mock_search_shodan.return_value = []

        shodan_helpers.run_shodan_thread(
            object(),
            [
                {"cyhy_db_name": "org_a", "organizations_uid": "uid-a"},
                {"cyhy_db_name": "org_b", "organizations_uid": "uid-b"},
            ],
            "Thread 1:",
        )

        mock_search_shodan.assert_called_once()
        self.assertEqual(mock_search_shodan.call_args.args[6], "org_b")


class ShodanVerificationTests(unittest.TestCase):
    """Verify is_verified CVE processing behavior."""

    def setUp(self):
        """Build reusable dictionaries and minimal row context."""
        (
            _,
            _,
            _,
            self.av_dict,
            self.ac_dict,
            self.ci_dict,
        ) = shodan_helpers.get_shodan_dicts()
        self.result_row = {
            "domains": ["example.gov"],
            "hostnames": ["host.example.gov"],
            "ip_str": "192.0.2.10",
            "isp": "Example ISP",
            "org": "Example Org",
            "tags": ["tag1"],
        }
        self.data_row = {
            "port": 443,
            "_shodan": {"module": "https"},
            "timestamp": "2026-01-10T10:00:00.000000",
        }

    @patch("pe_source.shodan.shodan_helpers.search_circl")
    def test_is_verified_adds_verified_vuln_row(self, mock_search_circl):
        """Verified CVEs should append a structured vulnerability row."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "summary": "Test summary",
            "vulnerable_product": ["vendor:product:1.0"],
            "access": {"vector": "NETWORK", "complexity": "LOW"},
            "impact": {
                "confidentiality": "PARTIAL",
                "integrity": "PARTIAL",
                "availability": "PARTIAL",
            },
            "cvss": 7.5,
        }
        mock_search_circl.return_value = mock_response

        vulns = {"CVE-2026-0001": {"verified": True}}
        unverified, vuln_data = shodan_helpers.is_verified(
            vulns,
            "CVE-2026-0001",
            self.av_dict,
            self.ac_dict,
            self.ci_dict,
            [],
            "org-uid",
            self.result_row,
            self.data_row,
            "AS64500",
            [],
        )

        self.assertEqual(unverified, [])
        self.assertEqual(len(vuln_data), 1)
        self.assertEqual(vuln_data[0]["cve"], "CVE-2026-0001")
        self.assertEqual(vuln_data[0]["severity"], "High")
        self.assertTrue(vuln_data[0]["is_verified"])

    @patch("pe_source.shodan.shodan_helpers.search_circl")
    def test_is_verified_severity_thresholds(self, mock_search_circl):
        """CVSS scores should map to expected severity buckets."""
        vulns = {"CVE-2026-0002": {"verified": True}}
        cases = [
            (10.0, "Critical"),
            (7.0, "High"),
            (4.0, "Medium"),
            (0.1, "Low"),
            (0.0, ""),
        ]

        for cvss, expected in cases:
            with self.subTest(cvss=cvss):
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "summary": "summary",
                    "vulnerable_product": [],
                    "access": {"vector": "NETWORK", "complexity": "LOW"},
                    "impact": {
                        "confidentiality": "NONE",
                        "integrity": "NONE",
                        "availability": "NONE",
                    },
                    "cvss": cvss,
                }
                mock_search_circl.return_value = mock_response
                _, vuln_data = shodan_helpers.is_verified(
                    vulns,
                    "CVE-2026-0002",
                    self.av_dict,
                    self.ac_dict,
                    self.ci_dict,
                    [],
                    "org-uid",
                    self.result_row,
                    self.data_row,
                    "AS64500",
                    [],
                )
                self.assertEqual(vuln_data[0]["severity"], expected)

    def test_is_verified_appends_unverified_cve(self):
        """Unverified CVEs should be tracked without appending vuln rows."""
        vulns = {"CVE-2026-9999": {"verified": False}}

        unverified, vuln_data = shodan_helpers.is_verified(
            vulns,
            "CVE-2026-9999",
            self.av_dict,
            self.ac_dict,
            self.ci_dict,
            [],
            "org-uid",
            self.result_row,
            self.data_row,
            "AS64500",
            [],
        )

        self.assertEqual(unverified, ["CVE-2026-9999"])
        self.assertEqual(vuln_data, [])


class SearchShodanTests(unittest.TestCase):
    """Verify search_shodan data assembly, retries, and edge handling."""

    def setUp(self):
        """Prepare a reusable time window and base API response row."""
        self.start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        self.end = datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc)
        self.base_result = {
            "domains": ["example.gov"],
            "hostnames": ["host.example.gov"],
            "ip_str": "198.51.100.15",
            "isp": "ISP",
            "org": "Org",
            "tags": ["gov"],
            "data": [],
        }

    @patch("pe_source.shodan.shodan_helpers.insert_shodan_vulns")
    @patch("pe_source.shodan.shodan_helpers.insert_shodan_assets")
    @patch("pe_source.shodan.shodan_helpers.time.sleep")
    @patch("pe_source.shodan.shodan_helpers.time_to_utc")
    @patch("pe_source.shodan.shodan_helpers.get_data_source_uid")
    def test_search_shodan_inserts_asset_rows(
        self,
        mock_get_source_uid,
        mock_time_to_utc,
        _mock_sleep,
        mock_insert_assets,
        mock_insert_vulns,
    ):
        """A valid in-window result should produce one asset insert row."""
        mock_get_source_uid.return_value = "source-uid"
        mock_time_to_utc.return_value = datetime.datetime(
            2026, 1, 10, tzinfo=datetime.timezone.utc
        )
        mock_insert_assets.side_effect = lambda chunk, failed: failed

        api = MagicMock()
        result = dict(self.base_result)
        result["data"] = [
            {
                "timestamp": "2026-01-10T10:00:00.000000",
                "product": "nginx",
                "http": {"server": "nginx"},
                "ASN": "AS64500",
                "vulns": None,
                "location": {"country_code": "US", "city": "DC"},
                "port": 443,
                "_shodan": {"module": "https"},
                "cpe": None,
                "data": "banner",
                "version": "1.0",
            }
        ]
        api.host.return_value = [result]

        failed = shodan_helpers.search_shodan(
            "Thread 1:",
            ["198.51.100.15"],
            api,
            self.start,
            self.end,
            "org-uid",
            "org_name",
            [],
        )

        self.assertEqual(failed, [])
        mock_insert_assets.assert_called_once()
        asset_chunk = mock_insert_assets.call_args.args[0]
        self.assertEqual(len(asset_chunk), 1)
        self.assertEqual(asset_chunk[0]["ip"], "198.51.100.15")
        mock_insert_vulns.assert_not_called()

    @patch("pe_source.shodan.shodan_helpers.insert_shodan_vulns")
    @patch("pe_source.shodan.shodan_helpers.insert_shodan_assets")
    @patch("pe_source.shodan.shodan_helpers.time.sleep")
    @patch("pe_source.shodan.shodan_helpers.time_to_utc")
    @patch("pe_source.shodan.shodan_helpers.get_data_source_uid")
    def test_search_shodan_skips_no_info_api_errors(
        self,
        mock_get_source_uid,
        mock_time_to_utc,
        _mock_sleep,
        mock_insert_assets,
        mock_insert_vulns,
    ):
        """The no-information APIError should skip chunk without failure append."""
        mock_get_source_uid.return_value = "source-uid"
        mock_time_to_utc.return_value = datetime.datetime(
            2026, 1, 10, tzinfo=datetime.timezone.utc
        )
        api = MagicMock()
        api.host.side_effect = shodan.APIError("No information available for that IP.")

        failed = shodan_helpers.search_shodan(
            "Thread 1:",
            ["198.51.100.15"],
            api,
            self.start,
            self.end,
            "org-uid",
            "org_name",
            [],
        )

        self.assertEqual(failed, [])
        mock_insert_assets.assert_not_called()
        mock_insert_vulns.assert_not_called()

    @patch("pe_source.shodan.shodan_helpers.insert_shodan_vulns")
    @patch("pe_source.shodan.shodan_helpers.insert_shodan_assets")
    @patch("pe_source.shodan.shodan_helpers.time.sleep")
    @patch("pe_source.shodan.shodan_helpers.get_data_source_uid")
    def test_search_shodan_retries_and_records_failure_after_api_errors(
        self, mock_get_source_uid, mock_sleep, mock_insert_assets, mock_insert_vulns
    ):
        """Repeated API errors should trigger retries and append failure text."""
        mock_get_source_uid.return_value = "source-uid"
        api = MagicMock()
        api.host.side_effect = [
            shodan.APIError("rate limit"),
            shodan.APIError("rate limit"),
            shodan.APIError("rate limit"),
            shodan.APIError("rate limit"),
            shodan.APIError("rate limit"),
        ]

        failed = shodan_helpers.search_shodan(
            "Thread 1:",
            ["198.51.100.15"],
            api,
            self.start,
            self.end,
            "org-uid",
            "org_name",
            [],
        )

        self.assertIn("org_name chunk 1 failed 5 times and skipped", failed)
        self.assertEqual(mock_sleep.call_count, 4)
        mock_sleep.assert_called_with(5)
        mock_insert_assets.assert_not_called()
        mock_insert_vulns.assert_not_called()

    @patch("pe_source.shodan.shodan_helpers.insert_shodan_vulns")
    @patch("pe_source.shodan.shodan_helpers.insert_shodan_assets")
    @patch("pe_source.shodan.shodan_helpers.time.sleep")
    @patch("pe_source.shodan.shodan_helpers.time_to_utc")
    @patch("pe_source.shodan.shodan_helpers.get_data_source_uid")
    @patch("pe_source.shodan.shodan_helpers.get_shodan_dicts")
    def test_search_shodan_special_org_filters_http_80_vuln_rows(
        self,
        mock_get_dicts,
        mock_get_source_uid,
        mock_time_to_utc,
        _mock_sleep,
        mock_insert_assets,
        mock_insert_vulns,
    ):
        """Special-org UID should drop port 80/http vulnerability rows."""
        risky_ports = ["http"]
        name_dict = {"http": "Hypertext Transfer Protocol"}
        risk_dict = {"http": "HTTP"}
        mock_get_dicts.return_value = (
            risky_ports,
            name_dict,
            risk_dict,
            {},
            {},
            {},
        )
        mock_get_source_uid.return_value = "source-uid"
        mock_time_to_utc.return_value = datetime.datetime(
            2026, 1, 10, tzinfo=datetime.timezone.utc
        )
        mock_insert_assets.side_effect = lambda chunk, failed: failed

        api = MagicMock()
        result = dict(self.base_result)
        result["data"] = [
            {
                "timestamp": "2026-01-10T10:00:00.000000",
                "product": "apache",
                "http": {"server": "apache"},
                "ASN": "AS64500",
                "vulns": None,
                "location": {"country_code": "US", "city": "DC"},
                "port": 80,
                "_shodan": {"module": "http"},
                "cpe": None,
                "data": "banner",
                "version": "2.0",
            }
        ]
        api.host.return_value = [result]

        shodan_helpers.search_shodan(
            "Thread 1:",
            ["198.51.100.15"],
            api,
            self.start,
            self.end,
            "7d2dbd06-f247-11ec-bb6e-02c6a3fe975b",
            "org_name",
            [],
        )

        mock_insert_assets.assert_called_once()
        mock_insert_vulns.assert_not_called()


if __name__ == "__main__":
    unittest.main()
