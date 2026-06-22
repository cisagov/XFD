"""Tests for PE SQS worker queue drain logic."""

# Standard Python Libraries
import json
import unittest
from unittest.mock import MagicMock, patch

from worker.pe_worker import parse_org, queue_confirmed_empty, receive_message


class ParseOrgTests(unittest.TestCase):
    def test_json_body(self):
        message = {"Body": json.dumps({"org": "NSF"})}
        self.assertEqual(parse_org(message), "NSF")

    def test_missing_org(self):
        self.assertIsNone(parse_org({"Body": "{}"}))


class ReceiveMessageTests(unittest.TestCase):
    def test_returns_none_when_no_messages(self):
        client = MagicMock()
        client.receive_message.return_value = {}
        self.assertIsNone(receive_message(client, "http://example/queue"))

    def test_returns_none_when_messages_null(self):
        client = MagicMock()
        client.receive_message.return_value = {"Messages": None}
        self.assertIsNone(receive_message(client, "http://example/queue"))

    def test_returns_first_message(self):
        client = MagicMock()
        msg = {"Body": '{"org":"NSF"}', "ReceiptHandle": "rh1"}
        client.receive_message.return_value = {"Messages": [msg]}
        self.assertEqual(receive_message(client, "http://example/queue"), msg)


class QueueConfirmedEmptyTests(unittest.TestCase):
    @patch("worker.pe_worker.time.sleep")
    @patch("worker.pe_worker.receive_message")
    def test_confirmed_empty(self, receive_mock, sleep_mock):
        receive_mock.return_value = None
        client = MagicMock()
        self.assertTrue(queue_confirmed_empty(client, "http://example/queue"))
        sleep_mock.assert_called_once()

    @patch("worker.pe_worker.time.sleep")
    @patch("worker.pe_worker.receive_message")
    def test_not_empty_on_recheck(self, receive_mock, sleep_mock):
        receive_mock.return_value = {"Body": '{"org":"NSF"}'}
        client = MagicMock()
        self.assertFalse(queue_confirmed_empty(client, "http://example/queue"))


if __name__ == "__main__":
    unittest.main()
