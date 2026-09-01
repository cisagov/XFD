"""Tests for the WAS Qualys client boundary."""

# Standard Python Libraries
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.qualys.qualys_client import (
    QualysClient,
    QualysRequest,
    create_qualys_client,
)
from was_reports.utils.qualys_config import QualysCredentials


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

    @patch("qualysapi.connector.QGConnector")
    def test_create_qualys_client_uses_credentials_directly(
        self,
        mock_connector,
    ) -> None:
        """Create a Qualys connector without writing a configuration file."""
        connection = FakeQualysConnection()
        mock_connector.return_value = connection
        credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )

        client = create_qualys_client(credentials)

        self.assertIsInstance(client, QualysClient)
        mock_connector.assert_called_once_with(
            auth=("user", "secret"),
            server="qualys.example",
        )


if __name__ == "__main__":
    unittest.main()
