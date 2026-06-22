"""Tests for peScanController scan/org resolution."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from pe.peScanController import resolve_orgs, resolve_scans


class ResolveScansTests(unittest.TestCase):
    def test_catalog_default_count(self):
        scans = resolve_scans(["dnstwist"])
        self.assertEqual(scans[0]["scan"], "dnstwist")
        self.assertEqual(scans[0]["count"], 142)

    def test_task_count_overrides_catalog(self):
        scans = resolve_scans(["dnstwist"], task_count=3)
        self.assertEqual(scans[0]["count"], 3)

    def test_task_count_overrides_inline(self):
        scans = resolve_scans([{"scan": "dnstwist", "count": 99}], task_count=2)
        self.assertEqual(scans[0]["count"], 2)

    def test_unknown_scan_raises(self):
        with self.assertRaises(ValueError):
            resolve_scans(["not-a-scan"])


class NormalizeLocalQueueUrlTests(unittest.TestCase):
    def test_replaces_localhost_with_elasticmq(self):
        from pe.peScanController import normalize_local_queue_url

        with patch.dict(
            os.environ,
            {"SQS_ENDPOINT_URL": "http://elasticmq:9324"},
            clear=False,
        ):
            url = normalize_local_queue_url(
                "http://localhost:9324/000000000000/staging-dnstwist-queue"
            )
        self.assertEqual(
            url, "http://elasticmq:9324/000000000000/staging-dnstwist-queue"
        )


class HostBindSourceTests(unittest.TestCase):
    def test_reads_bind_source_from_mountinfo(self):
        from pe.peScanController import host_bind_source_for_container_path

        mount_line = (
            "1234 567 0:23 / /app/pe rw,relatime master:1 - "
            "bind /Users/dev/XFD/backend/pe rw,relatime"
        )
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PE_DEV_MOUNT_HOST", None)
            with patch("builtins.open", mock_open(read_data=mount_line)):
                host_path = host_bind_source_for_container_path("/app/pe")
        self.assertEqual(host_path, "/Users/dev/XFD/backend/pe")

    def test_env_override(self):
        from pe.peScanController import host_bind_source_for_container_path

        with patch.dict(
            os.environ,
            {"PE_DEV_MOUNT_HOST": "/explicit/host/pe"},
            clear=False,
        ):
            self.assertEqual(
                host_bind_source_for_container_path("/app/pe"),
                "/explicit/host/pe",
            )


class ResolveOrgsTests(unittest.TestCase):
    def test_explicit_orgs_pass_through(self):
        self.assertEqual(resolve_orgs(["NSF", "DHS"]), ["NSF", "DHS"])

    def test_batch_shortcuts(self):
        self.assertEqual(resolve_orgs(["all"]), ["all"])
        self.assertEqual(resolve_orgs(["DEMO"]), ["DEMO"])

    @patch("pe.peScanController.fetch_orgs_from_db")
    def test_expand_all_orgs(self, fetch_mock):
        fetch_mock.return_value = ["NSF", "DHS"]
        self.assertEqual(resolve_orgs(["all-orgs"]), ["NSF", "DHS"])
        fetch_mock.assert_called_once_with(report_on=True, demo=False)

    @patch("pe.peScanController.fetch_orgs_from_db")
    def test_expand_demo_orgs(self, fetch_mock):
        fetch_mock.return_value = ["DEMO1"]
        self.assertEqual(resolve_orgs(["demo-orgs"]), ["DEMO1"])
        fetch_mock.assert_called_once_with(report_on=False, demo=True)

    def test_expand_shortcut_cannot_be_mixed(self):
        with self.assertRaises(ValueError):
            resolve_orgs(["all-orgs", "NSF"])


class FetchOrgsFromDbTests(unittest.TestCase):
    @patch("psycopg2.connect")
    def test_fetch_report_on_orgs(self, connect_mock):
        from pe.peScanController import fetch_orgs_from_db

        cursor = MagicMock()
        cursor.fetchall.return_value = [("NSF",), ("DHS",)]
        connect_mock.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            cursor
        )

        names = fetch_orgs_from_db(report_on=True)
        self.assertEqual(names, ["NSF", "DHS"])
        cursor.execute.assert_called_once()
        self.assertIn("report_on = true", cursor.execute.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
