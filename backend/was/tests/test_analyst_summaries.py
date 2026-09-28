"""Offline regression tests for combined, secret-safe analyst summaries."""

import unittest
from unittest.mock import patch

from was_reports.reporting import analyst_summaries as summaries


def batch_lineage(
    batch_id="batch",
    elapsed=90,
    tracker_duration=10,
    tracker_error=None,
    tracker_rows=4,
    workers=2,
    mode="capacity",
    workload="fixture",
    finished="finished",
    outcome="completed",
    timing_persisted=True,
    parent_batch_id=None,
    root_batch_id=None,
    depth=0,
):
    """Build one persisted batch-lineage row for summary fixtures."""
    resolved_root = root_batch_id or batch_id
    return (
        batch_id,
        elapsed,
        tracker_duration,
        tracker_error,
        tracker_rows,
        workers,
        mode,
        workload,
        finished,
        outcome,
        timing_persisted,
        parent_batch_id,
        resolved_root,
        depth,
    )


class AnalystSummaryTests(unittest.TestCase):
    """Exercise content, persistence and duplicate delivery boundaries."""

    @patch.object(summaries, "list_functional_test_recipient_emails_from_db", return_value=[])
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute")
    def test_no_enabled_analysts_skips_delivery_without_claim(self, execute, client, recipients):
        """Disabling every analyst email must not prevent customer report work."""
        self.assertFalse(summaries._deliver(
            "batch", "final", "from@example.gov", None, "body", [], False
        ))
        execute.assert_not_called()
        client.assert_not_called()

    def test_counts_distinguish_unknown_from_zero(self):
        """Structured NWS and HTML target lists provide exact known counts."""
        counts = summaries.preflight_counts(
            [
                {
                    "template": "Action Required",
                    "nws": "10, 2, 1",
                    "qualys_error": "<ul><li>one</li><li>two</li></ul>",
                },
                {"template": "All NWS", "nws": "unknown", "qualys_error": "opaque"},
                {"template": "Results", "nws": "10"},
            ]
        )
        self.assertEqual(counts["reports"], 3)
        self.assertEqual(counts["nws_webapps"], 3)
        self.assertEqual(counts["nws_unknown"], 1)
        self.assertEqual(counts["error_webapps"], 2)
        self.assertEqual(counts["error_unknown"], 1)
        self.assertEqual(summaries.target_count("one<br>two<br>"), 2)
        self.assertEqual(summaries.target_count("<br>one<br>two<br>"), 2)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows", return_value=[])
    @patch.object(
        summaries,
        "_execute",
        return_value=[(8, None, 12, "production", "fixture", None, "batch")],
    )
    def test_preflight_includes_tracker_duration_and_updated_count(
        self, execute, rows, deliver
    ):
        """Tracker outcomes are visible before any report workers begin."""
        summaries.send_tracker_summary("batch", [], "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertIn("Tracker time | 8.00 seconds", body)
        self.assertIn("Rows updated | 12", body)
        self.assertIn("Error | none", body)
        self.assertIn("Reports | 0", body)
        self.assertIn("Pending manual reports by analyst", body)
        self.assertIn("No pending manual reports | 0", body)
        html_body = deliver.call_args.kwargs["html_body"]
        self.assertIn("<table", html_body)
        self.assertIn('<th scope="col"', html_body)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows")
    @patch.object(
        summaries,
        "_execute",
        return_value=[(1.234, None, 4, "production", "fixture", None, "batch")],
    )
    def test_tracker_summary_groups_pending_manuals_by_assignee(
        self, execute, tracker_rows, deliver
    ):
        """The pre-generation notification includes assigned manual counts."""
        tracker_rows.side_effect = [
            [],
            [
                {"assignee": "Analyst One", "open_manual": True},
                {"assignee": "Analyst One", "open_manual": True},
                {"assignee": "Analyst Two", "open_manual": False},
                {"assignee": None, "open_manual": True},
            ],
        ]
        summaries.send_tracker_summary("batch", [], "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertIn("Tracker time | 1.23 seconds", body)
        self.assertIn("Analyst One | 2", body)
        self.assertIn("Unassigned | 1", body)
        self.assertNotIn("Analyst Two", body)
        self.assertIn(
            "Pending manual reports by analyst",
            deliver.call_args.kwargs["html_body"],
        )

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows", return_value=[])
    @patch.object(summaries, "_batch_lineage")
    @patch.object(
        summaries,
        "_execute",
        return_value=[
            (
                None,
                None,
                None,
                "capacity",
                "continuation of source-batch",
                "source-batch",
                "source-batch",
            )
        ],
    )
    def test_continuation_tracker_summary_uses_source_refresh(
        self, execute, lineage, rows, deliver
    ):
        """Continuation notices identify and reuse the root tracker refresh."""
        lineage.return_value = [
            batch_lineage(
                workload="continuation of source-batch",
                tracker_duration=None,
                tracker_rows=None,
                parent_batch_id="source-batch",
                root_batch_id="source-batch",
            ),
            batch_lineage(
                batch_id="source-batch",
                tracker_duration=42.62,
                tracker_rows=1,
                depth=1,
            ),
        ]
        summaries.send_tracker_summary("batch", [], "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertIn("Tracker refresh | Inherited from source batch", body)
        self.assertIn("Tracker source batch | source-batch", body)
        self.assertIn("Tracker time | 42.62 seconds", body)
        self.assertIn("Rows updated | 1", body)
        self.assertNotIn("Not available", body)

    @patch.object(summaries, "_execute")
    def test_batch_lineage_fallback_is_activity_bounded(self, execute):
        """An unfinished legacy parent uses activity time, not operator downtime."""
        execute.return_value = [batch_lineage(timing_persisted=False)]
        rows = summaries._batch_lineage("batch")
        self.assertFalse(rows[0][10])
        query = execute.call_args.args[0]
        self.assertIn("active_duration_seconds", query)
        self.assertIn("attempts.attempted_at", query)
        self.assertIn("attempts.sent_recorded_at", query)
        self.assertNotIn("COALESCE(finished_at,now())", query)
        self.assertIn("child.parent_batch_id=parent.batch_id", query)
        self.assertNotIn("child.workload_label=", query)

    @patch.object(summaries, "_execute")
    def test_batch_lineage_validates_multi_hop_parent_and_root(self, execute):
        """Explicit identifiers preserve and validate a multi-hop recovery chain."""
        execute.return_value = [
            batch_lineage(
                batch_id="third",
                parent_batch_id="second",
                root_batch_id="first",
            ),
            batch_lineage(
                batch_id="second",
                parent_batch_id="first",
                root_batch_id="first",
                depth=1,
            ),
            batch_lineage(
                batch_id="first",
                root_batch_id="first",
                depth=2,
            ),
        ]
        self.assertEqual(
            [row[0] for row in summaries._batch_lineage("third")],
            ["third", "second", "first"],
        )

    @patch.object(summaries, "_execute")
    def test_batch_lineage_rejects_cycle_or_missing_root(self, execute):
        """A truncated cycle cannot be presented as complete recovery evidence."""
        execute.return_value = [
            batch_lineage(
                batch_id="second",
                parent_batch_id="first",
                root_batch_id="first",
            ),
            batch_lineage(
                batch_id="first",
                parent_batch_id="second",
                root_batch_id="first",
                depth=1,
            ),
        ]
        with self.assertRaisesRegex(ValueError, "lineage is incomplete"):
            summaries._batch_lineage("second")

    @patch("was_mailer.email_reports.send_message", return_value="message-id")
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute", return_value=[("batch",)])
    @patch.object(summaries, "_recipients", return_value=["analyst@example.gov"])
    def test_success_sends_one_csv_message_and_finishes_claim(
        self, recipients, execute, client, send
    ):
        """One SES call contains the combined CSV without legacy secrets."""
        summaries._deliver(
            "batch",
            "final",
            "from@example.gov",
            None,
            "body",
            [{"id": 1, "legacy_password": "secret"}],
            False,
            html_body="<html><body><table></table></body></html>",
        )
        message = send.call_args.args[1]
        self.assertEqual(send.call_count, 1)
        attachments = list(message.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertNotIn(b"secret", attachments[0].get_payload(decode=True))
        self.assertEqual(
            message.get_body(preferencelist=("html",)).get_content_type(),
            "text/html",
        )
        self.assertIn("summary_status='sent'", execute.call_args.args[0])

    def test_csv_deduplicates_and_excludes_passwords(self):
        """Allowlisted exports exclude secrets and neutralize spreadsheet formulas."""
        row = {"id": 1, "tag": "=formula", "legacy_password": "secret"}
        result = summaries.summary_csv([row, row])
        self.assertNotIn("secret", result)
        self.assertNotIn("legacy_password", result)
        self.assertIn("'=formula", result)
        self.assertEqual(len(result.splitlines()), 2)

    @patch.object(summaries, "_execute")
    def test_attempt_merge_preserves_generation_and_sanitizes_errors(self, execute):
        """Delivery-only outcomes cannot erase generation metrics or expose payloads."""
        summaries.record_report_attempt("batch", 1, 0, error=ValueError("secret"))
        query, parameters = execute.call_args.args
        self.assertIn("GREATEST", query)
        self.assertIn("generated OR", query)
        self.assertEqual(parameters[5], "ValueError")
        self.assertNotIn("secret", str(parameters))
        with self.assertRaises(ValueError):
            summaries.record_report_attempt("batch", 1, float("nan"))

    @patch.object(summaries, "approved_analyst_recipients")
    @patch.object(summaries, "list_functional_test_recipient_emails_from_db")
    def test_all_enabled_recipients_use_existing_resolver(self, configured, approved):
        """Use enabled recipients including inactive functional-test accounts."""
        configured.return_value = ["inactive@example.gov", "active@example.gov"]
        approved.return_value = configured.return_value
        self.assertEqual(len(summaries._recipients(None)), 2)
        approved.assert_called_once_with("inactive@example.gov;active@example.gov")
        approved.return_value = [
            "recipient{}@example.gov".format(index) for index in range(51)
        ]
        with self.assertRaises(ValueError):
            summaries._recipients(None)

    @patch("was_mailer.email_reports.send_message")
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute")
    @patch.object(summaries, "_recipients", return_value=["analyst@example.gov"])
    def test_claimed_or_held_phase_never_sends_again(
        self, recipients, execute, client, send
    ):
        """A pending-only database claim controls delivery concurrency."""
        execute.return_value = []
        self.assertFalse(
            summaries._deliver(
                "batch", "final", "from@example.gov", None, "body", [], False
            )
        )
        send.assert_not_called()
        self.assertIn("summary_status='pending'", execute.call_args.args[0])

    @patch("was_mailer.email_reports.send_message", side_effect=RuntimeError("secret"))
    @patch.object(summaries, "create_ses_client")
    @patch.object(summaries, "_execute", return_value=[("batch",)])
    @patch.object(summaries, "_recipients", return_value=["analyst@example.gov"])
    def test_uncertain_send_is_held_without_payload(
        self, recipients, execute, client, send
    ):
        """SES failures never silently retry and never disclose exception messages."""
        with self.assertRaisesRegex(RuntimeError, "held for review: RuntimeError"):
            summaries._deliver(
                "batch", "final", "from@example.gov", None, "body", [], False
            )
        self.assertIn("summary_status='held'", execute.call_args.args[0])
        self.assertEqual(send.call_count, 1)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows")
    @patch.object(summaries, "_execute")
    def test_final_body_lists_only_open_manuals_and_csv_has_all(
        self, execute, rows, deliver
    ):
        """Manual details stay in the CSV while the email reports only totals."""
        execute.side_effect = [
            [batch_lineage()],
            [(12, True, True, None, "pdf", 2)],
        ]
        rows.return_value = [
            {"id": 1, "tag": "ORDINARY", "open_manual": False},
            {
                "id": 2,
                "tag": "MANUAL",
                "assignee": "Analyst",
                "status": "ERROR",
                "report_scan_notes": "MANUAL: Qualys scan processing failed",
                "open_manual": True,
            },
        ]
        summaries.send_batch_summary("batch", "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertNotIn("ORDINARY", body)
        self.assertNotIn("Analyst: tracker 2; tag MANUAL", body)
        self.assertNotIn("MANUAL", body)
        self.assertIn("Open manual work | 1", body)
        self.assertIn("Current batch failures | 0", body)
        self.assertIn("Existing manual backlog | 1", body)
        self.assertIn("Qualys scan error | 1", body)
        self.assertIn("Sent | 1", body)
        self.assertIn("Unsent | 0", body)
        self.assertIn("Analyst | 1", body)
        self.assertIn(
            "Pending manual reports by analyst",
            deliver.call_args.kwargs["html_body"],
        )
        self.assertEqual(len(deliver.call_args.args[5]), 2)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows")
    @patch.object(summaries, "_execute")
    def test_final_body_separates_delivery_reconciliation(
        self, execute, rows, deliver
    ):
        """Missing structured sent dates appear outside open manual work."""
        execute.side_effect = [
            [batch_lineage(mode="production")],
            [],
        ]
        rows.return_value = [
            {
                "id": 3,
                "tag": "LEGACY",
                "assignee": "Analyst",
                "scan_name": "Legacy scan",
                "report_scan_notes": "Sent 09/22/2026",
                "open_manual": False,
                "delivery_reconciliation": True,
            }
        ]
        summaries.send_batch_summary("batch", "from@example.gov", days_back=7)
        body = deliver.call_args.args[4]
        self.assertIn("Open manual work | 0", body)
        self.assertIn("Delivery reconciliation needed | 1", body)
        self.assertNotIn("tracker 3; tag LEGACY", body)
        rows.assert_called_once_with(batch_id="batch", days_back=7)

    def test_manual_summary_uses_exclusive_categories_and_batch_scope(self):
        """Manual totals reconcile without putting row details in the email."""
        rows = [
            {
                "id": 1,
                "open_manual": True,
                "current_batch_attempt": True,
                "report_scan_notes": (
                    "MANUAL: Report generation failed: ExistingReportPasswordError "
                    "occurred during report generation."
                ),
                "status": "ERROR",
            },
            {
                "id": 2,
                "open_manual": True,
                "current_batch_attempt": True,
                "report_scan_notes": (
                    "MANUAL: Report generation failed: QualysReadTimeout occurred "
                    "during report generation."
                ),
            },
            {
                "id": 3,
                "open_manual": True,
                "qualys_error": "SCAN_ERROR",
                "report_scan_notes": "MANUAL: Qualys scan processing failed",
            },
            {"id": 4, "open_manual": True, "stakeholder_manual": True},
            {
                "id": 5,
                "open_manual": True,
                "scan_execution_key": "legacy-import:1:2026-09-01",
            },
            {"id": 6, "open_manual": True, "report_scan_notes": "Review"},
            {"id": 7, "delivery_reconciliation": True},
        ]
        body = "\n".join(summaries.manual_work_summary_lines(rows))
        self.assertIn("Open manual work: 6 total", body)
        self.assertIn("Current batch failures: 2", body)
        self.assertIn("Existing manual backlog: 4", body)
        for label in summaries.MANUAL_REASON_LABELS:
            self.assertIn("- {}: 1".format(label), body)
        self.assertIn("Delivery reconciliation needed: 1", body)
        self.assertNotIn("tracker 1", body.lower())

    @patch.object(summaries, "getenv", return_value='{"total": 2, "completed": 1, "failed": 1, "remaining": 1, "blocked": 1}')
    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows", return_value=[])
    @patch.object(summaries, "_execute")
    def test_continuation_does_not_claim_fresh_throughput(self, execute, rows, deliver, getenv):
        """Previously accepted sends must not inflate a continuation's throughput."""
        execute.side_effect = [
            [
                batch_lineage(
                    batch_id="batch",
                    elapsed=90,
                    tracker_duration=None,
                    tracker_rows=None,
                    workload="continuation of previous",
                    outcome="failed",
                    parent_batch_id="previous",
                    root_batch_id="previous",
                ),
                batch_lineage(
                    batch_id="previous",
                    elapsed=120,
                    tracker_duration=8,
                    tracker_rows=12,
                    timing_persisted=False,
                    depth=1,
                ),
            ],
            [(0, True, True, None, "pdf", None)],
        ]
        summaries.send_batch_summary("batch", "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertIn("CONTINUATION", body)
        self.assertIn("Current continuation elapsed real time | 0:01:30.00", body)
        self.assertIn("Cumulative active elapsed real time | 0:03:30.00", body)
        self.assertIn("Source batch | previous", body)
        self.assertIn("Source tracker time | 8.00 seconds", body)
        self.assertIn("Source tracker rows updated | 12", body)
        self.assertIn(
            "Cumulative timing basis | Estimated from persisted batch activity",
            body,
        )
        self.assertIn("excludes operator downtime", body)
        self.assertIn("Current continuation PDF generation timing", body)
        self.assertIn("Current continuation delivery timing", body)
        self.assertIn("do not describe the full inherited workload", body)
        self.assertIn("Accepted deliveries per hour | Not available", body)
        self.assertIn("they are not new sends", body)
        self.assertIn("total=2; completed=1; failed=1; remaining=1; blocked=1", body)

    @patch.object(summaries, "_execute")
    def test_batch_context_and_completion_are_insert_once(self, execute):
        """Workers cannot reset the coordinator context or completion clock."""
        summaries.start_batch("batch", 4, "capacity", "same-workload")
        self.assertEqual(
            execute.call_args.args[1],
            ("batch", None, "batch", 4, "capacity", "same-workload"),
        )
        self.assertIn("ON CONFLICT (batch_id) DO NOTHING", execute.call_args.args[0])
        summaries.finish_batch("batch", "failed")
        self.assertIn("finished_at IS NULL", execute.call_args.args[0])
        self.assertIn("active_duration_seconds", execute.call_args.args[0])
        self.assertEqual(execute.call_args.args[1], ("failed", None, "batch"))
        summaries.finish_batch("timed-batch", "completed", 12.345)
        self.assertEqual(
            execute.call_args.args[1],
            ("completed", 12.345, "timed-batch"),
        )
        with self.assertRaises(ValueError):
            summaries.start_batch("batch", 0)
        with self.assertRaises(ValueError):
            summaries.start_batch(
                "child",
                parent_batch_id="parent",
                root_batch_id="child",
            )

    @patch.object(summaries, "_execute")
    def test_active_duration_checkpoint_is_monotonic_and_unfinished_only(
        self, execute
    ):
        """Checkpoint SQL cannot reduce timing or overwrite a finished batch."""
        summaries.checkpoint_batch_active_duration("batch", 12.5)
        query, parameters = execute.call_args.args
        self.assertIn("GREATEST", query)
        self.assertIn("finished_at IS NULL", query)
        self.assertEqual(parameters, (12.5, "batch"))

    @patch.object(summaries, "_execute")
    def test_delivery_acceptance_is_persisted_with_first_timestamp(self, execute):
        """Delivery recording persists acceptance and retains its first time."""
        summaries.record_report_attempt("batch", 1, 0, sent=True,
                                        delivery_duration_seconds=2.5, artifact_type="pdf")
        query, parameters = execute.call_args.args
        self.assertIn("sent_recorded_at=COALESCE", query)
        self.assertEqual(parameters[-3:], (2.5, "pdf", True))
        with self.assertRaises(ValueError):
            summaries.record_report_attempt("batch", 1, 0, delivery_duration_seconds=-1)

    @patch.object(summaries, "_deliver", return_value=True)
    @patch.object(summaries, "_tracker_rows", return_value=[])
    @patch.object(summaries, "_execute")
    def test_capacity_metrics_exclude_zero_timings_and_tracker_sent_dates(self, execute, rows, deliver):
        """Stable batch wall time and explicit attempts determine throughput."""
        execute.side_effect = [
            [batch_lineage(elapsed=120, workers=4)],
            [(10, True, True, None, "pdf", 2),
             (30, False, False, "Error", "pdf", None),
             (0.1, False, True, None, "notification", 1)],
        ]
        summaries.send_batch_summary("batch", "from@example.gov")
        body = deliver.call_args.args[4]
        self.assertIn("Elapsed real time | 0:02:00.00", body)
        self.assertIn("Average PDF generation time | 20.00 seconds", body)
        self.assertIn("Median PDF generation time | 20.00 seconds", body)
        self.assertIn("PDF generation p95 nearest rank | 30.00 seconds", body)
        self.assertNotIn("artifact preparation durations", body)
        self.assertIn("Accepted deliveries per minute | 1.00", body)
        self.assertIn("Accepted deliveries per hour | 60.00", body)
        self.assertIn("PDFs generated | 1", body)
        self.assertIn("Notifications generated | 1", body)
        self.assertIn("Sent | 2", body)
        self.assertIn("Unsent | 1", body)
        self.assertNotIn("report_sent_date", execute.call_args_list[1].args[0])
        self.assertIn("WITH RECURSIVE lineage", execute.call_args_list[0].args[0])

    def test_pending_manual_rows_groups_only_analysts_with_open_work(self):
        """Pending-manual tables group assigned work and omit zero-count analysts."""
        rows = [
            {"assignee": "Zack Cogswell", "open_manual": True},
            {"assignee": "zack cogswell", "open_manual": True},
            {"assignee": "Craig Duhn", "open_manual": False},
            {"assignee": None, "open_manual": True},
        ]
        self.assertEqual(
            summaries.pending_manual_rows(rows),
            [("Unassigned", 1), ("Zack Cogswell", 1), ("zack cogswell", 1)],
        )

    def test_time_formatters_use_two_decimals_and_real_time_clock(self):
        """Every duration uses two decimals and elapsed time uses h:mm:ss.ss."""
        self.assertEqual(summaries._format_seconds(8), "8.00 seconds")
        self.assertEqual(summaries._format_elapsed(3723.456), "1:02:03.46")
        self.assertEqual(summaries._format_elapsed(59.999), "0:01:00.00")

    @patch.object(summaries, "send_batch_summary")
    @patch.object(summaries, "finish_batch")
    def test_final_cli_preserves_failed_coordinator_outcome(self, finish, summary):
        """Failed worker phases cannot become completed through final reporting."""
        summaries.main(["--phase", "final", "--batch-id", "batch",
                        "--source-email", "from@example.gov", "--outcome", "failed"])
        finish.assert_called_once_with("batch", "failed")
        summary.assert_called_once()

    @patch.object(summaries, "_execute", return_value=[])
    def test_manual_query_includes_unassigned_and_limits_backlog(self, execute):
        """Final output includes current-batch rows plus seven-day manual backlog."""
        summaries._tracker_rows(batch_id="batch")
        query = execute.call_args.args[0]
        self.assertIn("LEFT JOIN was_stakeholders", query)
        self.assertIn("report_sent_date IS NULL", query)
        self.assertIn("CURRENT_DATE - (%s - 1)", query)
        self.assertIn("was_daily_report_tracker newer", query)
        self.assertIn("newer.tag = tracker.tag", query)
        self.assertIn("current_attempt.batch_id=%s", query)
        self.assertEqual(execute.call_args.args[1], ("batch", "batch", 7))
        self.assertNotIn("legacy_password", query)
        self.assertNotIn("active IS TRUE", query)
        self.assertNotIn("BTRIM(tracker.qualys_error)", query)
        self.assertNotIn("COALESCE(tracker.status", query)

    @patch.object(summaries, "_execute")
    def test_tracker_rows_marks_current_batch_and_stakeholder_manual(
        self, execute
    ):
        """Expose batch scope and manual configuration to summary grouping."""
        values = [None] * len(summaries.TRACKER_EXPORT_FIELDS)
        values[summaries.TRACKER_EXPORT_FIELDS.index("id")] = 42
        values[summaries.TRACKER_EXPORT_FIELDS.index("report_scan_notes")] = "MANUAL"
        execute.return_value = [tuple(values + [True, True])]
        rows = summaries._tracker_rows(batch_id="batch", days_back=None)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["stakeholder_manual"])
        self.assertTrue(rows[0]["current_batch_attempt"])
        self.assertTrue(rows[0]["open_manual"])
        self.assertFalse(rows[0]["delivery_reconciliation"])
        self.assertEqual(execute.call_args.args[1], ("batch", "batch"))

    @patch.object(summaries, "_execute")
    def test_tracker_rows_does_not_mark_error_overlay_as_manual(self, execute):
        """Qualys error data alone is automated, not open manual work."""
        values = [None] * len(summaries.TRACKER_EXPORT_FIELDS)
        values[summaries.TRACKER_EXPORT_FIELDS.index("id")] = 43
        values[summaries.TRACKER_EXPORT_FIELDS.index("status")] = "Error"
        values[summaries.TRACKER_EXPORT_FIELDS.index("qualys_error")] = (
            "https://error.example.gov<br>"
        )
        execute.return_value = [tuple(values + [False, True])]

        rows = summaries._tracker_rows(batch_id="batch", days_back=None)

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["current_batch_attempt"])
        self.assertFalse(rows[0]["open_manual"])
        self.assertFalse(rows[0]["delivery_reconciliation"])


if __name__ == "__main__":
    unittest.main()
