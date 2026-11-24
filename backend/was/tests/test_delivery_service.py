"""Exercise safe, idempotent retry of archived WAS delivery failures."""

# Standard Python Libraries
from contextlib import nullcontext
from pathlib import Path
from typing import Any
from unittest import TestCase
from unittest.mock import Mock, patch

# Third-Party Libraries
from botocore.exceptions import EndpointConnectionError
from s3transfer.exceptions import RetriesExceededError
from was_reports.delivery import service


def retry_context() -> dict:
    """Return one completed report and SES-confirmed failed recipient."""
    return {
        "id": 15,
        "report_run_id": 42,
        "status": "confirmed_failure",
        "recipient_addresses": ["old@example.gov"],
        "archived_report_s3_uri": (
            "s3://reports/was_reports/2026-11-18/TAG/42/report.pdf"
        ),
        "archive_sha256": "a" * 64,
        "output_path": "s3://reports/was_reports/2026-11-18/TAG/42/report.pdf",
        "stakeholder_tag": "TAG",
        "report_generation_status": "completed",
        "delivery_purpose": "customer",
        "artifact_type": "pdf",
        "report_password": None,
        "was_report_poc": None,
        "template": "Results",
        "assignee_name": None,
        "recent_nws": None,
        "nws": None,
        "remove_nws": None,
        "qualys_error": None,
        "scan_started_at": None,
        "next_scheduled": None,
    }


