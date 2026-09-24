"""Check capacity instrumentation at report delivery and batch boundaries."""

from contextlib import ExitStack
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from was_mailer import email_reports
from was_reports.commands import batch_runner
from was_reports.data.daily_report_tracker import TrackerReportCandidate
from was_reports.reporting import analyst_summaries


class CapacityHookTests(unittest.TestCase):
    """Keep delivery timing distinct from artifact generation."""

    def test_ready_retry_records_delivery_duration_and_persisted_success(self) -> None:
        """Count successful persisted delivery, with failures retained separately."""
        for failure in (None, RuntimeError("receipt persistence failed")):
            with self.subTest(failure=bool(failure)), ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        email_reports,
                        "list_report_runs_ready_for_email_from_db",
                        return_value=[
                            SimpleNamespace(
                                id=8, source_tracker_id=4, artifact_type="pdf"
                            )
                        ],
                    )
                )
                stack.enter_context(
                    patch.object(
                        email_reports,
                        "send_report_run_email",
                        return_value="receipt",
                        side_effect=failure,
                    )
                )
                stack.enter_context(
                    patch.object(email_reports, "monotonic", side_effect=[10, 14])
                )
                record = stack.enter_context(
                    patch.object(analyst_summaries, "record_report_attempt")
                )
                count = email_reports.send_ready_report_emails(
                    "reports@example.gov",
                    analyst_batch_id="batch",
                )
                self.assertEqual(count, 0 if failure else 1)
                self.assertEqual(
                    record.call_args.kwargs["delivery_duration_seconds"], 4
                )
                self.assertEqual(record.call_args.kwargs["duration_seconds"], 0)
                self.assertEqual(record.call_args.kwargs["sent"], not bool(failure))
                self.assertEqual(record.call_args.kwargs["artifact_type"], "pdf")

    def test_notification_timing_and_direct_batch_finish(self) -> None:
        """Separate notification delivery time and leave worker completion to coordinator."""
        candidate = TrackerReportCandidate(
            id=4,
            tag="TAG",
            data_pull_date=date(2026, 9, 1),
            schedule_id=1,
            assignee_id=2,
            template="All NWS",
        )
        for worker_index in (None, 0):
            with self.subTest(worker_index=worker_index), ExitStack() as stack:
                stack.enter_context(
                    patch.object(
                        batch_runner,
                        "list_ready_report_candidates_from_db",
                        return_value=[candidate],
                    )
                )
                stack.enter_context(
                    patch.object(
                        batch_runner,
                        "create_report_run_for_tracker",
                        return_value=SimpleNamespace(id=8, generation_token="lease"),
                    )
                )
                stack.enter_context(
                    patch.object(batch_runner, "complete_report_run_by_id")
                )
                stack.enter_context(
                    patch.object(
                        batch_runner, "send_report_run_email", return_value="receipt"
                    )
                )
                stack.enter_context(
                    patch.object(batch_runner, "monotonic", side_effect=[1, 3, 10, 15])
                )
                start = stack.enter_context(
                    patch.object(analyst_summaries, "start_batch")
                )
                finish = stack.enter_context(
                    patch.object(analyst_summaries, "finish_batch")
                )
                record = stack.enter_context(
                    patch.object(analyst_summaries, "record_report_attempt")
                )
                batch_runner.run_recent_scan_reports(
                    resource_root="/resources",
                    python_executable="python",
                    analyst_batch_id="batch",
                    send_email=True,
                    retry_ready_emails=False,
                    source_email="reports@example.gov",
                    worker_count=2 if worker_index == 0 else None,
                    worker_index=worker_index,
                )
                self.assertEqual(record.call_args.kwargs["duration_seconds"], 2)
                self.assertEqual(
                    record.call_args.kwargs["delivery_duration_seconds"], 5
                )
                self.assertEqual(
                    record.call_args.kwargs["artifact_type"], "notification"
                )
                self.assertTrue(record.call_args.kwargs["generated"])
                self.assertTrue(record.call_args.kwargs["sent"])
                self.assertEqual(finish.call_count, 1 if worker_index is None else 0)
                start.assert_called_once_with(
                    "batch", worker_count=2 if worker_index == 0 else None
                )

    def test_failed_direct_batch_finishes_before_final_summary(self) -> None:
        """Freeze a failed direct run even when retry enumeration fails."""
        events = []
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "list_ready_report_candidates_from_db",
                    return_value=[],
                )
            )
            stack.enter_context(patch.object(analyst_summaries, "start_batch"))
            stack.enter_context(patch.object(analyst_summaries, "send_tracker_summary"))
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "send_ready_report_emails",
                    side_effect=RuntimeError("retry failed"),
                )
            )
            finish = stack.enter_context(
                patch.object(
                    analyst_summaries,
                    "finish_batch",
                    side_effect=lambda *args, **kwargs: events.append("finish"),
                )
            )
            stack.enter_context(
                patch.object(
                    analyst_summaries,
                    "send_batch_summary",
                    side_effect=lambda *args, **kwargs: events.append("summary"),
                )
            )
            with self.assertRaises(RuntimeError):
                batch_runner.run_recent_scan_reports(
                    resource_root="/resources",
                    python_executable="python",
                    analyst_batch_id="batch",
                    send_email=True,
                    send_assignee_digests=True,
                    source_email="reports@example.gov",
                )
            finish.assert_called_once_with("batch", outcome="failed")
            self.assertEqual(events, ["finish", "summary"])

    def test_dry_run_creates_no_capacity_records(self) -> None:
        """Do not register or finish capacity runs during dry-run delivery."""
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    batch_runner,
                    "list_ready_report_candidates_from_db",
                    return_value=[],
                )
            )
            start = stack.enter_context(patch.object(analyst_summaries, "start_batch"))
            finish = stack.enter_context(
                patch.object(analyst_summaries, "finish_batch")
            )
            batch_runner.run_recent_scan_reports(
                resource_root="/resources",
                python_executable="python",
                analyst_batch_id="batch",
                dry_run_email=True,
            )
            start.assert_not_called()
            finish.assert_not_called()
