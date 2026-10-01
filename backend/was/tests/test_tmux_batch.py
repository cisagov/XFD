"""Persistent tmux batch launcher tests without starting real sessions."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
from was_reports.commands import tmux_batch

PRODUCTION_RUN_ID = "5cb98f63-7a8e-4ff4-aac5-461732f50204"
CAPACITY_RUN_ID = "96978f00-a576-4cb1-9bac-af3666764766"


class TmuxBatchTests(unittest.TestCase):
    """Verify detached sessions preserve scope and avoid shell interpolation."""

    @staticmethod
    def cleanup_tmux_side_effect(pane_output, on_kill=None):
        """Return stable tmux results for cleanup tests without real sessions."""

        def command(executable, *arguments, **kwargs):
            del executable, kwargs
            if arguments[0] == "list-panes":
                return subprocess.CompletedProcess(arguments, 0, stdout=pane_output)
            if arguments[0] == "capture-pane":
                return subprocess.CompletedProcess(
                    arguments, 0, stdout="retained console output\n"
                )
            if arguments[0] == "kill-session":
                if on_kill is not None:
                    on_kill(arguments)
                return subprocess.CompletedProcess(arguments, 0, stdout="")
            raise AssertionError("Unexpected tmux command: {}".format(arguments))

        return command

    def test_start_uses_fixed_tmux_arguments_and_restricted_manifest(self):
        """Launch through argument vectors and retain only approved Make settings."""
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output path"
            environment = {
                "BATCH_RUN_ID": PRODUCTION_RUN_ID,
                "BATCH_WORKERS": "30",
                "OUTPUT_DIR": str(output_directory),
                "UNRELATED_SECRET": "must-not-be-copied",
            }
            completed = MagicMock(returncode=0, stdout="")
            with patch.dict(os.environ, environment, clear=True), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch.subprocess, "run", return_value=completed
            ) as run:
                self.assertEqual(
                    tmux_batch.start_session("production", working_directory), 0
                )

            manifest_path = (
                output_directory
                / "tmux-launches"
                / ("was-production-{}.json".format(PRODUCTION_RUN_ID))
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], PRODUCTION_RUN_ID)
            self.assertEqual(manifest["target"], "_recent-scan-batch-foreground")
            self.assertEqual(manifest["environment"]["BATCH_WORKERS"], "30")
            self.assertNotIn("UNRELATED_SECRET", manifest["environment"])
            self.assertEqual(
                run.call_args_list[0].args[0][0:4],
                ["/usr/bin/tmux", "new-session", "-d", "-s"],
            )
            self.assertEqual(run.call_args_list[-1].args[0][1], "respawn-pane")
            for call in run.call_args_list:
                self.assertNotIn("shell", call.kwargs)

    def test_manifest_runner_invokes_only_fixed_internal_target(self):
        """Run saved settings without inheriting recursive Make control flags."""
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            with patch.dict(
                os.environ,
                {"OUTPUT_DIR": str(working_directory / "output")},
                clear=True,
            ):
                manifest_path = tmux_batch.write_manifest(
                    "capacity",
                    working_directory,
                    "was-capacity-{}".format(CAPACITY_RUN_ID),
                    "CAPACITY_RUN_ID",
                    CAPACITY_RUN_ID,
                )
            completed = MagicMock(returncode=7)
            with patch.dict(
                os.environ, {"MAKEFLAGS": "-n", "MFLAGS": "-n"}, clear=True
            ), patch.object(
                tmux_batch.shutil, "which", return_value="/usr/bin/make"
            ), patch.object(
                tmux_batch.subprocess, "run", return_value=completed
            ) as run:
                self.assertEqual(tmux_batch.run_manifest(manifest_path), 7)

            self.assertEqual(
                run.call_args.args[0],
                [
                    "/usr/bin/make",
                    "-C",
                    str(working_directory.resolve()),
                    "_capacity-test-foreground",
                ],
            )
            self.assertNotIn("MAKEFLAGS", run.call_args.kwargs["env"])
            self.assertNotIn("MFLAGS", run.call_args.kwargs["env"])
            self.assertEqual(
                run.call_args.kwargs["env"]["CAPACITY_RUN_ID"], CAPACITY_RUN_ID
            )
            self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_session_selection_rejects_cross_workflow_and_non_uuid_names(self):
        """Never operate on a loosely matched or different workflow session."""
        invalid_names = (
            "was-capacity-{}".format(CAPACITY_RUN_ID),
            "was-production-not-a-uuid",
            "was-production-{}-extra".format(PRODUCTION_RUN_ID),
        )
        for name in invalid_names:
            with self.subTest(name=name), patch.dict(
                os.environ, {"TMUX_SESSION": name}, clear=True
            ):
                with self.assertRaises(ValueError):
                    tmux_batch.selected_session("/usr/bin/tmux", "production")

    def test_launch_rejects_make_expansion_characters(self):
        """Do not carry shell or Make substitutions into the foreground target."""
        with patch.dict(
            os.environ,
            {"CAPACITY_WORKLOAD_LABEL": "unsafe$(command)"},
            clear=True,
        ):
            with self.assertRaises(ValueError):
                tmux_batch.launch_environment()

    def test_capacity_detach_requires_apply_and_explicit_test_recipient(self):
        """Preserve capacity write authorization and recipient isolation."""
        invalid_environments = (
            {"APPLY": "0", "TEST_RECIPIENTS": "analyst@example.gov"},
            {"APPLY": "1", "TEST_RECIPIENTS": "operator@example.gov"},
            {"APPLY": "1", "TEST_RECIPIENTS": ""},
        )
        for environment in invalid_environments:
            with self.subTest(environment=environment), patch.dict(
                os.environ, environment, clear=True
            ):
                with self.assertRaises(ValueError):
                    tmux_batch.validate_workflow_environment("capacity")

    def test_production_detach_rejects_invalid_days_back_before_tmux(self):
        """Return actionable date guidance before creating a detached session."""
        expected = (
            "BATCH_DAYS_BACK must be all or an integer of at least 1; "
            "1 means today only."
        )
        for value in ("", "0", "-1", "invalid"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"BATCH_DAYS_BACK": value}, clear=True
            ):
                with self.assertRaises(ValueError) as context:
                    tmux_batch.validate_workflow_environment("production")
                self.assertEqual(str(context.exception), expected)

        for value in ("1", "7", "all"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"BATCH_DAYS_BACK": value}, clear=True
            ):
                self.assertIsNone(
                    tmux_batch.validate_workflow_environment("production")
                )

    def test_stop_sends_interrupt_without_killing_session(self):
        """Allow coordinator cleanup after a deliberate exact-session interrupt."""
        name = "was-capacity-{}".format(CAPACITY_RUN_ID)
        with patch.dict(
            os.environ,
            {"TMUX_SESSION": name, "TMUX_STOP_WAIT_SECONDS": "0"},
            clear=True,
        ), patch.object(
            tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
        ), patch.object(
            tmux_batch, "tmux_command"
        ) as command:
            self.assertEqual(tmux_batch.stop_session("capacity"), 0)
        self.assertEqual(command.call_count, 2)
        self.assertEqual(
            command.call_args_list[0].args,
            ("/usr/bin/tmux", "send-keys", "-t", "{}:0.0".format(name), "C-c"),
        )
        self.assertNotIn("kill-session", str(command.call_args_list))

    def test_latest_session_uses_tmux_creation_time(self):
        """Select latest by tmux metadata because session names contain UUIDs."""
        older = "was-capacity-{}".format(PRODUCTION_RUN_ID)
        newer = "was-capacity-{}".format(CAPACITY_RUN_ID)
        output = "20\t{}\n10\t{}\n".format(newer, older)
        result = subprocess.CompletedProcess([], 0, stdout=output)
        with patch.object(tmux_batch, "tmux_command", return_value=result):
            self.assertEqual(
                tmux_batch.matching_sessions("/usr/bin/tmux", "capacity"),
                [older, newer],
            )

    def test_cleanup_skips_live_owned_session(self):
        """Skip live panes and reject sessions outside the exact workflow scope."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        pane_output = (
            "{}\t0\t\t1759250000\t%0\t12345\t\n"
            "was-capacity-{}\t1\t0\t1759250000\t%0\t12345\t\n"
            "was-production-not-a-uuid\t1\t0\t1759250000\t%0\t12345\t\n"
        ).format(session, CAPACITY_RUN_ID)
        fixed_now = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output"
            with patch.dict(
                os.environ, {"OUTPUT_DIR": str(output_directory)}, clear=True
            ), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch,
                "tmux_command",
                side_effect=self.cleanup_tmux_side_effect(pane_output),
            ) as command:
                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        now=fixed_now,
                    ),
                    0,
                )

            operations = [call.args[1] for call in command.call_args_list]
            self.assertEqual(operations, ["list-panes"])
            self.assertFalse(output_directory.exists())

    def test_cleanup_dry_run_writes_nothing_and_kills_nothing(self):
        """Make the default cleanup mode observational even for dead panes."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        pane_output = "{}\t1\t0\t1759250000\t%0\t12345\t\n".format(session)
        fixed_now = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output"
            with patch.dict(
                os.environ, {"OUTPUT_DIR": str(output_directory)}, clear=True
            ), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch,
                "tmux_command",
                side_effect=self.cleanup_tmux_side_effect(pane_output),
            ) as command:
                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production", working_directory, now=fixed_now
                    ),
                    0,
                )

            operations = [call.args[1] for call in command.call_args_list]
            self.assertEqual(operations, ["list-panes"])
            self.assertFalse(output_directory.exists())

    def test_cleanup_reports_tmux_inspection_failure(self):
        """Fail visibly when tmux cannot be inspected for an operational reason."""
        failed = subprocess.CompletedProcess(
            [], 1, stdout="", stderr="permission denied"
        )
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            with patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(tmux_batch, "tmux_command", return_value=failed):
                with self.assertRaisesRegex(RuntimeError, "permission denied"):
                    tmux_batch.cleanup_sessions("production", working_directory)

    def test_cleanup_rejects_malformed_owned_session_state(self):
        """Do not report success when an owned pane has unreadable metadata."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        malformed = subprocess.CompletedProcess(
            [], 0, stdout="{}\t1\n".format(session), stderr=""
        )
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            with patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(tmux_batch, "tmux_command", return_value=malformed):
                with self.assertRaisesRegex(RuntimeError, "malformed state"):
                    tmux_batch.cleanup_sessions("production", working_directory)

    def test_failure_acknowledgement_requires_exact_owned_session(self):
        """Never allow a workflow-wide acknowledgement of failed sessions."""
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            with self.assertRaisesRegex(ValueError, "exact tmux session"):
                tmux_batch.cleanup_sessions(
                    "production",
                    working_directory,
                    acknowledge_failures=True,
                )

    def test_cleanup_discards_incomplete_staging_archive(self):
        """Do not leave a blocking archive directory after an interrupted write."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        pane_output = "{}\t1\t0\t1759250000\t%0\t12345\t\n".format(session)
        fixed_now = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output"
            with patch.dict(
                os.environ, {"OUTPUT_DIR": str(output_directory)}, clear=True
            ), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch,
                "tmux_command",
                side_effect=self.cleanup_tmux_side_effect(pane_output),
            ), patch.object(
                tmux_batch,
                "write_private_file",
                side_effect=OSError("simulated archive interruption"),
            ):
                with self.assertRaisesRegex(OSError, "archive interruption"):
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        now=fixed_now,
                    )

            archive_root = output_directory / "tmux-archives"
            self.assertTrue(archive_root.is_dir())
            self.assertEqual(list(archive_root.iterdir()), [])

    def test_cleanup_rechecks_pane_generation_after_console_capture(self):
        """Discard evidence if the pane is respawned during archival."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        original = "{}\t1\t0\t1759250000\t%0\t12345\t\n".format(session)
        respawned = "{}\t1\t0\t1759250000\t%0\t54321\t\n".format(session)
        fixed_now = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)
        list_calls = []

        def command(executable, *arguments, **kwargs):
            del executable, kwargs
            if arguments[0] == "list-panes":
                list_calls.append(arguments)
                output = original if len(list_calls) < 3 else respawned
                return subprocess.CompletedProcess(arguments, 0, stdout=output)
            if arguments[0] == "capture-pane":
                self.assertIn("%0", arguments)
                return subprocess.CompletedProcess(
                    arguments, 0, stdout="captured console\n"
                )
            raise AssertionError("Unexpected tmux command: {}".format(arguments))

        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output"
            with patch.dict(
                os.environ, {"OUTPUT_DIR": str(output_directory)}, clear=True
            ), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch, "tmux_command", side_effect=command
            ):
                with self.assertRaisesRegex(RuntimeError, "changed while archiving"):
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        now=fixed_now,
                    )

            archive_root = output_directory / "tmux-archives"
            self.assertEqual(list(archive_root.iterdir()), [])

    def test_cleanup_archives_success_before_removing_after_retention(self):
        """Archive a dead success, retain it for 24 hours, then kill exactly it."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        pane_output = "{}\t1\t0\t1759250000\t%0\t12345\t\n".format(session)
        fixed_now = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output"
            archive_directory = output_directory / "tmux-archives" / session
            console_path = archive_directory / "console.log"
            metadata_path = archive_directory / "metadata.json"
            killed = []

            def verify_archive_then_kill(arguments):
                self.assertEqual(arguments, ("kill-session", "-t", session))
                self.assertEqual(
                    console_path.read_text(encoding="utf-8"),
                    "retained console output\n",
                )
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["workflow"], "production")
                self.assertEqual(metadata["session_name"], session)
                self.assertEqual(metadata["run_id"], PRODUCTION_RUN_ID)
                self.assertEqual(metadata["exit_status"], 0)
                self.assertEqual(metadata["console_file"], "console.log")
                killed.append(session)

            side_effect = self.cleanup_tmux_side_effect(
                pane_output, on_kill=verify_archive_then_kill
            )
            with patch.dict(
                os.environ, {"OUTPUT_DIR": str(output_directory)}, clear=True
            ), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch, "tmux_command", side_effect=side_effect
            ) as command:
                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        now=fixed_now,
                    ),
                    0,
                )
                self.assertTrue(console_path.is_file())
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["observed_dead_at"], fixed_now.isoformat())
                self.assertNotIn(
                    "kill-session",
                    [call.args[1] for call in command.call_args_list],
                )

                metadata["observed_dead_at"] = (
                    fixed_now - timedelta(hours=25)
                ).isoformat()
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                command.reset_mock()
                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        now=fixed_now,
                    ),
                    0,
                )

            self.assertEqual(killed, [session])
            kill_call = next(
                call
                for call in command.call_args_list
                if call.args[1] == "kill-session"
            )
            self.assertEqual(kill_call.args[2:], ("-t", session))

    def test_cleanup_retains_failed_session_without_acknowledgement(self):
        """Keep an old failed pane until an operator explicitly acknowledges it."""
        session = "was-production-{}".format(PRODUCTION_RUN_ID)
        pane_output = "{}\t1\t7\t1759250000\t%0\t12345\t\n".format(session)
        fixed_now = datetime(2026, 9, 30, 18, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as directory:
            working_directory = Path(directory)
            working_directory.joinpath("Makefile").write_text("all:\n\t@true\n")
            output_directory = working_directory / "output"
            metadata_path = (
                output_directory / "tmux-archives" / session / "metadata.json"
            )
            with patch.dict(
                os.environ, {"OUTPUT_DIR": str(output_directory)}, clear=True
            ), patch.object(
                tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
            ), patch.object(
                tmux_batch,
                "tmux_command",
                side_effect=self.cleanup_tmux_side_effect(pane_output),
            ) as command:
                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        now=fixed_now,
                    ),
                    2,
                )
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.assertEqual(metadata["exit_status"], 7)
                metadata["observed_dead_at"] = (
                    fixed_now - timedelta(hours=25)
                ).isoformat()
                metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
                command.reset_mock()

                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        acknowledge_failures=False,
                        now=fixed_now,
                    ),
                    2,
                )
                operations = [call.args[1] for call in command.call_args_list]
                self.assertNotIn("kill-session", operations)
                command.reset_mock()

                self.assertEqual(
                    tmux_batch.cleanup_sessions(
                        "production",
                        working_directory,
                        apply=True,
                        acknowledge_failures=True,
                        now=fixed_now,
                        session=session,
                    ),
                    0,
                )

            kill_calls = [
                call
                for call in command.call_args_list
                if call.args[1] == "kill-session"
            ]
            self.assertEqual(len(kill_calls), 1)
            self.assertEqual(kill_calls[0].args[2:], ("-t", session))


if __name__ == "__main__":
    unittest.main()
