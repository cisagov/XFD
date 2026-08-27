"""Tests for Qualys report data helpers."""

# Standard Python Libraries
import tempfile
import unittest
from pathlib import Path

# First-Party Libraries
from was_reports import report_data
from was_reports.qualys_client import QualysClient


class FakeConnection:
    """Small Qualys connection fake for report data tests."""

    def __init__(self, responses):
        """Initialize response queue and captured calls."""
        self.responses = list(responses)
        self.calls = []

    def request(self, endpoint, payload=None, http_method=None):
        """Capture a request and return the next response."""
        self.calls.append(
            {
                "endpoint": endpoint,
                "payload": payload,
                "http_method": http_method,
            }
        )
        return self.responses.pop(0)


def write_report_template(directory: str, filename: str) -> Path:
    """Write a minimal report template compatible with the legacy payload."""
    template_path = Path(directory) / filename
    template_path.write_text(
        """<?xml version="1.0" encoding="UTF-8" ?>
<ServiceRequest>
    <data>
        <Report>
            <name></name>
            <format>XML</format>
            <type>WAS_WEBAPP_REPORT</type>
            <config>
                <webAppReport>
                    <target>
                        <tags>
                            <included>
                                <option>ALL</option>
                                <tagList>
                                    <Tag>
                                        <id></id>
                                    </Tag>
                                </tagList>
                            </included>
                        </tags>
                    </target>
                </webAppReport>
            </config>
            <template>
                <id></id>
            </template>
        </Report>
    </data>
</ServiceRequest>
""",
        encoding="utf-8",
    )
    return template_path


def write_detail_template(directory: str, filename: str) -> Path:
    """Write a minimal detail-report template."""
    template_path = Path(directory) / filename
    template_path.write_text(
        """<?xml version="1.0" encoding="UTF-8" ?>
<ServiceRequest>
    <data>
        <Report>
            <name></name>
            <format>XML</format>
            <type>WAS_WEBAPP_REPORT</type>
            <config>
                <webAppReport>
                    <target>
                        <webapps>
                            <WebApp>
                                <id></id>
                            </WebApp>
                        </webapps>
                    </target>
                </webAppReport>
            </config>
            <template>
                <id></id>
            </template>
        </Report>
    </data>
</ServiceRequest>
""",
        encoding="utf-8",
    )
    return template_path


class ReportDataTests(unittest.TestCase):
    """Validate report data service behavior."""

    def test_get_tag_id_uses_legacy_endpoint_and_payload(self) -> None:
        """Look up a Qualys tag ID from a tag name."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <count>1</count>
                    <data><Tag><id>12345</id></Tag></data>
                </ServiceResponse>
                """
            ]
        )
        client = QualysClient(connection)

        tag_id = report_data.get_tag_id(client, "CUSTOMER_TAG")

        self.assertEqual(tag_id, "12345")
        self.assertEqual(connection.calls[0]["endpoint"], "search/am/tag")
        self.assertIn("CUSTOMER_TAG", connection.calls[0]["payload"])

    def test_parse_tag_id_rejects_missing_tag(self) -> None:
        """Raise a lookup error when Qualys returns no matching tag."""
        with self.assertRaises(LookupError):
            report_data.parse_tag_id(
                "<ServiceResponse><count>0</count></ServiceResponse>"
            )

    def test_count_webapps_uses_count_endpoint(self) -> None:
        """Count web applications associated with a tag."""
        connection = FakeConnection(
            ["<ServiceResponse><count>7</count></ServiceResponse>"]
        )
        client = QualysClient(connection)

        count = report_data.count_webapps(client, "CUSTOMER_TAG")

        self.assertEqual(count, 7)
        self.assertEqual(connection.calls[0]["endpoint"], "/count/was/webapp")
        self.assertEqual(connection.calls[0]["http_method"], "POST")
        self.assertIn("tags.name", connection.calls[0]["payload"])

    def test_create_webapp_xml_report_returns_report_id(self) -> None:
        """Create an XML report and return the Qualys report ID."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <responseCode>SUCCESS</responseCode>
                    <data><Report><id>98765</id></Report></data>
                </ServiceResponse>
                """
            ]
        )
        client = QualysClient(connection)

        with tempfile.TemporaryDirectory() as directory:
            template_path = write_report_template(directory, "was_report.xml")
            report_id = report_data.create_webapp_xml_report(
                client=client,
                report_name="CUSTOMER_TAG",
                tag_id="12345",
                template_path=template_path,
            )

        self.assertEqual(report_id, "98765")
        self.assertEqual(connection.calls[0]["endpoint"], "/create/was/report")
        self.assertEqual(connection.calls[0]["http_method"], "post")
        self.assertIn("1994875", connection.calls[0]["payload"])
        self.assertIn("12345", connection.calls[0]["payload"])
        self.assertIn("XML", connection.calls[0]["payload"])

    def test_create_detail_pdf_report_uses_detail_template(self) -> None:
        """Create a detail PDF report using a web application ID."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <responseCode>SUCCESS</responseCode>
                    <data><Report><id>555</id></Report></data>
                </ServiceResponse>
                """
            ]
        )
        client = QualysClient(connection)

        with tempfile.TemporaryDirectory() as directory:
            template_path = write_detail_template(directory, "was_report_details.xml")
            report_id = report_data.create_detail_pdf_report(
                client=client,
                report_name="Web App",
                target_id="2468",
                template_path=template_path,
                from_webapp_id=True,
            )

        self.assertEqual(report_id, "555")
        self.assertIn("2201149", connection.calls[0]["payload"])
        self.assertIn("2468", connection.calls[0]["payload"])
        self.assertIn("PDF", connection.calls[0]["payload"])

    def test_parse_created_report_id_rejects_failure_response(self) -> None:
        """Reject a failed Qualys create-report response."""
        with self.assertRaises(RuntimeError):
            report_data.parse_created_report_id(
                """
                <ServiceResponse>
                    <responseCode>INVALID_REQUEST</responseCode>
                </ServiceResponse>
                """
            )

    def test_get_report_xml_downloads_by_report_id(self) -> None:
        """Download report XML by report ID."""
        connection = FakeConnection(["<WAS_WEBAPP_REPORT />"])
        client = QualysClient(connection)

        response = report_data.get_report_xml(client, "98765")

        self.assertEqual(response, "<WAS_WEBAPP_REPORT />")
        self.assertEqual(
            connection.calls[0]["endpoint"],
            "/download/was/report/98765",
        )
        self.assertEqual(connection.calls[0]["http_method"], "get")

    def test_get_report_status_parses_status(self) -> None:
        """Read a generated report status."""
        connection = FakeConnection(
            [
                """
                <ServiceResponse>
                    <data><Report><status>FINISHED</status></Report></data>
                </ServiceResponse>
                """
            ]
        )
        client = QualysClient(connection)

        status = report_data.get_report_status(client, "98765")

        self.assertEqual(status, "FINISHED")
        self.assertEqual(
            connection.calls[0]["endpoint"],
            "/status/was/report/98765",
        )
        self.assertEqual(connection.calls[0]["http_method"], "get")

    def test_delete_report_returns_success_boolean(self) -> None:
        """Delete a temporary Qualys report."""
        connection = FakeConnection(
            [
                "<ServiceResponse>"
                "<responseCode>SUCCESS</responseCode>"
                "</ServiceResponse>"
            ]
        )
        client = QualysClient(connection)

        deleted = report_data.delete_report(client, "98765")

        self.assertTrue(deleted)
        self.assertEqual(
            connection.calls[0]["endpoint"],
            "/delete/was/report/98765",
        )


if __name__ == "__main__":
    unittest.main()
