"""Tests for peReportController org resolution."""

# Standard Python Libraries
import unittest
from unittest.mock import patch

# Third-Party Libraries
from pe.peReportController import chunk_report_orgs, resolve_report_orgs


class ResolveReportOrgsTests(unittest.TestCase):
    """resolve_report_orgs maps scan-style shortcuts to pe-reports --orgs values."""

    def test_all_shortcut(self):
        """Map all shortcut to pe-reports batch mode."""
        self.assertEqual(resolve_report_orgs(["all"]), "all")

    def test_demo_shortcut(self):
        """Map demo shortcut to pe-reports batch mode."""
        self.assertEqual(resolve_report_orgs(["demo"]), "demo")

    def test_named_orgs(self):
        """Join explicit org codes for pe-reports."""
        self.assertEqual(resolve_report_orgs(["DHS", "DHS_CISA"]), "DHS,DHS_CISA")

    @patch("pe.peReportController.fetch_orgs_from_db")
    def test_all_orgs_expands(self, mock_fetch):
        """Expand all-orgs into a comma-separated org list."""
        mock_fetch.return_value = ["A", "B"]
        self.assertEqual(resolve_report_orgs(["all-orgs"]), "A,B")
        mock_fetch.assert_called_once_with(report_on=True)


class ChunkReportOrgsTests(unittest.TestCase):
    """chunk_report_orgs splits work across Fargate tasks."""

    def test_batch_shortcut_not_split(self):
        """Leave batch shortcuts intact when chunking."""
        self.assertEqual(chunk_report_orgs("all", 3), ["all"])

    def test_splits_comma_list(self):
        """Round-robin split comma-separated org lists across tasks."""
        chunks = chunk_report_orgs("A,B,C,D", 2)
        self.assertEqual(chunks, ["A,C", "B,D"])


if __name__ == "__main__":
    unittest.main()