class DeliveryRetryServiceTests(TestCase):
    """Protect the original attempt and suppress duplicate or uncertain sends."""

    def _patch(self, target: object, attribute: str, **options: Any) -> Mock:
        """Start one boundary mock and stop it after the current test."""
        patcher = patch.object(target, attribute, **options)
        mocked_attribute = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked_attribute

    def setUp(self) -> None:
        """Patch external boundaries while retaining real retry orchestration."""
        self.context = retry_context()
        self.recover_stale = self._patch(
            service.delivery_attempts,
            "recover_stale_delivery_attempts",
            return_value=0,
        )
        self.get_context = self._patch(
            service.delivery_attempts, "get_retry_context", return_value=self.context
        )
        self.claim_retry = self._patch(
            service.delivery_attempts,
            "claim_retry",
            return_value={"id": 22, "status": "pending"},
        )
        self.mark_sending = self._patch(service.delivery_attempts, "mark_sending")
        self.mark_accepted = self._patch(service.delivery_attempts, "mark_accepted")
        self.mark_pre_send_failure = self._patch(
            service.delivery_attempts, "mark_pre_send_failure"
        )
        self.mark_uncertain = self._patch(service.delivery_attempts, "mark_uncertain")
        self.materialize = self._patch(
            service,
            "materialize_report",
            return_value=nullcontext(Path("/private/tmp/report.pdf")),
        )
        self.validate = self._patch(service, "validate_archived_pdf")
        report_attachment = Mock()
        report_attachment.get_content_type.return_value = "application/pdf"
        prepared_message = Mock()
        prepared_message.iter_attachments.return_value = [report_attachment]
        self.build_message = self._patch(
            service, "build_report_email", return_value=prepared_message
        )
        self.source = self._patch(
            service, "require_env", return_value="sender@example.gov"
        )
        self.client = self._patch(service, "create_ses_client", return_value=Mock())
        self.send = self._patch(
            service, "send_message", return_value="new-ses-message-id"
        )

    def test_success_uses_existing_report_once_and_records_new_message(self) -> None:
        """Send only the corrected recipient and preserve report-run state."""
        result = service.retry_failure(
            15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
        )

        self.assertEqual(result["status"], "accepted")
        self.materialize.assert_called_once_with(self.context["output_path"])
        self.build_message.assert_called_once()
        self.assertEqual(
            self.build_message.call_args.kwargs["recipients"], ["new@example.gov"]
        )
        self.send.assert_called_once()
        self.validate.assert_called_once_with(
            Path("/private/tmp/report.pdf"),
            None,
            expected_sha256="a" * 64,
        )
        self.mark_accepted.assert_called_once_with(22, "new-ses-message-id")
        self.mark_pre_send_failure.assert_not_called()

    def test_repeat_request_does_not_send_again(self) -> None:
        """Return the persisted result for an already claimed retry."""
        self.claim_retry.return_value = {"id": 22, "status": "accepted"}

        result = service.retry_failure(
            15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
        )

        self.assertEqual(result, {"id": 22, "status": "accepted"})
        self.materialize.assert_not_called()
        self.send.assert_not_called()

    def test_missing_archive_records_pre_send_failure_without_ses(self) -> None:
        """Keep the failed retry separate and avoid an incomplete email."""
        self.materialize.side_effect = FileNotFoundError("private path")

        with self.assertRaises(FileNotFoundError) as failure:
            service.retry_failure(
                15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
            )

        self.assertIn("missing, inaccessible, or invalid", str(failure.exception))
        self.mark_pre_send_failure.assert_called_once_with(22, "archive_unavailable")
        self.send.assert_not_called()

    def test_s3_transport_failure_records_pre_send_failure(self) -> None:
        """Treat botocore connection errors as inaccessible archived reports."""
        self.materialize.side_effect = EndpointConnectionError(
            endpoint_url="https://s3.example.invalid"
        )

        with self.assertRaises(FileNotFoundError):
            service.retry_failure(
                15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
            )

        self.mark_pre_send_failure.assert_called_once_with(22, "archive_unavailable")
        self.send.assert_not_called()

    def test_s3_transfer_retry_exhaustion_records_pre_send_failure(self) -> None:
        """Keep an exhausted S3 download from leaving a pending child."""
        self.materialize.side_effect = RetriesExceededError(
            last_exception=TimeoutError("private transfer")
        )

        with self.assertRaises(FileNotFoundError):
            service.retry_failure(
                15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
            )

        self.mark_pre_send_failure.assert_called_once_with(22, "archive_unavailable")
        self.send.assert_not_called()

    def test_missing_validation_digest_records_pre_send_failure(self) -> None:
        """Do not resend an archive that was never validated at initial send."""
        self.context["archive_sha256"] = None

        with self.assertRaises(FileNotFoundError):
            service.retry_failure(
                15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
            )

        self.mark_pre_send_failure.assert_called_once_with(22, "archive_unavailable")
        self.materialize.assert_not_called()
        self.send.assert_not_called()

    def test_uncertain_ses_result_is_held_without_second_send(self) -> None:
        """Require manual reconciliation after an ambiguous SES response."""
        self.send.side_effect = TimeoutError("private SES response")

        with self.assertRaises(RuntimeError) as failure:
            service.retry_failure(
                15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
            )

        self.assertIn("manual review", str(failure.exception))
        self.mark_uncertain.assert_called_once_with(22, "ses_outcome_uncertain")
        self.send.assert_called_once()

    def test_email_preparation_failure_is_recorded_before_ses(self) -> None:
        """Keep a failed template or configuration step out of uncertain SES state."""
        self.source.side_effect = RuntimeError("missing source")

        with self.assertRaises(RuntimeError) as failure:
            service.retry_failure(
                15, "os-uid:1001", "request-15", "old@example.gov", "new@example.gov"
            )

        self.assertIn("no email was sent", str(failure.exception))
        self.mark_pre_send_failure.assert_called_once_with(
            22, "email_preparation_failed"
        )
        self.mark_sending.assert_not_called()
        self.send.assert_not_called()

    def test_confirmed_failure_can_retry_the_same_address(self) -> None:
        """Resend a confirmed failure when the original mailbox is now clear."""
        result = service.retry_failure(
            15,
            "os-uid:1001",
            "request-15",
            "old@example.gov",
            "old@example.gov",
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(
            self.claim_retry.call_args.args[2:4],
            ("old@example.gov", "old@example.gov"),
        )
        self.assertEqual(
            self.build_message.call_args.kwargs["recipients"],
            ["old@example.gov"],
        )
        self.send.assert_called_once()

    def test_selected_failed_recipient_is_bound_to_the_send(self) -> None:
        """Send only the address explicitly confirmed by the operator."""
        service.retry_failure(
            15,
            "os-uid:1001",
            "request-15",
            "old@example.gov",
            "new@example.gov",
        )

        self.assertEqual(
            self.claim_retry.call_args.args[2:4],
            ("old@example.gov", "new@example.gov"),
        )
        self.assertEqual(
            self.build_message.call_args.kwargs["recipients"],
            ["new@example.gov"],
        )


class DeliveryReviewServiceTests(TestCase):
    """Keep sensitive archive references out of CLI detail output."""

    def test_detail_redacts_s3_reference_and_audits_access(self) -> None:
        """Return scoped history without exposing an unrestricted S3 URI."""
        failure = {
            "id": 15,
            "archived_report_s3_uri": "s3://private/report.pdf",
            "attempt_history": [{"id": 15, "status": "confirmed_failure"}],
        }
        with (
            patch.object(
                service.delivery_attempts, "get_failure", return_value=failure
            ),
            patch.object(service.delivery_attempts, "record_access") as record_access,
            patch.object(service.delivery_attempts, "recover_stale_delivery_attempts"),
        ):
            detail = service.get_failure(15, "os-uid:1001")

        self.assertNotIn("archived_report_s3_uri", detail)
        self.assertEqual(detail["attempt_history"], failure["attempt_history"])
        record_access.assert_called_once_with("os-uid:1001", 15, "detail")
