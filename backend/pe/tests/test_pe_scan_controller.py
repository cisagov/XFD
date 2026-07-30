"""Tests for peScanController scan/org resolution."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

# Third-Party Libraries
from pe.peScanController import (
    queue_name_for_scan,
    queue_url_for_scan,
    resolve_orgs,
    resolve_scans,
    run,
)


class QueueNameTests(unittest.TestCase):
    """Verify PE queue names are separate from XFD scan queues."""

    def test_default_prefix(self):
        """PE queues should use the pe-staging prefix by default."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PE_QUEUE_PREFIX", None)
            self.assertEqual(
                queue_name_for_scan("dnstwist"), "pe-staging-dnstwist-queue"
            )

    def test_custom_prefix(self):
        """PE_QUEUE_PREFIX should override the default queue prefix."""
        with patch.dict(os.environ, {"PE_QUEUE_PREFIX": "pe-integration"}, clear=False):
            self.assertEqual(
                queue_name_for_scan("shodan"), "pe-integration-shodan-queue"
            )


class QueueUrlForScanTests(unittest.TestCase):
    """Verify scan queues are created before messages are sent."""

    @patch("pe.peScanController.sqs_client")
    @patch("pe.peScanController.sqs_endpoint_url", return_value=None)
    def test_aws_create_queue_before_send(self, _endpoint_mock, client_mock):
        """AWS deployments should create the queue when it does not exist yet."""
        client = MagicMock()
        client_mock.return_value = client
        client.create_queue.return_value = {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/pe-staging-dnstwist-queue"
        }
        with patch.dict(os.environ, {"PE_QUEUE_PREFIX": "pe-staging"}, clear=False):
            url = queue_url_for_scan("dnstwist")
        self.assertEqual(
            url, "https://sqs.us-east-1.amazonaws.com/123/pe-staging-dnstwist-queue"
        )
        client.create_queue.assert_called_once()
        create_kwargs = client.create_queue.call_args.kwargs
        self.assertEqual(create_kwargs["QueueName"], "pe-staging-dnstwist-queue")
        self.assertEqual(create_kwargs["Attributes"]["VisibilityTimeout"], "18000")
        client.set_queue_attributes.assert_called_once()


class ResolveScansTests(unittest.TestCase):
    """Verify scan catalog resolution and taskCount overrides."""

    def test_catalog_default_count(self):
        """Use the catalog default worker count when taskCount is omitted."""
        scans = resolve_scans(["dnstwist"])
        self.assertEqual(scans[0]["scan"], "dnstwist")
        self.assertEqual(scans[0]["count"], 142)

    def test_task_count_overrides_catalog(self):
        """The taskCount parameter should override the catalog default."""
        scans = resolve_scans(["dnstwist"], task_count=3)
        self.assertEqual(scans[0]["count"], 3)

    def test_task_count_overrides_inline(self):
        """The taskCount parameter should override inline scan config counts."""
        scans = resolve_scans([{"scan": "dnstwist", "count": 99}], task_count=2)
        self.assertEqual(scans[0]["count"], 2)

    def test_catalog_includes_flare_events(self):
        """flare_events should be available in the PE scan catalog."""
        scans = resolve_scans(["flare_events"])
        self.assertEqual(scans[0]["scan"], "flare_events")
        self.assertGreaterEqual(scans[0]["count"], 1)

    def test_unknown_scan_raises(self):
        """Unknown scan names should raise ValueError."""
        with self.assertRaises(ValueError):
            resolve_scans(["not-a-scan"])


class NormalizeLocalQueueUrlTests(unittest.TestCase):
    """Verify localhost queue URL rewriting for Docker workers."""

    def test_replaces_localhost_with_elasticmq(self):
        """Replace localhost in queue URLs with the ElasticMQ service host."""
        # Third-Party Libraries
        from pe.peScanController import normalize_local_queue_url

        with patch.dict(
            os.environ,
            {"SQS_ENDPOINT_URL": "http://elasticmq:9324"},
            clear=False,
        ):
            url = normalize_local_queue_url(
                "http://localhost:9324/000000000000/pe-staging-dnstwist-queue"
            )
            self.assertEqual(
                url, "http://elasticmq:9324/000000000000/pe-staging-dnstwist-queue"
            )


