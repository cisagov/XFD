"""Unit tests for Shodan top-CVE orchestration."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
import pandas as pd

from pe_source.shodan.shodan_top_cves import (
    get_cve_details,
    get_shodan_cve_info,
    run_top_cves_shodan,
)

class ShodanTopCvesTests(unittest.TestCase):
    """Verify Shodan top-CVE helpers and orchestration."""

    @patch("pe_source.shodan.shodan_top_cves.time.sleep")
    @patch("pe_source.shodan.shodan_top_cves.requests.get")
    def test_get_shodan_cve_info_retries_and_returns_json(
        self, mock_get, mock_sleep
    ):
        """Transient HTTP failures should retry and return the final JSON payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"dynamic_rating": 0.42, "summary": "ok"}
        mock_get.side_effect = [
            MagicMock(status_code=500),
            MagicMock(status_code=503),
            mock_response,
        ]

        result = get_shodan_cve_info("CVE-2026-0001")

        self.assertEqual(result, {"dynamic_rating": 0.42, "summary": "ok"})
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)


    @patch("pe_source.shodan.shodan_top_cves.get_shodan_cve_info")
    def test_get_cve_details_builds_expected_dataframe(self, mock_get_info):
        """CVE detail retrieval should assemble the expected dataframe rows."""
        mock_get_info.return_value = {
            "epss": 0.25,
            "v2": 5.0,
            "v3": 7.5,
            "summary": "A sample issue.",
        }

        details = get_cve_details(["CVE-2026-0001"])

        self.assertIsInstance(details, pd.DataFrame)
        self.assertEqual(len(details), 1)
        self.assertEqual(details.iloc[0]["cve_id"], "CVE-2026-0001")
        self.assertEqual(details.iloc[0]["dynamic_rating"], '25.0')
        self.assertIn("v2", details.iloc[0]["nvd_base_score"])
        self.assertIn("v3", details.iloc[0]["nvd_base_score"])
        self.assertEqual(details.iloc[0]["summary"], "A sample issue.")
        mock_get_info.assert_called_once_with("CVE-2026-0001")

    @patch("pe_source.shodan.shodan_top_cves.insert_shodan_top_cves")
    @patch("pe_source.shodan.shodan_top_cves.get_cve_details")
    @patch("pe_source.shodan.shodan_top_cves.get_all_shodan_cves")
    def test_run_top_cves_shodan_uses_top_ten_sorted_by_dynamic_rating(
        self, mock_query, mock_get_details, mock_insert
    ):
        """The orchestration should query distinct CVEs, enrich them, sort, and write the top 10."""
        mock_query.return_value = pd.DataFrame(
            {"cve": [f"CVE-2026-{idx:04d}" for idx in range(1, 12)]}
        )
        mock_get_details.return_value = pd.DataFrame(
            [
                {"cve_id": "CVE-2026-0001", "dynamic_rating": 1.0, "summary": "one"},
                {"cve_id": "CVE-2026-0002", "dynamic_rating": 5.0, "summary": "two"},
                {"cve_id": "CVE-2026-0003", "dynamic_rating": 3.0, "summary": "three"},
                {"cve_id": "CVE-2026-0004", "dynamic_rating": 7.0, "summary": "four"},
                {"cve_id": "CVE-2026-0005", "dynamic_rating": 2.0, "summary": "five"},
                {"cve_id": "CVE-2026-0006", "dynamic_rating": 8.0, "summary": "six"},
                {"cve_id": "CVE-2026-0007", "dynamic_rating": 0.5, "summary": "seven"},
                {"cve_id": "CVE-2026-0008", "dynamic_rating": 6.0, "summary": "eight"},
                {"cve_id": "CVE-2026-0009", "dynamic_rating": 4.0, "summary": "nine"},
                {"cve_id": "CVE-2026-0010", "dynamic_rating": 9.0, "summary": "ten"},
                {"cve_id": "CVE-2026-0011", "dynamic_rating": 0.1, "summary": "eleven"},
            ]
        )

        run_top_cves_shodan()

        mock_query.assert_called_once()
        mock_get_details.assert_called_once_with(
            ["CVE-2026-0001", "CVE-2026-0002", "CVE-2026-0003", "CVE-2026-0004", "CVE-2026-0005", "CVE-2026-0006", "CVE-2026-0007", "CVE-2026-0008", "CVE-2026-0009", "CVE-2026-0010", "CVE-2026-0011"]
        )
        mock_insert.assert_called_once()
        inserted = mock_insert.call_args.args[0]
        self.assertEqual(inserted[0]["cve_id"], "CVE-2026-0010")
        self.assertEqual(inserted[1]["cve_id"], "CVE-2026-0006")
        self.assertEqual(inserted[2]["cve_id"], "CVE-2026-0004")
        self.assertEqual(inserted[3]["cve_id"], "CVE-2026-0008")
        self.assertEqual(inserted[4]["cve_id"], "CVE-2026-0002")
        self.assertEqual(inserted[5]["cve_id"], "CVE-2026-0009")
        self.assertEqual(inserted[6]["cve_id"], "CVE-2026-0003")
        self.assertEqual(inserted[7]["cve_id"], "CVE-2026-0005")
        self.assertEqual(inserted[8]["cve_id"], "CVE-2026-0001")
        self.assertEqual(inserted[9]["cve_id"], "CVE-2026-0007")
        self.assertEqual(inserted[-1]["cve_id"], "CVE-2026-0007")


if __name__ == "__main__":
    unittest.main()
