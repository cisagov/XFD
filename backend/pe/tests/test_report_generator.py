"""Tests for pe-reports report_generator and related report pipeline helpers."""

# Standard Python Libraries
import datetime
import logging
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import uuid

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")  # nosec B105

# Third-Party Libraries
from botocore.exceptions import ClientError
import fitz
from pe_reports import report_generator
from pe_reports._version import __version__
from pe_reports.data import db_query


def _sample_org(*, premium=False, code="DHS", name="Department of Homeland Security"):
    """Build a get_orgs()-style org row (index 8 is premium_report)."""
    row = [None] * 9
    row[0] = str(uuid.uuid4())
    row[1] = name
    row[2] = code
    row[8] = premium
    return tuple(row)


def _init_return_values(tmpdir, org_code, end_date):
    """Minimal init() return tuple for generate_reports mocks."""
    org_dir = os.path.join(tmpdir, org_code)
    os.makedirs(org_dir, exist_ok=True)

    def _touch(name):
        path = os.path.join(org_dir, name)
        with open(path, "wb") as handle:
            handle.write(b"{}")
        return path

    cred_json = _touch("compromised_credentials.json")
    da_json = _touch("domain_alerts.json")
    vuln_json = _touch("vuln_alerts.json")
    mi_json = _touch("mention_incidents.json")
    cred_xlsx = _touch("compromised_credentials.xlsx")
    da_xlsx = _touch("domain_alerts.xlsx")
    vuln_xlsx = _touch("vuln_alerts.xlsx")
    mi_xlsx = _touch("mention_incidents.xlsx")

    return (
        {"filename": ""},
        {"end_date": end_date},
        {},
        cred_json,
        da_json,
        vuln_json,
        mi_json,
        cred_xlsx,
        da_xlsx,
        vuln_xlsx,
        mi_xlsx,
    )


class ShouldUploadToS3Tests(unittest.TestCase):
    """_should_upload_to_s3 gates S3 backup uploads."""

    def test_skips_when_is_local(self):
        """Skip S3 upload when IS_LOCAL is set."""
        with patch.dict(os.environ, {"IS_LOCAL": "true"}, clear=False):
            self.assertFalse(report_generator._should_upload_to_s3("prod-bucket"))

    def test_skips_empty_or_local_reports_bucket(self):
        """Skip S3 upload for empty or local-reports bucket names."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IS_LOCAL", None)
            self.assertFalse(report_generator._should_upload_to_s3(""))
            self.assertFalse(report_generator._should_upload_to_s3("local-reports"))

    def test_allows_production_bucket(self):
        """Allow S3 upload for a real reports bucket name."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IS_LOCAL", None)
            self.assertTrue(
                report_generator._should_upload_to_s3("cisa-crossfeed-staging-reports")
            )


