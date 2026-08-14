"""Tests for pe_mailer.email_reports failure-path handling and attachments."""

# Standard Python Libraries
import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")  # nosec B105
os.environ.setdefault("MAILER_ARN", "arn:aws:iam::123456789012:role/fake")

# Third-Party Libraries
import fitz
from pe_mailer import email_reports
from pe_mailer.email_reports import UnableToSendError


def _write_pdf(path):
    """Write a minimal real (openable) PDF at path."""
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()


def _seed_local_report(local_dir, cyhy_id, report_date):
    """Write a report PDF + ASM summary PDF matching report_generator's layout."""
    org_dir = os.path.join(local_dir, cyhy_id)
    os.makedirs(org_dir, exist_ok=True)
    report_path = os.path.join(
        org_dir, f"Posture_and_Exposure_Report-{cyhy_id}-{report_date}.pdf"
    )
    asm_path = os.path.join(
        org_dir, f"Posture-and-Exposure-ASM-Summary_{cyhy_id}_{report_date}.pdf"
    )
    _write_pdf(report_path)
    _write_pdf(asm_path)
    return report_path, asm_path


def _always_succeeds(ses_client, message, counter=0):
    return counter + 1


def _always_fails(ses_client, message, counter=0):
    raise UnableToSendError({"ResponseMetadata": {"HTTPStatusCode": 500}})


class ResolveOrgsUnmatchedNameTests(unittest.TestCase):
    """resolve_orgs warns about requested names that don't match any org."""

    def setUp(self):
        """Stub get_orgs() with a small fixed org list."""
        self.pe_orgs = [
            {"cyhy_db_name": "DHS", "report_on": True},
            {"cyhy_db_name": "DOC", "report_on": True},
        ]

    @patch.object(email_reports, "LOGGER")
    def test_warns_on_unmatched_name(self, mock_logger):
        """A typo'd org name is dropped with a warning, not silently."""
        with patch.object(email_reports, "get_orgs", return_value=self.pe_orgs):
            result = email_reports.resolve_orgs("DHS,DHS_TYPOO")

        self.assertEqual([o["cyhy_db_name"] for o in result], ["DHS"])
        mock_logger.warning.assert_called_once()
        self.assertIn("DHS_TYPOO", mock_logger.warning.call_args[0][1])

    @patch.object(email_reports, "LOGGER")
    def test_no_warning_when_all_match(self, mock_logger):
        """No warning when every requested name resolves."""
        with patch.object(email_reports, "get_orgs", return_value=self.pe_orgs):
            result = email_reports.resolve_orgs("DHS,DOC")

        self.assertEqual(sorted(o["cyhy_db_name"] for o in result), ["DHS", "DOC"])
        mock_logger.warning.assert_not_called()


class SendPeReportsFailurePropagationTests(unittest.TestCase):
    """Tests for send_pe_reports' had_failures return value.

    Confirms it correctly distinguishes failures (missing report/password/
    contacts, failed sends) from GSEC's permanent, by-design skip -- and
    confirms the actual attachment sent is the encrypted copy, not the
    plaintext original.
    """

    def setUp(self):
        """Seed a local-reports-dir fixture for the DHS org."""
        self.tmp = tempfile.TemporaryDirectory()
        self.local_dir = self.tmp.name
        self.report_date = "2026-07-15"
        _seed_local_report(self.local_dir, "DHS", self.report_date)
        self.password_patch = patch.object(
            email_reports,
            "_load_org_passwords",
            return_value={"DHS": "test-password-123"},
        )
        self.connect_patch = patch.object(email_reports, "connect", return_value=None)
        self.password_patch.start()
        self.connect_patch.start()
        self.addCleanup(self.password_patch.stop)
        self.addCleanup(self.connect_patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def _send(self, orgs, send_message_impl):
        with patch.object(email_reports, "send_message", send_message_impl):
            return email_reports.send_pe_reports(
                ses_client=object(),
                s3_client=object(),
                s3_bucket=None,
                report_date=self.report_date,
                orgs=orgs,
                to=["you@example.com"],
                local_reports_dir=self.local_dir,
            )

    def test_successful_send_has_no_failures(self):
        """A clean send reports had_failures=False."""
        stats, had_failures = self._send([{"cyhy_db_name": "DHS"}], _always_succeeds)
        self.assertFalse(had_failures)
        self.assertIn("1 (100.00%)", stats)

    def test_ses_failure_counts_as_not_mailed(self):
        """A failed send is reflected in both reports_not_mailed and had_failures."""
        stats, had_failures = self._send([{"cyhy_db_name": "DHS"}], _always_fails)
        self.assertTrue(had_failures)
        self.assertIn("0 (0.00%)", stats)

    def test_gsec_skip_is_not_a_failure(self):
        """The permanent GSEC skip must not trip had_failures."""
        stats, had_failures = self._send([{"cyhy_db_name": "GSEC"}], _always_succeeds)
        self.assertFalse(had_failures)

    def test_missing_password_is_a_failure(self):
        """An org with no encryption password on file counts as a failure."""
        with patch.object(email_reports, "_load_org_passwords", return_value={}):
            stats, had_failures = self._send(
                [{"cyhy_db_name": "DHS"}], _always_succeeds
            )
        self.assertTrue(had_failures)

    def test_missing_report_pdf_is_a_failure(self):
        """An org with no report PDF on disk counts as a failure."""
        stats, had_failures = self._send([{"cyhy_db_name": "DOC"}], _always_succeeds)
        self.assertTrue(had_failures)

    def test_attachment_sent_is_the_encrypted_copy(self):
        """The attached PDF is the encrypted copy, not the plaintext original.

        Confirms it against the actual outgoing message, not just the
        filename passed to PEMessage -- decrypts it with the org's real
        password and checks it needs one at all.
        """
        sent_messages = []

        def _capture(ses_client, message, counter=0):
            sent_messages.append(message)
            return counter + 1

        stats, had_failures = self._send([{"cyhy_db_name": "DHS"}], _capture)
        self.assertFalse(had_failures)
        self.assertEqual(len(sent_messages), 1)

        payloads = [
            part
            for part in sent_messages[0].walk()
            if part.get_content_type() == "application/pdf"
        ]
        self.assertTrue(payloads, "no PDF attachment found on the sent message")

        for part in payloads:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(part.get_payload(decode=True))
                attached_path = f.name
            try:
                doc = fitz.open(attached_path)
                try:
                    self.assertTrue(
                        doc.needs_pass,
                        f"attachment {part.get_filename()!r} is not password-protected",
                    )
                    self.assertTrue(doc.authenticate("test-password-123"))
                finally:
                    doc.close()
            finally:
                os.unlink(attached_path)


if __name__ == "__main__":
    unittest.main()
