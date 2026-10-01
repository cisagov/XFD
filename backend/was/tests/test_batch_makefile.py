"""Verify batch Make targets agree without starting containers or delivery."""

# Standard Python Libraries
from pathlib import Path
import subprocess
import unittest


class BatchMakefileTests(unittest.TestCase):
    """Keep production, preview, and assignee-test date scopes aligned."""

    def test_production_public_target_starts_persistent_tmux_launcher(self) -> None:
        """Submit production through the persistent host launcher."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["make", "-n", "-C", str(directory), "recent-scan-batch"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        self.assertIn("was_reports.commands.tmux_batch start", result.stdout)
        self.assertIn("--workflow production", result.stdout)
        self.assertNotIn("was_reports.commands.batch_coordinator", result.stdout)

    def test_production_internal_target_uses_shared_coordinator(self) -> None:
        """Keep the detached implementation on the shared Python workflow."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "make",
                "-s",
                "-C",
                str(directory),
                "_recent-scan-batch-foreground",
                "BATCH_RUN_ID=00000000-0000-0000-0000-000000000000",
                "PYTHON=/bin/echo",
                "WAS_TMUX_LAUNCH=1",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        self.assertIn("was_reports.commands.batch_coordinator", result.stdout)
        self.assertIn("--workers 30 --worker-backend docker", result.stdout)
        self.assertIn("--worker-image was-reporting", result.stdout)
        self.assertIn("--lookback-days 3 --apply", result.stdout)
        self.assertIn(
            "--run-id 00000000-0000-0000-0000-000000000000",
            result.stdout,
        )
        self.assertIn("--delete-apps", result.stdout)
        self.assertNotIn("--test-recipients", result.stdout)
        self.assertNotIn("worker_pids=", result.stdout)
        self.assertNotIn("--send-assignee-digests", result.stdout)

    def test_capacity_apply_detaches_but_preview_stays_foreground(self) -> None:
        """Require APPLY=1 before capacity work moves into tmux."""
        directory = Path(__file__).resolve().parents[1]
        base_command = [
            "make",
            "-n",
            "-C",
            str(directory),
            "capacity-start",
            "TEST_RECIPIENTS=preview@example.invalid",
        ]
        preview = subprocess.run(
            base_command,
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        applied = subprocess.run(
            base_command + ["APPLY=1"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        self.assertIn("was_reports.commands.capacity_test", preview.stdout)
        self.assertNotIn("was_reports.commands.tmux_batch start", preview.stdout)
        self.assertIn("was_reports.commands.tmux_batch start", applied.stdout)
        self.assertIn("--workflow capacity", applied.stdout)
        self.assertNotIn("was_reports.commands.capacity_test", applied.stdout)

    def test_assignee_test_inherits_default_and_explicit_windows(self) -> None:
        """Dry-run expansion forwards seven days by default and honors overrides."""
        directory = Path(__file__).resolve().parents[1]
        for override, expected in (
            (None, "7"),
            ("1", "1"),
            ("30", "30"),
            ("all", "all"),
        ):
            with self.subTest(override=override):
                command = [
                    "make",
                    "-n",
                    "-C",
                    str(directory),
                    "recent-scan-batch-assignee-test",
                    "TEST_RECIPIENTS=preview@example.invalid",
                ]
                if override is not None:
                    command.append("BATCH_DAYS_BACK={}".format(override))
                result = subprocess.run(
                    command, capture_output=True, text=True, check=True, timeout=15
                )
                self.assertIn('BATCH_DAYS_BACK="{}"'.format(expected), result.stdout)
                self.assertIn("web application deletion is disabled", result.stdout)
                self.assertIn("1 means today only", result.stdout)
                self.assertIn("was_reports.commands.tmux_batch start", result.stdout)
                self.assertNotIn("previous 30 calendar days", result.stdout)

    def test_assignee_internal_target_does_not_authorize_deletion(self) -> None:
        """Keep the recipient-override coordinator refresh non-destructive."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "make",
                "-s",
                "-C",
                str(directory),
                "_recent-scan-batch-foreground",
                "BATCH_TEST_RECIPIENTS=preview@example.invalid",
                "PYTHON=/bin/echo",
                "WAS_TMUX_LAUNCH=1",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

        self.assertIn("--test-recipients preview@example.invalid", result.stdout)
        self.assertNotIn("--delete-apps", result.stdout)

    def test_log_diagnostics_remain_make_only_and_read_batch_files(self) -> None:
        """Expose summary, error, and tag filters without adding menu operations."""
        directory = Path(__file__).resolve().parents[1]
        commands: dict[str, tuple[str, list[str]]] = {
            "logs-latest": ("--latest --mode summary", []),
            "logs-summary": ("--mode summary", ["LOG_BATCH_ID=" + "0" * 36]),
            "logs-errors": ("--mode errors", ["LOG_BATCH_ID=" + "0" * 36]),
            "logs-tag": (
                '--mode tag --tag "TAG1"',
                ["LOG_BATCH_ID=" + "0" * 36, "LOG_TAG=TAG1"],
            ),
        }
        for target, (expected, variables) in commands.items():
            with self.subTest(target=target):
                result = subprocess.run(
                    ["make", "-n", "-C", str(directory), target] + variables,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=15,
                )
                self.assertIn("was_reports.commands.log_diagnostics", result.stdout)
                self.assertIn(expected, result.stdout)

    def test_failed_tmux_cleanup_acknowledges_one_exact_session(self) -> None:
        """Scope failed-pane cleanup acknowledgement to one validated session."""
        directory = Path(__file__).resolve().parents[1]
        session = "was-production-5cb98f63-7a8e-4ff4-aac5-461732f50204"
        result = subprocess.run(
            [
                "make",
                "-n",
                "-C",
                str(directory),
                "recent-scan-batch-cleanup",
                "TMUX_CLEANUP_ACKNOWLEDGE_FAILURES=1",
                "TMUX_SESSION={}".format(session),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        self.assertIn("--acknowledge-failures", result.stdout)
        self.assertIn('--session "{}"'.format(session), result.stdout)

    def test_targets_removed_test_requires_explicit_rows_and_assignee(self) -> None:
        """Route a reviewed Targets Removed test through isolated replay."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "make",
                "-n",
                "-C",
                str(directory),
                "test-targets-removed",
                "TARGETS_REMOVED_TRACKER_IDS=260169,260087",
                "TEST_RECIPIENTS=analyst@example.gov",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

        self.assertIn("test-report-replay", result.stdout)
        self.assertIn(
            '--targets-removed-tracker-ids "260169,260087"',
            result.stdout,
        )
        self.assertIn('--test-recipients "analyst@example.gov"', result.stdout)

    def test_delivery_reconciliation_uses_guarded_entrypoint(self) -> None:
        """Keep held delivery recovery behind its dedicated command."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [
                "make",
                "-n",
                "-C",
                str(directory),
                "reconcile-email-delivery",
                "REPORT_RUN_ID=3703",
                "RECONCILIATION_ACTION=retry-confirmed-undelivered",
                "RECONCILIATION_REFERENCE=reviewed-evidence",
                "TEST_RECIPIENTS=analyst@example.gov",
                "APPLY=1",
                "RECONCILIATION_CONFIRM=NONDELIVERY_CONFIRMED_RETRY",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )

        self.assertIn("--entrypoint was-reconcile-delivery", result.stdout)
        self.assertIn("--test-recipients", result.stdout)
        self.assertIn("--apply --confirm", result.stdout)
        self.assertNotIn("--entrypoint was-mailer", result.stdout)
