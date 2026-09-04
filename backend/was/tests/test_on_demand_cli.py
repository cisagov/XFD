"""Regression coverage for explicit report generation and delivery."""

# Standard Python Libraries
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

# Third-Party Libraries
from was_reports.commands import on_demand_cli
from was_reports.commands.menu_cli import WasOperatorMenu
from was_reports.data import report_runs
from was_reports.data.daily_report_tracker import list_ready_report_candidates


class OnDemandTests(unittest.TestCase):
    """Test stage ordering and avoid accidental or duplicate delivery."""

    def setUp(self) -> None:
        """Isolate orchestration from live database, Qualys, and AWS services."""
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.services = {}
        for name in (
            "require_env",
            "create_on_demand_report_run",
            "generate_report_output",
            "complete_report_run_by_id",
            "fail_report_run_by_id",
            "send_report_run_email",
        ):
            self.services[name] = self.stack.enter_context(
                patch.object(on_demand_cli, name)
            )
        self.services["require_env"].return_value = "approved@example.gov"
        self.services["create_on_demand_report_run"].return_value = SimpleNamespace(
            id=8
        )
        self.services["generate_report_output"].return_value = "s3://test/8/report.pdf"
        self.services["send_report_run_email"].return_value = "test-message"
        self.stack.enter_context(
            patch.object(on_demand_cli, "getenv", return_value="/tmp")
        )

    def arguments(self, email: bool = False) -> list[str]:
        """Build one deterministic CLI invocation."""
        arguments = ["--tag", "CROSSFEED", "--create-missing-password"]
        if email:
            arguments.extend(
                ["--send-email", "--test-recipients", "analyst@example.gov"]
            )
        return arguments

    def test_generation_only_archives_and_records(self) -> None:
        """Create a standalone run and durable S3 reference without email."""
        self.assertEqual(on_demand_cli.main(self.arguments()), 0)
        self.services["create_on_demand_report_run"].assert_called_once_with(
            "CROSSFEED", None
        )
        self.services["complete_report_run_by_id"].assert_called_once_with(
            8, output_path="s3://test/8/report.pdf", artifact_type="pdf"
        )
        self.services["send_report_run_email"].assert_not_called()

    def test_upload_then_complete_then_email(self) -> None:
        """Use the shared S3-generating and mailer paths in the correct order."""
        sequence = Mock()
        for name in (
            "generate_report_output",
            "complete_report_run_by_id",
            "send_report_run_email",
        ):
            sequence.attach_mock(self.services[name], name)
        self.assertEqual(on_demand_cli.main(self.arguments(email=True)), 0)
        self.assertEqual(
            [call[0] for call in sequence.mock_calls],
            [
                "generate_report_output",
                "complete_report_run_by_id",
                "send_report_run_email",
            ],
        )
        self.services["send_report_run_email"].assert_called_once_with(
            report_run_id=8,
            source_email="approved@example.gov",
            override_recipients="analyst@example.gov",
            storage_mode="s3",
            allow_held=True,
        )

    def test_generation_failure_does_not_email(self) -> None:
        """Persist a safe generation failure without invoking the mailer."""
        self.services["generate_report_output"].side_effect = RuntimeError(
            "private detail"
        )
        self.assertEqual(on_demand_cli.main(self.arguments(email=True)), 1)
        self.services["complete_report_run_by_id"].assert_not_called()
        self.services["send_report_run_email"].assert_not_called()
        self.services["fail_report_run_by_id"].assert_called_once_with(
            8, "RuntimeError occurred during report generation."
        )

    def test_completion_failure_retains_artifact_without_email(self) -> None:
        """Do not send or misclassify an uncertain completion write."""
        self.services["complete_report_run_by_id"].side_effect = RuntimeError()
        self.assertEqual(on_demand_cli.main(self.arguments(email=True)), 1)
        self.services["send_report_run_email"].assert_not_called()
        self.services["fail_report_run_by_id"].assert_not_called()

    def test_email_failure_preserves_completed_generation(self) -> None:
        """Leave delivery status to the existing atomic mailer implementation."""
        self.services["send_report_run_email"].side_effect = RuntimeError()
        self.assertEqual(on_demand_cli.main(self.arguments(email=True)), 1)
        self.services["complete_report_run_by_id"].assert_called_once()
        self.services["fail_report_run_by_id"].assert_not_called()

    def test_rejects_ambiguous_delivery_flags(self) -> None:
        """Never implicitly select real stakeholder recipients."""
        for flags in (
            ["--send-email"],
            ["--test-recipients", "analyst@example.gov"],
            ["--tracker-id", "0"],
        ):
            with self.subTest(flags=flags), self.assertRaises(SystemExit):
                on_demand_cli.parse_args(["--tag", "CROSSFEED"] + flags)

    def test_rejects_bad_recipients_before_claim(self) -> None:
        """Empty overrides and header injection must not reach generation."""
        for recipient in ("", "not-an-email", "user@example.gov\nBcc: bad@example.gov"):
            with self.subTest(recipient=recipient):
                arguments = [
                    "--tag",
                    "CROSSFEED",
                    "--send-email",
                    "--test-recipients",
                    recipient,
                ]
                self.assertEqual(on_demand_cli.main(arguments), 1)
        self.services["create_on_demand_report_run"].assert_not_called()

    def test_tracker_selection_is_explicit(self) -> None:
        """Pass the operator-selected tracker row without creating scan data."""
        self.assertEqual(
            on_demand_cli.main(self.arguments() + ["--tracker-id", "9"]), 0
        )
        self.services["create_on_demand_report_run"].assert_called_once_with(
            "CROSSFEED", 9
        )

    def test_menu_confirms_recipient_and_delegates(self) -> None:
        """Expose the same workflow through a thin menu adapter."""
        menu = WasOperatorMenu(
            input_function=Mock(
                side_effect=["CROSSFEED", "y", "analyst@example.gov", "", "y", ""]
            ),
            output_function=Mock(),
        )
        with patch.object(on_demand_cli, "main", return_value=0) as command:
            menu.run_on_demand_report()
        command.assert_called_once_with(self.arguments(email=True))
        self.assertTrue(
            any(
                "analyst@example.gov" in call.args[0]
                for call in menu.input.call_args_list
            )
        )

    def test_menu_cancel_does_not_generate(self) -> None:
        """Require final confirmation even for archive-only requests."""
        menu = WasOperatorMenu(
            input_function=Mock(side_effect=["CROSSFEED", "n", "", "n"]),
            output_function=Mock(),
        )
        with patch.object(on_demand_cli, "main") as command:
            menu.run_on_demand_report()
        command.assert_not_called()