class UploadFileToS3Tests(unittest.TestCase):
    """upload_file_to_s3 builds keys and respects local skip."""

    def setUp(self):
        """Clear IS_LOCAL for upload tests."""
        self._saved_is_local = os.environ.get("IS_LOCAL")
        os.environ.pop("IS_LOCAL", None)

    def tearDown(self):
        """Restore IS_LOCAL after upload tests."""
        if self._saved_is_local is None:
            os.environ.pop("IS_LOCAL", None)
        else:
            os.environ["IS_LOCAL"] = self._saved_is_local

    @patch.object(report_generator, "ACCESSOR_AWS_PROFILE", None)
    @patch.object(report_generator, "boto3")
    def test_uploads_report_pdf_to_date_prefix(self, boto3_mock):
        """Upload report PDF under the report date prefix."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IS_LOCAL", None)
        client = MagicMock()
        boto3_mock.client.return_value = client
        report_path = os.path.join(tempfile.gettempdir(), "out", "DHS", "report.pdf")
        report_generator.upload_file_to_s3(
            report_path, "2026-07-15", "reports-bucket", None
        )
        client.upload_file.assert_called_once_with(
            report_path,
            "reports-bucket",
            "2026-07-15/report.pdf",
        )

    @patch.object(report_generator, "ACCESSOR_AWS_PROFILE", None)
    @patch.object(report_generator, "boto3")
    def test_uploads_excel_under_org_raw_data_prefix(self, boto3_mock):
        """Upload Excel backups under org raw-data prefix."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IS_LOCAL", None)
        client = MagicMock()
        boto3_mock.client.return_value = client
        excel_path = os.path.join(
            tempfile.gettempdir(), "out", "DHS", "compromised_credentials.xlsx"
        )
        report_generator.upload_file_to_s3(
            excel_path,
            "2026-07-15",
            "reports-bucket",
            "DHS",
        )
        client.upload_file.assert_called_once_with(
            excel_path,
            "reports-bucket",
            "2026-07-15/DHS-raw-data/compromised_credentials.xlsx",
        )

    @patch.object(report_generator.LOGGER, "debug")
    @patch.object(report_generator, "boto3")
    def test_skips_upload_when_local(self, boto3_mock, debug_mock):
        """Do not call boto3 when IS_LOCAL is set."""
        with patch.dict(os.environ, {"IS_LOCAL": "true"}, clear=False):
            report_generator.upload_file_to_s3(
                os.path.join(tempfile.gettempdir(), "x.pdf"),
                "2026-07-15",
                "b",
                None,
            )
        boto3_mock.client.assert_not_called()
        debug_mock.assert_called()

    @patch.object(report_generator, "ACCESSOR_AWS_PROFILE", None)
    @patch.object(report_generator.LOGGER, "error")
    @patch.object(report_generator, "boto3")
    def test_logs_client_error_without_raising(self, boto3_mock, error_mock):
        """Log S3 ClientError without raising to the caller."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IS_LOCAL", None)
        client = MagicMock()
        client.upload_file.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}},
            "PutObject",
        )
        boto3_mock.client.return_value = client
        report_generator.upload_file_to_s3(
            os.path.join(tempfile.gettempdir(), "x.pdf"),
            "2026-07-15",
            "reports-bucket",
            None,
        )
        error_mock.assert_called()


class RefreshAssetCountsViewTests(unittest.TestCase):
    """refresh_asset_counts_vw refreshes all report materialized views."""

    @patch.object(db_query.LOGGER, "info")
    @patch.object(db_query, "connect")
    def test_refreshes_breach_materialized_views(self, connect_mock, info_mock):
        """Refresh all breach-comp materialized views used by reports."""
        cursor = MagicMock()
        connection = MagicMock()
        connection.cursor.return_value = cursor
        connect_mock.return_value = connection

        db_query.refresh_asset_counts_vw()

        self.assertEqual(connect_mock.call_count, 3)
        self.assertEqual(cursor.execute.call_count, 3)
        for view_name in (
            "mat_vw_breachcomp",
            "mat_vw_breachcomp_breachdetails",
            "mat_vw_breachcomp_credsbydate",
        ):
            info_mock.assert_any_call("Refreshing %s", view_name)
        self.assertEqual(connection.commit.call_count, 3)


class EmbedTests(unittest.TestCase):
    """embed attaches JSON/XLSX payloads into the report PDF."""

    def setUp(self):
        """Create a minimal multi-page PDF and attachment files."""
        self.tmp = tempfile.TemporaryDirectory()
        self.org_code = "DHS"
        self.datestring = "2026-07-15"
        self.org_dir = os.path.join(self.tmp.name, self.org_code)
        os.makedirs(self.org_dir)

        self.source_pdf = os.path.join(
            self.org_dir,
            f"Posture_and_Exposure_Report-{self.org_code}-{self.datestring}.pdf",
        )
        doc = fitz.open()
        for _ in range(6):
            doc.new_page()
        doc.save(self.source_pdf)
        doc.close()

        self.paths = {}
        for name in (
            "compromised_credentials.json",
            "domain_alerts.json",
            "vuln_alerts.json",
            "compromised_credentials.xlsx",
            "domain_alerts.xlsx",
            "vuln_alerts.xlsx",
        ):
            path = os.path.join(self.org_dir, name)
            with open(path, "wb") as handle:
                handle.write(b"data")
            self.paths[name] = path

    def tearDown(self):
        """Remove temporary embed test files."""
        self.tmp.cleanup()

    def test_embed_writes_output_pdf(self):
        """Embed JSON and Excel attachments into the report PDF."""
        filesize, too_large, output = report_generator.embed(
            self.tmp.name,
            self.org_code,
            self.datestring,
            self.source_pdf,
            self.paths["compromised_credentials.json"],
            self.paths["domain_alerts.json"],
            self.paths["vuln_alerts.json"],
            None,
            self.paths["compromised_credentials.xlsx"],
            self.paths["domain_alerts.xlsx"],
            self.paths["vuln_alerts.xlsx"],
            None,
        )
        self.assertTrue(os.path.isfile(output))
        self.assertGreater(filesize, 0)
        self.assertFalse(too_large)
        self.assertEqual(output, self.source_pdf)
        embedded = fitz.open(output)
        annots = list(embedded[4].annots() or [])
        embedded.close()
        self.assertEqual(len(annots), 6)


class GenerateReportsTests(unittest.TestCase):
    """generate_reports orchestrates refresh, PDF build, embed, and upload."""

    def setUp(self):
        """Create a temporary output directory for generate_reports tests."""
        self.tmp = tempfile.TemporaryDirectory()
        self.end_date = datetime.date(2026, 7, 15)

    def tearDown(self):
        """Remove temporary generate_reports test files."""
        self.tmp.cleanup()

    @patch.object(report_generator, "connect")
    def test_returns_error_when_db_unavailable(self, connect_mock):
        """Return error code when the database connection fails."""
        connect_mock.return_value = None
        result = report_generator.generate_reports("DHS", "2026-07-15", self.tmp.name)
        self.assertEqual(result, 1)

    @patch.object(report_generator, "connect")
    def test_returns_error_when_no_orgs_match(self, connect_mock):
        """Return error code when requested orgs are not in the database."""
        connect_mock.return_value = MagicMock()
        with patch.object(report_generator, "get_specific_orgs", return_value=[]):
            result = report_generator.generate_reports(
                "DHS", "2026-07-15", self.tmp.name
            )
        self.assertEqual(result, 1)

    @patch.object(report_generator, "upload_file_to_s3")
    @patch.object(report_generator, "embed")
    @patch.object(report_generator, "report_gen")
    @patch.object(report_generator, "create_summary")
    @patch.object(report_generator, "init")
    @patch.object(report_generator, "refresh_asset_counts_vw")
    @patch.object(report_generator, "get_specific_orgs")
    @patch.object(report_generator, "connect")
    def test_core_report_path_refreshes_views_and_uploads(
        self,
        connect_mock,
        get_specific_orgs_mock,
        refresh_mock,
        init_mock,
        create_summary_mock,
        report_gen_mock,
        embed_mock,
        upload_mock,
    ):
        """Run report path with view refresh, embed, and S3 uploads."""
        connect_mock.return_value = MagicMock()
        get_specific_orgs_mock.return_value = [_sample_org(premium=False)]
        init_mock.return_value = _init_return_values(
            self.tmp.name, "DHS", self.end_date
        )
        create_summary_mock.return_value = os.path.join(self.tmp.name, "asm.xlsx")
        embed_mock.return_value = (1000, False, os.path.join(self.tmp.name, "out.pdf"))

        report_generator.generate_reports("DHS", "2026-07-15", self.tmp.name)

        refresh_mock.assert_called_once()
        report_gen_mock.assert_called_once()
        embed_mock.assert_called_once()
        self.assertGreaterEqual(upload_mock.call_count, 5)

    @patch.object(report_generator, "upload_file_to_s3")
    @patch.object(report_generator, "embed")
    @patch.object(report_generator, "report_gen")
    @patch.object(report_generator, "create_summary")
    @patch.object(report_generator, "init")
    @patch.object(report_generator, "refresh_asset_counts_vw")
    @patch.object(report_generator, "get_specific_orgs")
    @patch.object(report_generator, "connect")
    def test_premium_report_uses_flare_generator(
        self,
        connect_mock,
        get_specific_orgs_mock,
        refresh_mock,
        init_mock,
        create_summary_mock,
        report_gen_mock,
        embed_mock,
        upload_mock,
    ):
        """Use report_gen for all orgs."""
        connect_mock.return_value = MagicMock()
        get_specific_orgs_mock.return_value = [_sample_org(premium=True)]
        init_mock.return_value = _init_return_values(
            self.tmp.name, "DHS", self.end_date
        )
        create_summary_mock.return_value = os.path.join(self.tmp.name, "asm.xlsx")
        embed_mock.return_value = (1000, False, os.path.join(self.tmp.name, "out.pdf"))

        report_generator.generate_reports("DHS", "2026-07-15", self.tmp.name)

        report_gen_mock.assert_called_once()
        refresh_mock.assert_called_once()

    @patch.object(report_generator, "upload_file_to_s3")
    @patch.object(report_generator, "embed")
    @patch.object(report_generator, "report_gen")
    @patch.object(report_generator, "create_summary")
    @patch.object(report_generator, "init")
    @patch.object(report_generator, "refresh_asset_counts_vw")
    @patch.object(report_generator, "get_demo_orgs")
    @patch.object(report_generator, "connect")
    def test_demo_shortcut_uses_demo_orgs(
        self,
        connect_mock,
        get_demo_orgs_mock,
        refresh_mock,
        init_mock,
        create_summary_mock,
        report_gen_mock,
        embed_mock,
        upload_mock,
    ):
        """Resolve demo orgs when generate_reports receives the demo shortcut."""
        connect_mock.return_value = MagicMock()
        get_demo_orgs_mock.return_value = [_sample_org(code="DEMO_ORG")]
        init_mock.return_value = _init_return_values(
            self.tmp.name, "DEMO_ORG", self.end_date
        )
        create_summary_mock.return_value = os.path.join(self.tmp.name, "asm.xlsx")
        embed_mock.return_value = (1000, False, os.path.join(self.tmp.name, "out.pdf"))

        report_generator.generate_reports("demo", "2026-07-15", self.tmp.name)

        get_demo_orgs_mock.assert_called_once()
        refresh_mock.assert_called_once()


class ReportGeneratorMainTests(unittest.TestCase):
    """CLI entrypoint validation and wiring."""

    def test_version_flag(self):
        """Exit when --version is passed on the command line."""
        with self.assertRaises(SystemExit):
            with patch.object(sys, "argv", ["pe-reports", "--version"]):
                report_generator.main()

    @patch.object(report_generator, "generate_reports")
    def test_main_passes_cli_args_to_generate_reports(self, generate_mock):
        """Forward CLI org, soc_med, and logging flags to generate_reports."""
        out_dir = tempfile.mkdtemp()
        try:
            argv = [
                "pe-reports",
                "2026-07-15",
                out_dir,
                "--orgs=DHS",
                "--soc_med_included",
                "--log-level=warning",
            ]
            with patch.object(sys, "argv", argv):
                report_generator.main()
            generate_mock.assert_called_once_with(
                "DHS",
                "2026-07-15",
                out_dir,
                True,
            )
        finally:
            os.rmdir(out_dir)

    def test_invalid_log_level_exits_with_error(self):
        """Exit with error when an invalid log level is provided."""
        out_dir = tempfile.mkdtemp()
        try:
            argv = ["pe-reports", "2026-07-15", out_dir, "--log-level=emergency"]
            with patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit) as ctx:
                    report_generator.main()
            self.assertEqual(ctx.exception.code, 1)
        finally:
            os.rmdir(out_dir)

    def test_version_string(self):
        """Expose the expected package version string."""
        self.assertEqual(__version__, "1.2.1")


class ConsoleLoggingTests(unittest.TestCase):
    """_configure_console_logging adds stderr handler once."""

    def test_adds_stderr_handler(self):
        """Add a single stderr StreamHandler on first configure call."""
        root = logging.getLogger()
        original_handlers = list(root.handlers)
        try:
            root.handlers = []
            report_generator._configure_console_logging("info")
            stderr_handlers = [
                handler
                for handler in root.handlers
                if isinstance(handler, logging.StreamHandler)
                and handler.stream is sys.stderr
            ]
            self.assertEqual(len(stderr_handlers), 1)
            report_generator._configure_console_logging("debug")
            self.assertEqual(len(stderr_handlers), 1)
        finally:
            root.handlers = original_handlers


class ReportMainModuleTests(unittest.TestCase):
    """pe_reports.__main__ delegates to report_generator.main."""

    def test_main_module_version(self):
        """Run pe_reports as __main__ and honor --version."""
        # Standard Python Libraries
        import runpy

        with self.assertRaises(SystemExit):
            with patch.object(sys, "argv", ["pe-reports", "--version"]):
                runpy.run_module("pe_reports", run_name="__main__")


if __name__ == "__main__":
    unittest.main()
