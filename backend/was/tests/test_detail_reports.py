"""Tests for Qualys detail-report download helpers."""

# Standard Python Libraries
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient
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
        return self.responses.pop(0)


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


class DetailReportsTests(unittest.TestCase):
    """Validate detail-report helper behavior."""

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

        detail_reports.wait_for_report_completion(
            client=QualysClient(connection),
            report_id="123",
            sleep_seconds=1,
            sleep_function=sleep_calls.append,
        )

        self.assertEqual(sleep_calls, [1])
        self.assertEqual(len(connection.calls), 2)

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