class OnDemandClaimTests(unittest.TestCase):
    """Exercise SQL transactions at the database connection boundary."""

    def claim(self, rows: list, tracker_id: int | None = None):
        """Run a claim with deterministic database response rows."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = rows
        with patch(
            "was_reports.utils.database.connect", return_value=connection
        ), patch("was_reports.utils.database.close"):
            result = report_runs.create_on_demand_report_run("CROSSFEED", tracker_id)
        return result, connection, cursor

    def test_standalone_claim_locks_stakeholder(self) -> None:
        """Serialize on-demand claims and leave scan associations null."""
        result, connection, cursor = self.claim(
            [(False,), None, (8, "CROSSFEED", "running")]
        )
        self.assertEqual(result.id, 8)
        self.assertIn("FOR UPDATE", cursor.execute.call_args_list[0].args[0])
        self.assertEqual(
            cursor.execute.call_args.args[1],
            ("CROSSFEED", "running", None, None, "held"),
        )
        connection.commit.assert_called_once()

    def test_linked_claim_uses_existing_matching_tracker(self) -> None:
        """Attach an unsent real tracker row using the unique claim constraint."""
        result, connection, cursor = self.claim(
            [(False,), None, ("CROSSFEED", None), (8, "CROSSFEED", "running")], 9
        )
        self.assertEqual(result.id, 8)
        self.assertEqual(cursor.execute.call_args.args[1][-2:], (9, "held"))

    def test_held_runs_require_explicit_email_claim(self) -> None:
        """Scheduled mailers cannot race an explicit test-recipient send."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None
        report_runs.claim_report_run_email(8, connection)
        self.assertNotIn("held", cursor.execute.call_args.args[1][-1])
        report_runs.claim_report_run_email(8, connection, allow_held=True)
        self.assertIn("held", cursor.execute.call_args.args[1][-1])

    def test_failed_explicit_send_stays_held(self) -> None:
        """Prevent failed test emails from entering automated recipient queues."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (8,)
        report_runs.mark_report_run_email_failed(
            8, "Delivery failed.", connection, hold_for_manual_retry=True
        )
        self.assertEqual(cursor.execute.call_args.args[1][1], "held")

    def test_ready_listing_excludes_held_even_when_retrying(self) -> None:
        """Bulk retries must not send held on-demand reports to customer lists."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        report_runs.list_report_runs_ready_for_email(
            connection, include_previous_failures=True
        )
        self.assertNotIn("held", cursor.execute.call_args.args[1][-1])

    def test_manual_batch_cannot_reclaim_held_generation_failure(self) -> None:
        """Keep on-demand failures out of the manual batch's customer sends."""
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        list_ready_report_candidates(connection, include_manual=True)
        self.assertIn(
            "COALESCE(runs.email_status, 'pending') <> 'held'",
            cursor.execute.call_args.args[0],
        )

    def test_rejects_invalid_or_conflicting_claims(self) -> None:
        """Reject retired tags, active runs, wrong tags, and existing claims."""
        cases: list[tuple[list[object], int | None]] = [
            ([None], None),
            ([(True,)], None),
            ([(False,), (7,)], None),
            ([(False,), None, ("OTHER", None)], 9),
            ([(False,), None, ("CROSSFEED", "2026-09-01")], 9),
            ([(False,), None, ("CROSSFEED", None), None], 9),
        ]
        for rows, tracker_id in cases:
            with self.subTest(rows=rows), self.assertRaises((ValueError, RuntimeError)):
                self.claim(rows, tracker_id)


if __name__ == "__main__":
    unittest.main()
