"""Tests for the WAS Qualys client boundary."""

# Standard Python Libraries
import unittest
from unittest.mock import patch

# Third-Party Libraries
import requests

# First-Party Libraries
from was_reports.qualys.qualys_client import (
    QualysClient,
    QualysRequest,
    QualysRetryPolicy,
    TimeoutSession,
    create_qualys_client,
    is_retry_safe,
)
from was_reports.utils.qualys_config import QualysCredentials


class FakeQualysConnection:
    """Small Qualys connection test double."""

    def __init__(self, responses=None):
        """Initialize captured request state."""
        self.calls = []
        self.responses = list(responses or [])
        self.session: object | None = None

    def request(self, endpoint, payload=None, http_method=None):
        """Capture request arguments and return a fake XML response."""
        self.calls.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "http_method": http_method,
            }
        )
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return "<response />"


def http_error(status_code: int, retry_after: str = "") -> requests.HTTPError:
    """Return an HTTP error with response metadata for retry tests."""
    response = requests.Response()
    response.status_code = status_code
    if retry_after:
        response.headers["Retry-After"] = retry_after
    return requests.HTTPError(response=response)


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

    def test_search_request_retries_transient_connection_failures(self) -> None:
        """Retry a read-safe POST search using bounded exponential backoff."""
        connection = FakeQualysConnection(
            [
                requests.ConnectionError("connection failed"),
                requests.Timeout("request timed out"),
                "<response />",
            ]
        )
        sleep_calls: list[float] = []
        client = QualysClient(
            connection,
            retry_policy=QualysRetryPolicy(max_attempts=4),
            sleep_function=sleep_calls.append,
            random_function=lambda: 0.0,
        )

        response = client.request(
            QualysRequest(
                endpoint="/search/was/finding",
                payload="<ServiceRequest />",
                http_method="POST",
            )
        )

        self.assertEqual(response, "<response />")
        self.assertEqual(len(connection.calls), 3)
        self.assertEqual(sleep_calls, [1.0, 2.0])

    def test_retry_honors_retry_after_within_configured_maximum(self) -> None:
        """Use a Qualys rate-limit delay when it exceeds exponential backoff."""
        connection = FakeQualysConnection([http_error(429, "12"), "<response />"])
        sleep_calls: list[float] = []
        client = QualysClient(
            connection,
            retry_policy=QualysRetryPolicy(max_attempts=2),
            sleep_function=sleep_calls.append,
            random_function=lambda: 0.0,
        )

        client.request(QualysRequest(endpoint="/count/was/webapp"))

        self.assertEqual(sleep_calls, [12.0])

    def test_create_request_does_not_retry_transient_failure(self) -> None:
        """Avoid duplicate reports by keeping create operations single-attempt."""
        connection = FakeQualysConnection([requests.Timeout("request timed out")])
        client = QualysClient(
            connection,
            retry_policy=QualysRetryPolicy(max_attempts=4),
            sleep_function=lambda seconds: self.fail("Unexpected retry sleep."),
        )

        with self.assertRaises(requests.Timeout):
            client.request(
                QualysRequest(
                    endpoint="/create/was/report",
                    payload="<ServiceRequest />",
                    http_method="POST",
                )
            )

        self.assertEqual(len(connection.calls), 1)

    def test_nontransient_client_error_does_not_retry(self) -> None:
        """Do not retry authentication, authorization, or validation failures."""
        connection = FakeQualysConnection([http_error(401)])
        client = QualysClient(
            connection,
            retry_policy=QualysRetryPolicy(max_attempts=4),
            sleep_function=lambda seconds: self.fail("Unexpected retry sleep."),
        )

        with self.assertRaises(requests.HTTPError):
            client.request(QualysRequest(endpoint="/search/was/webapp"))

        self.assertEqual(len(connection.calls), 1)

    def test_retry_safe_classification_allows_explicit_override(self) -> None:
        """Allow callers to explicitly disable inferred retry safety."""
        self.assertTrue(is_retry_safe(QualysRequest(endpoint="search/am/tag")))
        self.assertFalse(
            is_retry_safe(QualysRequest(endpoint="search/am/tag", retry_safe=False))
        )

    @patch("requests.Session.get")
    def test_timeout_session_applies_default_timeout(self, mock_get) -> None:
        """Apply a timeout to connector requests that omit one."""
        session = TimeoutSession(timeout_seconds=45.0)

        session.get("https://qualys.example/test")

        self.assertEqual(mock_get.call_args.kwargs["timeout"], 45.0)

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

        retry_policy = QualysRetryPolicy(request_timeout_seconds=45.0)
        client = create_qualys_client(credentials, retry_policy=retry_policy)

        self.assertIsInstance(client, QualysClient)
        mock_connector.assert_called_once_with(
            auth=("user", "secret"),
            server="qualys.example",
            max_retries=0,
        )
        self.assertIsInstance(connection.session, TimeoutSession)


if __name__ == "__main__":
    unittest.main()
