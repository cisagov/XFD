"""Tests for guarded interrupted production batch recovery."""

# Standard Python Libraries
from argparse import Namespace
from contextlib import ExitStack
from datetime import datetime, timezone
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
    values = {
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


def write_workload(output_root: Path, batch_id: str) -> None:
    """Write one immutable coordinator workload for command tests."""
    workload_directory = output_root / "batches" / batch_id
    workload_directory.mkdir(parents=True)
    (workload_directory / "workload.json").write_text(
        json.dumps({"run_id": batch_id, "candidate_ids": [101]}),
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
        )
        complete_report_run.assert_called_once()
        send_report_email.assert_called_once()
        record_generation_failure.assert_not_called()
        record_report_attempt.assert_called_once()
        touch_report_run.assert_called()

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
        )

        self.assertFalse(recovered)
        send_report_email.assert_not_called()
        record_generation_failure.assert_not_called()
        record_report_attempt.assert_called_once()
        touch_report_run.assert_called()


if __name__ == "__main__":
    unittest.main()
