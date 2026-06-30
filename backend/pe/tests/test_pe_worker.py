"""Tests for PE SQS worker queue drain logic."""

# Standard Python Libraries
import json
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
from worker.pe_worker import (
    extend_message_visibility,
    parse_org,
    queue_confirmed_empty,
    receive_message,
)


class ParseOrgTests(unittest.TestCase):
    """Verify organization parsing from SQS messages."""

    def test_json_body(self):
        """Parse org from a JSON message body."""
        message = {"Body": json.dumps({"org": "NSF"})}
        self.assertEqual(parse_org(message), "NSF")

    def test_missing_org(self):
        """Return None when the message body has no org field."""
        self.assertIsNone(parse_org({"Body": "{}"}))


class ReceiveMessageTests(unittest.TestCase):
    """Verify SQS receive_message empty-response handling."""

    def test_returns_none_when_no_messages(self):
        """Return None when the SQS response omits Messages."""
        client = MagicMock()
        client.receive_message.return_value = {}
        self.assertIsNone(receive_message(client, "http://example/queue"))

    def test_returns_none_when_messages_null(self):
        """Return None when Messages is explicitly null."""
        client = MagicMock()
        client.receive_message.return_value = {"Messages": None}
        self.assertIsNone(receive_message(client, "http://example/queue"))

    def test_returns_first_message(self):
        """Return the first message when Messages is populated."""
        client = MagicMock()
        msg = {"Body": '{"org":"NSF"}', "ReceiptHandle": "rh1"}
        client.receive_message.return_value = {"Messages": [msg]}
        self.assertEqual(receive_message(client, "http://example/queue"), msg)


class ExtendVisibilityTests(unittest.TestCase):
    """Verify long scans extend SQS visibility before processing."""

    def test_extends_visibility(self):
        """Reset visibility timeout when a scan starts."""
        client = MagicMock()
        extend_message_visibility(client, "http://example/queue", "rh1")
        client.change_message_visibility.assert_called_once_with(
            QueueUrl="http://example/queue",
            ReceiptHandle="rh1",
            VisibilityTimeout=18000,
        )


class QueueConfirmedEmptyTests(unittest.TestCase):
    """Verify double-check logic before worker exit."""

    @patch("worker.pe_worker.time.sleep")
    @patch("worker.pe_worker.receive_message")
    def test_confirmed_empty(self, receive_mock, sleep_mock):
        """Confirm empty when the recheck poll also finds no messages."""
        receive_mock.return_value = None
        client = MagicMock()
        self.assertTrue(queue_confirmed_empty(client, "http://example/queue"))
        sleep_mock.assert_called_once()

    @patch("worker.pe_worker.time.sleep")
    @patch("worker.pe_worker.receive_message")
    def test_not_empty_on_recheck(self, receive_mock, sleep_mock):
        """Return false when a message appears on the recheck poll."""
        receive_mock.return_value = {"Body": '{"org":"NSF"}'}
        client = MagicMock()
        self.assertFalse(queue_confirmed_empty(client, "http://example/queue"))


if __name__ == "__main__":
    unittest.main()
