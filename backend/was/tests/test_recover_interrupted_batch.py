"""Tests for guarded interrupted production batch recovery."""

# Standard Python Libraries
from argparse import Namespace
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
from requests import Response
from requests.exceptions import HTTPError

# First-Party Libraries
from was_reports.commands import recover_interrupted_batch as recovery
from was_reports.data.report_runs import InterruptedReportRun, ReportRun


def test_recipient_scope(address: str) -> str:
    """Return the stored recipient fingerprint for one test address."""
    digest = hashlib.sha256(address.lower().encode("utf-8")).hexdigest()
    return "test-sha256:{}".format(digest)


def interrupted_report_run() -> InterruptedReportRun:
    """Build a representative interrupted customer report run."""
    return InterruptedReportRun(
        id=5093,
        stakeholder_tag="TAG",
        source_tracker_id=101,
        email_status="pending",
        updated_at=datetime(2026, 10, 19, tzinfo=timezone.utc),
        detail_report_id="qualys-detail",
        detail_report_status="RUNNING",
        xml_report_id=None,
        xml_report_status=None,
        tag_id=42,
        organization_name="Customer",
        template="template",
    )


def recovery_arguments(**overrides) -> Namespace:
    """Build command arguments for a focused recovery unit test."""
    values: dict[str, object] = {
        "apply": False,
        "confirm": None,
        "replacement_confirm": None,
        "replace_missing_report_runs": frozenset(),
        "send_email": False,
        "send_final_summary": False,
        "resource_root": "/resources",
        "output_root": Path("/output"),
    }
    values.update(overrides)
    return Namespace(**values)


def write_workload(
    output_root: Path,
    batch_id: str,
    *,
    delivery_mode: str = "customer",
    recipient_scope: str = "stored-customer",
) -> None:
    """Write one immutable coordinator workload for command tests."""
    workload_directory = output_root / "batches" / batch_id
    workload_directory.mkdir(parents=True)
    (workload_directory / "workload.json").write_text(
        json.dumps(
            {
                "run_id": batch_id,
                "candidate_ids": [101],
                "delivery_mode": delivery_mode,
                "recipient_scope": recipient_scope,
            }
        ),
        encoding="utf-8",
    )


