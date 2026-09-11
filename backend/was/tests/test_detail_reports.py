"""Tests for Qualys detail-report download helpers."""

# Standard Python Libraries
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

# Third-Party Libraries
import requests

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, QualysRetryPolicy
from was_reports.reporting import detail_reports
from was_reports.utils.qualys_config import QualysCredentials


class FakeConnection:
    """Small Qualys status connection fake."""

    def __init__(self, responses):
        """Initialize response queue and captured calls."""
        self.responses = list(responses)
        self.calls = []

    def request(self, endpoint, payload=None, http_method=None):
        """Capture a request and return the next fake response."""
        self.calls.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "http_method": http_method,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeResponse:
    """Small HTTP response fake."""

    def __init__(self, content: bytes):
        """Initialize response content."""
        self.content = content
        self.raise_for_status_called = False

    def raise_for_status(self):
        """Record status validation."""
        self.raise_for_status_called = True


class FakeSession:
    """Small requests session fake."""

    def __init__(self):
        """Initialize captured HTTP state."""
        self.auth = None
        self.urls = []
        self.response = FakeResponse(b"pdf-content")

    def get(self, url: str):
        """Capture requested URL and return a fake response."""
        self.urls.append(url)
        return self.response


class RetryingFakeSession(FakeSession):
    """Session fake that returns or raises queued outcomes."""

    def __init__(self, outcomes):
        """Initialize queued download outcomes."""
        super().__init__()
        self.outcomes = list(outcomes)

    def get(self, url: str):
        """Capture a URL and return or raise the next queued outcome."""
        self.urls.append(url)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class DetailReportsTests(unittest.TestCase):
    """Validate detail-report helper behavior."""

    def test_polling_does_not_start_another_request_at_deadline(self) -> None:
        """Bound sleeps and stop before issuing a request after expiry."""
        times = iter([0.0, 9.5, 10.0])
        sleeper = Mock()
        with patch.object(
            detail_reports.report_data, "get_report_status", return_value="RUNNING"
        ) as status:
            with self.assertRaises(TimeoutError):
                detail_reports.wait_for_report_completion(
                    Mock(),
                    "123",
                    sleep_seconds=60,
                    timeout_seconds=10,
                    sleep_function=sleeper,
                    monotonic_function=lambda: next(times),
                )
        sleeper.assert_called_once_with(0.5)
        status.assert_called_once()

    def test_polling_propagates_permanent_http_and_tls_errors(self) -> None:
        """Do not loop on authorization, invalid requests, or certificate errors."""
        errors: list[Exception] = [
            requests.exceptions.SSLError("certificate validation failed")
        ]
        for status_code in (400, 401, 403, 404):
            response = requests.Response()
            response.status_code = status_code
            errors.append(requests.HTTPError(response=response))
        for error in errors:
            with self.subTest(error=type(error).__name__):
                sleep = Mock()
                with patch.object(
                    detail_reports.report_data, "get_report_status", side_effect=error
                ):
                    with self.assertRaises(type(error)):
                        detail_reports.wait_for_report_completion(
                            Mock(), "123", sleep_function=sleep
                        )
                sleep.assert_not_called()

    def test_polling_retries_throttling_and_server_failures(self) -> None:
        """Continue status reads after transient HTTP failures."""
        for status_code in (429, 500, 502, 503, 504):
            response = requests.Response()
            response.status_code = status_code
            sleep = Mock()
            with self.subTest(status_code=status_code), patch.object(
                detail_reports.report_data,
                "get_report_status",
                side_effect=[requests.HTTPError(response=response), "COMPLETE"],
            ):
                detail_reports.wait_for_report_completion(
                    Mock(), "123", sleep_function=sleep
                )
                sleep.assert_called_once()

    def test_sanitized_detail_filename_matches_legacy_behavior(self) -> None:
        """Remove URL characters from detail filenames."""
        filename = detail_reports.sanitized_detail_filename(
            "https://example.gov:443/a path"
        )

        self.assertEqual(filename, "example.gov443apath")

    def test_detail_pdf_path_uses_docs_for_webapp_exports(self) -> None:
        """Use the output directory for details-only web app exports."""
        output_path = detail_reports.detail_pdf_path(
            filename="https://example.gov/a path",
            output_directory=Path("/reports"),
            asset_directory=Path("/legacy/assets"),
            from_webapp=True,
        )

        self.assertEqual(output_path, Path("/reports/example.govapathDetails.pdf"))

    def test_detail_pdf_path_uses_assets_for_tag_reports(self) -> None:
        """Use the legacy asset directory for normal tag detail reports."""
        output_path = detail_reports.detail_pdf_path(
            filename="CUSTOMER_TAG",
            output_directory=Path("/reports"),
            asset_directory=Path("/legacy/assets"),
            from_webapp=False,
        )

        self.assertEqual(output_path, Path("/legacy/assets/CUSTOMER_TAGDetails.pdf"))

    def test_wait_for_report_completion_polls_until_complete(self) -> None:
        """Poll Qualys status until the detail report is complete."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <data><Report><status>RUNNING</status></Report></data>
                </ServiceResponse>
                """,
                """
                <ServiceResponse>
                    <data><Report><status>COMPLETE</status></Report></data>
                </ServiceResponse>
                """,
            ]
        )
        sleep_calls: list[int] = []

        with self.assertLogs(detail_reports.LOGGER, level="INFO") as captured:
            detail_reports.wait_for_report_completion(
                client=QualysClient(connection),
                report_id="123",
                sleep_seconds=1,
                sleep_function=sleep_calls.append,
            )

        self.assertEqual(sleep_calls, [1])
        self.assertEqual(len(connection.calls), 2)
        messages = " ".join(captured.output)
        self.assertIn("status is RUNNING", messages)
        self.assertIn("completed after", messages)

    def test_wait_for_report_completion_rejects_error_status(self) -> None:
        """Fail when Qualys returns an error status."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <data><Report><status>ERROR</status></Report></data>
                </ServiceResponse>
                """
            ]
        )

        with self.assertRaises(RuntimeError):
            detail_reports.wait_for_report_completion(
                client=QualysClient(connection),
                report_id="123",
                sleep_function=lambda seconds: None,
            )

    def test_wait_for_report_completion_rejects_canceled_status(self) -> None:
        """Fail when Qualys reports that generation was canceled."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <data><Report><status>CANCELED</status></Report></data>
                </ServiceResponse>
                """
            ]
        )

        with self.assertRaisesRegex(RuntimeError, "terminal status CANCELED"):
            detail_reports.wait_for_report_completion(
                client=QualysClient(connection),
                report_id="123",
                sleep_function=lambda seconds: None,
            )

    def test_wait_for_report_completion_continues_after_transient_failure(self) -> None:
        """Continue polling after one status request exhausts its retries."""
        connection = FakeConnection(
            [
                requests.ReadTimeout("timed out"),
                """
                <ServiceResponse>
                    <data><Report><status>COMPLETE</status></Report></data>
                </ServiceResponse>
                """,
            ]
        )
        sleep_calls: list[int] = []
        client = QualysClient(
            connection,
            retry_policy=QualysRetryPolicy(max_attempts=1),
        )

        with self.assertLogs(detail_reports.LOGGER, level="WARNING") as captured:
            detail_reports.wait_for_report_completion(
                client=client,
                report_id="123",
                sleep_seconds=1,
                sleep_function=sleep_calls.append,
            )

        self.assertEqual(sleep_calls, [1])
        self.assertIn("Polling will continue", " ".join(captured.output))

    def test_wait_for_report_completion_has_bounded_timeout(self) -> None:
        """Honor an explicitly configured positive polling timeout."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <data><Report><status>RUNNING</status></Report></data>
                </ServiceResponse>
                """
            ]
        )
        monotonic_values = iter([0.0, 10.0])

        with self.assertRaisesRegex(TimeoutError, "did not complete"):
            detail_reports.wait_for_report_completion(
                client=QualysClient(connection),
                report_id="123",
                timeout_seconds=10,
                sleep_function=lambda seconds: None,
                monotonic_function=lambda: next(monotonic_values),
            )

    @patch("was_reports.reporting.detail_reports.getenv", return_value="0")
    def test_report_poll_timeout_zero_disables_elapsed_timeout(
        self,
        mock_getenv,
    ) -> None:
        """Treat a zero report polling timeout as unlimited."""
        self.assertIsNone(detail_reports.report_poll_timeout_seconds_from_environment())
        mock_getenv.assert_called_once()

    def test_download_detail_pdf_sets_auth_and_writes_file(self) -> None:
        """Download detail PDF content using Qualys credentials."""
        session = FakeSession()
        credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.pdf"
            result = detail_reports.download_detail_pdf(
                report_id="123",
                output_path=output_path,
                credentials=credentials,
                session_factory=lambda: session,
            )

            self.assertEqual(result, output_path)
            self.assertEqual(output_path.read_bytes(), b"pdf-content")

        self.assertEqual(session.auth, ("user", "secret"))
        self.assertEqual(
            session.urls,
            ["https://qualys.example/qps/rest/3.0/download/was/report/123"],
        )
        self.assertTrue(session.response.raise_for_status_called)

    def test_download_detail_pdf_retries_transient_failure(self) -> None:
        """Retry a transient detail-report download without duplicating reports."""
        response = FakeResponse(b"pdf-content")
        session = RetryingFakeSession(
            [requests.ConnectionError("connection failed"), response]
        )
        credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )
        sleep_calls: list[float] = []

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.pdf"
            detail_reports.download_detail_pdf(
                report_id="123",
                output_path=output_path,
                credentials=credentials,
                session_factory=lambda: session,
                retry_policy=QualysRetryPolicy(max_attempts=2),
                sleep_function=sleep_calls.append,
                random_function=lambda: 0.0,
            )

            self.assertEqual(output_path.read_bytes(), b"pdf-content")

        self.assertEqual(len(session.urls), 2)
        self.assertEqual(sleep_calls, [1.0])

    @patch("was_reports.reporting.detail_reports.post_process_detail_pdf")
    def test_download_and_process_detail_report_runs_full_flow(
        self,
        mock_post_process,
    ) -> None:
        """Download and post-process a completed detail report."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <data><Report><status>COMPLETE</status></Report></data>
                </ServiceResponse>
                """
            ]
        )
        session = FakeSession()
        credentials = QualysCredentials(
            username="user",
            password="secret",
            hostname="qualys.example",
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_path = detail_reports.download_and_process_detail_report(
                client=QualysClient(connection),
                report_id="123",
                filename="CUSTOMER_TAG",
                credentials=credentials,
                output_directory=root / "docs",
                resource_root=root,
                python_executable="python3",
                sleep_function=lambda seconds: None,
                session_factory=lambda: session,
            )

        self.assertEqual(output_path.name, "CUSTOMER_TAGDetails.pdf")
        self.assertEqual(mock_post_process.call_count, 1)


if __name__ == "__main__":
    unittest.main()
