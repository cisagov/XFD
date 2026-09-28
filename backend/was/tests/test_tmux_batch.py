"""Persistent tmux batch launcher tests without starting real sessions."""

import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from was_reports.commands import tmux_batch


PRODUCTION_RUN_ID = "5cb98f63-7a8e-4ff4-aac5-461732f50204"
CAPACITY_RUN_ID = "96978f00-a576-4cb1-9bac-af3666764766"


class TmuxBatchTests(unittest.TestCase):
    """Verify detached sessions preserve scope and avoid shell interpolation."""

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
            ), patch.object(tmux_batch.subprocess, "run", return_value=completed) as run:
                self.assertEqual(
                    tmux_batch.start_session("production", working_directory), 0
                )

            manifest_path = output_directory / "tmux-launches" / (
                "was-production-{}.json".format(PRODUCTION_RUN_ID)
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], PRODUCTION_RUN_ID)
            self.assertEqual(
                manifest["target"], "_recent-scan-batch-foreground"
            )
            self.assertEqual(manifest["environment"]["BATCH_WORKERS"], "30")
            self.assertNotIn("UNRELATED_SECRET", manifest["environment"])
            self.assertEqual(run.call_args_list[0].args[0][0:4], [
                "/usr/bin/tmux", "new-session", "-d", "-s"
            ])
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

            self.assertEqual(run.call_args.args[0], [
                "/usr/bin/make",
                "-C",
                str(working_directory.resolve()),
                "_capacity-test-foreground",
            ])
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

    def test_stop_sends_interrupt_without_killing_session(self):
        """Allow coordinator cleanup after a deliberate exact-session interrupt."""
        name = "was-capacity-{}".format(CAPACITY_RUN_ID)
        with patch.dict(
            os.environ,
            {"TMUX_SESSION": name, "TMUX_STOP_WAIT_SECONDS": "0"},
            clear=True,
        ), patch.object(
            tmux_batch, "require_tmux", return_value="/usr/bin/tmux"
        ), patch.object(tmux_batch, "tmux_command") as command:
            self.assertEqual(tmux_batch.stop_session("capacity"), 0)
        self.assertEqual(command.call_count, 2)
        self.assertEqual(command.call_args_list[0].args, (
            "/usr/bin/tmux", "send-keys", "-t", "{}:0.0".format(name), "C-c"
        ))
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


if __name__ == "__main__":
    unittest.main()