class InterruptedBatchRecoveryTests(unittest.TestCase):
    """Validate preview gates and explicitly approved recovery behavior."""

    def test_load_workload_rejects_wrong_batch(self) -> None:
        """Bind recovery to the coordinator's immutable workload snapshot."""
        with TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            workload_directory = output_root / "batches" / "expected"
            workload_directory.mkdir(parents=True)
            (workload_directory / "workload.json").write_text(
                json.dumps({"run_id": "other", "candidate_ids": [101]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "does not match"):
                recovery.load_workload(output_root, "expected")

    def test_legacy_workload_is_preview_only(self) -> None:
        """Never guess customer recipients for an older workload snapshot."""
        workload = recovery.RecoveryWorkload((101,), None, None)

        self.assertIsNone(recovery.recovery_recipients(workload, None, applying=False))
        with self.assertRaisesRegex(ValueError, "legacy workload"):
            recovery.recovery_recipients(workload, None, applying=True)

    @patch.object(
        recovery,
        "approved_analyst_recipients",
        return_value=["analyst@example.gov"],
    )
    def test_test_workload_requires_matching_approved_recipients(
        self, approved_recipients
    ) -> None:
        """Bind applied test recovery to the original recipient scope."""
        matching_scope = test_recipient_scope("analyst@example.gov")
        workload = recovery.RecoveryWorkload((101,), "test", matching_scope)

        with self.assertRaisesRegex(ValueError, "requires the original"):
            recovery.recovery_recipients(workload, None, applying=True)
        self.assertEqual(
            recovery.recovery_recipients(
                workload,
                "analyst@example.gov",
                applying=True,
            ),
            "analyst@example.gov",
        )
        mismatched = recovery.RecoveryWorkload(
            (101,),
            "test",
            test_recipient_scope("other@example.gov"),
        )
        with self.assertRaisesRegex(ValueError, "do not match"):
            recovery.recovery_recipients(
                mismatched,
                "analyst@example.gov",
                applying=True,
            )
        self.assertEqual(approved_recipients.call_count, 2)

    def test_customer_workload_rejects_recipient_override(self) -> None:
        """Keep a customer batch on its recorded customer delivery path."""
        workload = recovery.RecoveryWorkload((101,), "customer", "stored-customer")

        with self.assertRaisesRegex(ValueError, "customer workload"):
            recovery.recovery_recipients(
                workload,
                "analyst@example.gov",
                applying=True,
            )

    def test_only_qualys_404_is_definitively_missing(self) -> None:
        """Require an explicit Qualys not-found response before replacement."""
        missing_response = Response()
        missing_response.status_code = 404
        server_response = Response()
        server_response.status_code = 500

        self.assertTrue(recovery._missing_report(HTTPError(response=missing_response)))
        self.assertFalse(recovery._missing_report(HTTPError(response=server_response)))
        self.assertFalse(recovery._missing_report(TimeoutError("timeout")))

    def test_apply_requires_per_run_missing_report_approval(self) -> None:
        """Do not replace a missing external report under batch-wide approval."""
        inspection = recovery.QualysInspection(
            report_run=interrupted_report_run(),
            detail_status=None,
            xml_status=None,
            missing_labels=("detail",),
        )
        arguments = recovery_arguments(
            apply=True,
            confirm=recovery.RECOVERY_CONFIRMATION,
            send_email=True,
            send_final_summary=True,
        )

        with self.assertRaisesRegex(ValueError, "per-run replacement approval"):
            recovery.validate_application_request(arguments, [inspection])

    def test_main_preview_does_not_recover_or_finalize(self) -> None:
        """Keep the default command path read-only after all live inspection."""
        batch_id = "0d039ae2-f152-481f-9f15-e89943cfc63b"
        inspection = recovery.QualysInspection(
            report_run=interrupted_report_run(),
            detail_status="FINISHED",
            xml_status=None,
            missing_labels=(),
        )
        connection = MagicMock()
        with TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            write_workload(output_root, batch_id)
            with ExitStack() as context_stack:
                context_stack.enter_context(patch.object(recovery, "configure_logging"))
                acquire_lock = context_stack.enter_context(
                    patch.object(
                        recovery,
                        "acquire_coordinator_lock",
                        return_value=connection,
                    )
                )
                list_runs = context_stack.enter_context(
                    patch.object(
                        recovery,
                        "list_interrupted_report_runs",
                        return_value=[interrupted_report_run()],
                    )
                )
                context_stack.enter_context(
                    patch.object(
                        recovery,
                        "inspect_qualys_reports",
                        return_value=[inspection],
                    )
                )
                context_stack.enter_context(patch.object(recovery, "display_preview"))
                recover_run = context_stack.enter_context(
                    patch.object(recovery, "recover_run")
                )
                active_operation_count = context_stack.enter_context(
                    patch.object(recovery, "active_operation_count")
                )
                finish_batch = context_stack.enter_context(
                    patch.object(recovery.analyst_summaries, "finish_batch")
                )

                result = recovery.main(
                    ["--batch-id", batch_id, "--output-root", str(output_root)]
                )

        self.assertEqual(result, 0)
        acquire_lock.assert_called_once_with()
        list_runs.assert_called_once()
        recover_run.assert_not_called()
        active_operation_count.assert_not_called()
        finish_batch.assert_not_called()
        connection.close.assert_called_once_with()

    @patch.object(recovery, "touch_report_run_by_id", return_value=True)
    @patch.object(recovery.analyst_summaries, "record_report_attempt")
    @patch.object(recovery, "record_generation_failure")
    @patch.object(recovery, "send_report_run_email")
    @patch.object(recovery, "complete_report_run_by_id")
    @patch.object(recovery, "generate_report_output")
    @patch.object(recovery, "clear_qualys_report_id_by_run_id")
    @patch.object(recovery, "claim_interrupted_report_run")
    def test_recovery_reuses_existing_qualys_identifier(
        self,
        claim_interrupted_report_run,
        clear_qualys_report_id,
        generate_report_output,
        complete_report_run,
        send_report_email,
        record_generation_failure,
        record_report_attempt,
        touch_report_run,
    ) -> None:
        """Resume stored report IDs without clearing or recreating them."""
        claim_interrupted_report_run.return_value = ReportRun(
            id=5093,
            stakeholder_tag="TAG",
            status="running",
            generation_token="new-generation-token",
        )
        generate_report_output.return_value = "s3://bucket/report.pdf"
        send_report_email.return_value = "message-id"
        inspection = recovery.QualysInspection(
            report_run=interrupted_report_run(),
            detail_status="FINISHED",
            xml_status=None,
            missing_labels=(),
        )

        recovered = recovery.recover_run(
            inspection,
            MagicMock(),
            recovery_arguments(),
            "source@example.gov",
            "batch-id",
            "analyst@example.gov",
        )

        self.assertTrue(recovered)
        clear_qualys_report_id.assert_not_called()
        generate_report_output.assert_called_once_with(
            report_run_id=5093,
            stakeholder_tag="TAG",
            resource_root="/resources",
            python_executable=recovery.sys.executable,
            create_missing_password=True,
            output_directory="/output",
            storage_mode=recovery.S3_STORAGE,
            staging_directory="/output/.recovery-staging",
            generation_token="new-generation-token",
            tag_id=42,
            organization_name="Customer",
            password_stakeholder_tag="TAG",
        )
        complete_report_run.assert_called_once()
        send_report_email.assert_called_once_with(
            report_run_id=5093,
            source_email="source@example.gov",
            override_recipients="analyst@example.gov",
            delivery_purpose="customer",
        )
        record_generation_failure.assert_not_called()
        record_report_attempt.assert_called_once()
        touch_report_run.assert_called()

    @patch.object(recovery.analyst_summaries, "record_report_attempt")
    @patch.object(recovery, "record_generation_failure")
    @patch.object(recovery, "send_report_run_email", return_value="message-id")
    @patch.object(recovery, "complete_report_run_by_id")
    @patch.object(recovery, "generate_report_output")
    @patch.object(recovery, "claim_interrupted_report_run")
    def test_all_nws_recovery_remains_notification_only(
        self,
        claim_interrupted_report_run,
        generate_report_output,
        complete_report_run,
        send_report_email,
        record_generation_failure,
        record_report_attempt,
    ) -> None:
        """Recover an all-NWS child without creating an unnecessary PDF."""
        claim_interrupted_report_run.return_value = ReportRun(
            id=5093,
            stakeholder_tag="PARENT",
            status="running",
            generation_token="new-generation-token",
        )
        interrupted_run = replace(
            interrupted_report_run(),
            stakeholder_tag="PARENT",
            report_target_tag="PARENT_CHILD",
            template="All NWS",
        )
        inspection = recovery.QualysInspection(
            report_run=interrupted_run,
            detail_status=None,
            xml_status=None,
            missing_labels=(),
        )

        recovered = recovery.recover_run(
            inspection,
            MagicMock(),
            recovery_arguments(),
            "source@example.gov",
            "batch-id",
            "analyst@example.gov",
        )

        self.assertTrue(recovered)
        generate_report_output.assert_not_called()
        complete_report_run.assert_called_once_with(
            5093,
            artifact_type="notification",
            generation_token="new-generation-token",
        )
        send_report_email.assert_called_once()
        record_generation_failure.assert_not_called()
        self.assertEqual(
            record_report_attempt.call_args.kwargs["artifact_type"],
            "notification",
        )

    @patch.object(recovery, "touch_report_run_by_id", return_value=True)
    @patch.object(recovery.analyst_summaries, "record_report_attempt")
    @patch.object(recovery, "record_generation_failure")
    @patch.object(recovery, "send_report_run_email")
    @patch.object(recovery, "complete_report_run_by_id")
    @patch.object(recovery, "generate_report_output")
    @patch.object(recovery, "claim_interrupted_report_run")
    def test_uncertain_completion_is_not_marked_failed(
        self,
        claim_interrupted_report_run,
        generate_report_output,
        complete_report_run,
        send_report_email,
        record_generation_failure,
        record_report_attempt,
        touch_report_run,
    ) -> None:
        """Preserve an uncertain completion for later database reconciliation."""
        claim_interrupted_report_run.return_value = ReportRun(
            id=5093,
            stakeholder_tag="TAG",
            status="running",
            generation_token="new-generation-token",
        )
        generate_report_output.return_value = "s3://bucket/report.pdf"
        complete_report_run.side_effect = RuntimeError("uncertain commit")
        inspection = recovery.QualysInspection(
            report_run=interrupted_report_run(),
            detail_status="FINISHED",
            xml_status=None,
            missing_labels=(),
        )

        recovered = recovery.recover_run(
            inspection,
            MagicMock(),
            recovery_arguments(),
            "source@example.gov",
            "batch-id",
            None,
        )

        self.assertFalse(recovered)
        send_report_email.assert_not_called()
        record_generation_failure.assert_not_called()
        record_report_attempt.assert_called_once()
        touch_report_run.assert_called()

    def test_main_applied_test_recovery_preserves_recipient_override(self) -> None:
        """Send recovered reports and the final summary only to test recipients."""
        batch_id = "0d039ae2-f152-481f-9f15-e89943cfc63b"
        test_recipients = "analyst@example.gov"
        recipient_scope = test_recipient_scope(test_recipients)
        inspection = recovery.QualysInspection(
            report_run=interrupted_report_run(),
            detail_status="FINISHED",
            xml_status=None,
            missing_labels=(),
        )
        connection = MagicMock()
        with TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            write_workload(
                output_root,
                batch_id,
                delivery_mode="test",
                recipient_scope=recipient_scope,
            )
            with ExitStack() as context_stack:
                context_stack.enter_context(patch.object(recovery, "configure_logging"))
                context_stack.enter_context(
                    patch.object(
                        recovery,
                        "approved_analyst_recipients",
                        return_value=[test_recipients],
                    )
                )
                context_stack.enter_context(
                    patch.object(
                        recovery,
                        "acquire_coordinator_lock",
                        return_value=connection,
                    )
                )
                context_stack.enter_context(
                    patch.object(
                        recovery,
                        "list_interrupted_report_runs",
                        return_value=[interrupted_report_run()],
                    )
                )
                context_stack.enter_context(
                    patch.object(
                        recovery,
                        "inspect_qualys_reports",
                        return_value=[inspection],
                    )
                )
                context_stack.enter_context(patch.object(recovery, "display_preview"))
                recover_run = context_stack.enter_context(
                    patch.object(recovery, "recover_run", return_value=True)
                )
                context_stack.enter_context(
                    patch.object(recovery, "active_operation_count", return_value=0)
                )
                context_stack.enter_context(
                    patch.object(
                        recovery, "require_env", return_value="source@example.gov"
                    )
                )
                context_stack.enter_context(
                    patch.object(recovery.analyst_summaries, "finish_batch")
                )
                send_summary = context_stack.enter_context(
                    patch.object(recovery.analyst_summaries, "send_batch_summary")
                )
                context_stack.enter_context(
                    patch.object(
                        recovery,
                        "configured_recent_scan_days_back",
                        return_value=14,
                    )
                )

                result = recovery.main(
                    [
                        "--batch-id",
                        batch_id,
                        "--output-root",
                        str(output_root),
                        "--test-recipients",
                        test_recipients,
                        "--apply",
                        "--confirm",
                        recovery.RECOVERY_CONFIRMATION,
                        "--send-email",
                        "--send-final-summary",
                    ]
                )

        self.assertEqual(result, 0)
        self.assertEqual(recover_run.call_args.args[-1], test_recipients)
        send_summary.assert_called_once_with(
            batch_id,
            source_email="source@example.gov",
            override_recipients=test_recipients,
            days_back=14,
        )


if __name__ == "__main__":
    unittest.main()
