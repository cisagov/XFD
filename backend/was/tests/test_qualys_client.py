"""Tests for the WAS Qualys client boundary."""

# Standard Python Libraries
import sys
import tempfile
import types
import unittest
from pathlib import Path

# First-Party Libraries
from was_reports.qualys.qualys_client import (
    QualysClient,
    QualysRequest,
    create_qualys_client,
)


class FakeQualysConnection:
    """Small Qualys connection test double."""

    def __init__(self):
        """Initialize captured request state."""
        self.calls = []

    def request(self, endpoint, payload=None, http_method=None):
        """Capture request arguments and return a fake XML response."""
        self.calls.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "http_method": http_method,
            }
        )
        return "<response />"


class QualysClientTests(unittest.TestCase):
    """Validate legacy-compatible Qualys request behavior."""

    def test_request_without_payload_uses_endpoint_only(self) -> None:
        """Call the legacy connection with only an endpoint."""
        connection = FakeQualysConnection()
        client = QualysClient(connection)

        response = client.request(QualysRequest(endpoint="/download/was/report/1"))

        self.assertEqual(response, "<response />")
        self.assertEqual(
            connection.calls[0],
            {
                "endpoint": "/download/was/report/1",
                "payload": None,
                "http_method": None,
            },
        )

    def test_request_with_payload_forwards_payload(self) -> None:
        """Call the legacy connection with endpoint and payload."""
        connection = FakeQualysConnection()
        client = QualysClient(connection)

        client.request(
            QualysRequest(endpoint="/search/was/webapp", payload="<ServiceRequest />")
        )

        self.assertEqual(connection.calls[0]["endpoint"], "/search/was/webapp")
        self.assertEqual(connection.calls[0]["payload"], "<ServiceRequest />")
        self.assertIsNone(connection.calls[0]["http_method"])

    def test_request_with_method_forwards_http_method(self) -> None:
        """Call the legacy connection with endpoint, payload, and method."""
        connection = FakeQualysConnection()
        client = QualysClient(connection)

        client.request(
            QualysRequest(
                endpoint="/create/was/report",
                payload="<ServiceRequest />",
                http_method="POST",
            )
        )

        self.assertEqual(connection.calls[0]["endpoint"], "/create/was/report")
        self.assertEqual(connection.calls[0]["payload"], "<ServiceRequest />")
        self.assertEqual(connection.calls[0]["http_method"], "POST")

    def test_request_with_method_only_forwards_http_method(self) -> None:
        """Call the legacy connection with endpoint and method only."""
        connection = FakeQualysConnection()
        client = QualysClient(connection)

        client.request(
            QualysRequest(endpoint="/download/was/report/1", http_method="get")
        )

        self.assertEqual(connection.calls[0]["endpoint"], "/download/was/report/1")
        self.assertIsNone(connection.calls[0]["payload"])
        self.assertEqual(connection.calls[0]["http_method"], "get")

    def test_create_qualys_client_validates_config_before_connecting(self) -> None:
        """Validate config and create a client without returning credentials."""
        module_name = "qualysapi"
        fake_module = types.SimpleNamespace()
        captured_config_paths = []

        def connect(config_path):
            """Capture the config path supplied to qualysapi.connect."""
            captured_config_paths.append(config_path)
            return FakeQualysConnection()

        fake_module.connect = connect
        original_module = sys.modules.get(module_name)
        sys.modules[module_name] = fake_module

        try:
            with tempfile.TemporaryDirectory() as directory:
                config_path = Path(directory) / "was_config.txt"
                config_path.write_text(
                    "[info]\n"
                    "username = user\n"
                    "password = secret\n"
                    "hostname = qualys.example\n",
                    encoding="utf-8",
                )

                client = create_qualys_client(config_path)
        finally:
            if original_module is None:
                del sys.modules[module_name]
            else:
                sys.modules[module_name] = original_module

        self.assertIsInstance(client, QualysClient)
        self.assertEqual(captured_config_paths, [config_path])


if __name__ == "__main__":
    unittest.main()