class HostBindSourceTests(unittest.TestCase):
    """Verify host bind path resolution for local dev mounts."""

    def test_reads_bind_source_from_mountinfo(self):
        """Read the host bind source from /proc/self/mountinfo."""
        # Third-Party Libraries
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
        """PE_DEV_MOUNT_HOST should override mountinfo discovery."""
        # Third-Party Libraries
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
    """Verify org list resolution and shortcut expansion."""

    def test_explicit_orgs_pass_through(self):
        """Explicit org names should pass through unchanged."""
        self.assertEqual(resolve_orgs(["NSF", "DHS"]), ["NSF", "DHS"])

    def test_batch_shortcuts(self):
        """Batch shortcuts should pass through as a single token."""
        self.assertEqual(resolve_orgs(["all"]), ["all"])
        self.assertEqual(resolve_orgs(["DEMO"]), ["DEMO"])

    @patch("pe.peScanController.fetch_orgs_from_db")
    def test_expand_all_orgs(self, fetch_mock):
        """The all-orgs shortcut should expand to report_on orgs from the PE DB."""
        fetch_mock.return_value = ["NSF", "DHS"]
        self.assertEqual(resolve_orgs(["all-orgs"]), ["NSF", "DHS"])
        fetch_mock.assert_called_once_with(report_on=True)

    @patch("pe.peScanController.fetch_orgs_from_db")
    def test_expand_demo_orgs(self, fetch_mock):
        """demo-orgs should expand to demo orgs from the PE database."""
        fetch_mock.return_value = ["DEMO1"]
        self.assertEqual(resolve_orgs(["demo-orgs"]), ["DEMO1"])
        fetch_mock.assert_called_once_with(demo=True)

    def test_expand_shortcut_cannot_be_mixed(self):
        """Expand shortcuts cannot be combined with named orgs."""
        with self.assertRaises(ValueError):
            resolve_orgs(["all-orgs", "NSF"])


class RunKeyedScanPreflightTests(unittest.TestCase):
    """Verify keyed-scan validation happens before SQS enqueue."""

    @patch("pe.peScanController.queue_messages")
    @patch("pe.peScanController.plan_worker_keys_for_scans")
    def test_key_planning_failure_does_not_queue(self, plan_mock, queue_mock):
        """Invalid keyed scans should fail before any messages are sent."""
        plan_mock.side_effect = ValueError("FLARE_API_KEYS is empty")

        with self.assertRaises(ValueError):
            run(
                {
                    "scans": ["flare_events"],
                    "orgs": ["DHS"],
                    "queueOnly": False,
                    "tasksOnly": False,
                    "local": True,
                }
            )

        queue_mock.assert_not_called()

    @patch("pe.peScanController.start_workers", return_value={})
    @patch("pe.peScanController.queue_messages", return_value={"flare_events": 1})
    @patch(
        "pe.peScanController.plan_worker_keys_for_scans",
        return_value={"flare_events": ["k1"]},
    )
    def test_key_planning_before_queue(self, plan_mock, queue_mock, _start_mock):
        """Keyed scans should be validated before messages are enqueued."""
        result = run(
            {
                "scans": ["flare_events"],
                "orgs": ["DHS"],
                "queueOnly": False,
                "tasksOnly": False,
                "local": True,
            }
        )

        self.assertEqual(result["statusCode"], 200)
        plan_mock.assert_called_once()
        queue_mock.assert_called_once()
        self.assertLess(plan_mock.call_args, queue_mock.call_args)


class FetchOrgsFromDbTests(unittest.TestCase):
    """Verify PE database org lookup for shortcut expansion."""

    @patch("psycopg2.connect")
    def test_fetch_report_on_orgs(self, connect_mock):
        """Fetch report_on organizations from the PE database."""
        # Third-Party Libraries
        from pe.peScanController import fetch_orgs_from_db

        cursor = MagicMock()
        cursor.fetchall.return_value = [("NSF",), ("DHS",)]
        cursor_ctx = connect_mock.return_value.__enter__.return_value.cursor
        cursor_ctx.return_value.__enter__.return_value = cursor

        names = fetch_orgs_from_db(report_on=True)
        self.assertEqual(names, ["NSF", "DHS"])
        cursor.execute.assert_called_once()
        self.assertIn("report_on = true", cursor.execute.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
