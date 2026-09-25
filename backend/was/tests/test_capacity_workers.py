"""Verify Docker worker isolation and cleanup without launching containers."""

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from was_reports.utils.capacity_workers import DockerCapacityWorker, launch_docker_worker


class CapacityWorkerTests(unittest.TestCase):
    """Exercise launch configuration and ownership-checked cancellation."""

    def test_launch_maps_paths_and_forwards_secrets_by_name_only(self):
        """Use host ownership and explicit application settings, never a Docker socket."""
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            environment = {"WAS_DB_PASSWORD": "private-secret",
                           "WAS_RUN_MODE": "capacity", "WAS_DB_NAME": "was_capacity_test",
                           "WAS_CAPACITY_TRACKER_IDS": "[1]",
                           "WAS_OUTPUT_DIRECTORY": str(root / "capacity" / "trial"),
                           "WAS_METRICS_DIRECTORY": str(root / "capacity" / "trial" / "metrics"),
                           "AWS_REGION": "us-east-1", "AWS_PROFILE": "unmounted",
                           "TEST_WAS_DB_PASSWORD": "not-needed", "PYTHONPATH": "host-only"}
            with patch.dict(os.environ, environment, clear=True), patch(
                "was_reports.utils.capacity_workers.subprocess.Popen"
            ) as launch:
                worker = launch_docker_worker(
                    ["/host/python", "-m", "was_reports.commands.batch_runner",
                     "--test-recipients", "test@example.com",
                     "--output-directory", str(root / "capacity" / "trial")],
                    run_id="00000000-0000-0000-0000-000000000001", worker_index=2,
                    image="was-reporting", output_directory=root,
                )
            command = launch.call_args.args[0]
            self.assertIn("/output/capacity/trial", command)
            self.assertIn("WAS_DB_PASSWORD", command)
            self.assertNotIn("private-secret", command)
            self.assertNotIn("AWS_PROFILE", command)
            self.assertNotIn("TEST_WAS_DB_PASSWORD", command)
            self.assertNotIn("PYTHONPATH", command)
            self.assertNotIn("/var/run/docker.sock", " ".join(command))
            self.assertIn("{}:{}".format(os.getuid(), os.getgid()), command)
            self.assertEqual(launch.call_args.kwargs["env"]["WAS_METRICS_DIRECTORY"],
                             "/output/capacity/trial/metrics/worker-2")
            self.assertEqual(launch.call_args.kwargs["env"]["WAS_LOG_ROLE"], "worker")
            self.assertEqual(launch.call_args.kwargs["env"]["WAS_LOG_WORKER_INDEX"], "2")
            self.assertEqual(
                launch.call_args.kwargs["env"]["WAS_LOG_PHASE"],
                "report_generation",
            )
            self.assertTrue(worker.name.endswith("-2"))

    def test_invalid_identity_rejected_before_launch(self):
        """An arbitrary container identity cannot be supplied to the launcher."""
        with self.assertRaises(ValueError):
            launch_docker_worker([], run_id="bad", worker_index=0,
                                 image="was-reporting", output_directory=Path("/tmp"))

    def test_capacity_recipients_cannot_be_omitted_or_empty(self):
        """Shared launching retains the mandatory test recipient safety boundary."""
        environment = {"WAS_RUN_MODE": "capacity", "WAS_DB_NAME": "was_capacity_test",
                       "WAS_CAPACITY_TRACKER_IDS": "[1]"}
        with TemporaryDirectory() as directory, patch.dict(os.environ, environment, clear=True), patch(
            "was_reports.utils.capacity_workers.subprocess.Popen"
        ) as launch:
            for options in ([], ["--test-recipients"], ["--test-recipients", ""]):
                with self.subTest(options=options), self.assertRaises(ValueError):
                    launch_docker_worker(
                        ["was_reports.commands.batch_runner"] + options,
                        run_id="00000000-0000-0000-0000-000000000001", worker_index=0,
                        image="was-reporting", output_directory=Path(directory),
                    )
            launch.assert_not_called()

    @patch("was_reports.utils.capacity_workers.subprocess.run")
    def test_cleanup_stops_container_even_when_client_exited(self, run):
        """An exited Docker CLI does not prove its container stopped."""
        process = Mock()
        process.poll.return_value = 1
        run.return_value = subprocess.CompletedProcess([], 0, stdout="owner\n")
        DockerCapacityWorker(process, "owned-container", "owner").stop()
        self.assertEqual(run.call_count, 3)
        self.assertEqual(run.call_args_list[1].args[0],
                         ["docker", "stop", "--time", "30", "owned-container"])
        self.assertEqual(run.call_args_list[2].args[0],
                         ["docker", "rm", "--force", "owned-container"])

    @patch("was_reports.utils.capacity_workers.subprocess.run")
    def test_cleanup_never_stops_other_owner(self, run):
        """Container name reuse alone cannot authorize stopping another run."""
        run.return_value = subprocess.CompletedProcess([], 0, stdout="someone-else\n")
        DockerCapacityWorker(Mock(), "owned-container", "owner").stop()
        self.assertEqual(run.call_count, 1)

    def test_wait_and_poll_delegate(self):
        """Return the Docker client's exit state for coordinator accounting."""
        process = Mock()
        worker = DockerCapacityWorker(process, "name", "owner")
        self.assertEqual(worker.poll(), process.poll.return_value)
        self.assertEqual(worker.wait(timeout=4), process.wait.return_value)
        process.wait.assert_called_once_with(timeout=4)

    @patch("was_reports.utils.capacity_workers.subprocess.run")
    def test_cleanup_inspection_failure_is_not_hidden(self, run):
        """A disconnected Docker daemon must be reported rather than treated as success."""
        run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="unreachable")
        with self.assertRaises(RuntimeError):
            DockerCapacityWorker(Mock(), "owned-container", "owner").stop()

    def test_production_environment_rejected(self):
        """The launcher cannot silently fall back to production settings."""
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                launch_docker_worker(
                    ["was_reports.commands.batch_runner", "--test-recipients", "test@example.com"],
                    run_id="00000000-0000-0000-0000-000000000001", worker_index=0,
                    image="was-reporting", output_directory=Path(directory),
                )

    def test_production_launch_uses_saved_scope_without_recipient_override(self):
        """Shared production workers use ordinary delivery and owned batch names."""
        identity = "00000000-0000-0000-0000-000000000001"
        environment = {"WAS_RUN_MODE": "production", "WAS_DB_NAME": "was",
                       "WAS_BATCH_TRACKER_IDS": "[1]", "WAS_ANALYST_BATCH_ID": identity}
        with TemporaryDirectory() as directory, patch.dict(os.environ, environment, clear=True), patch(
            "was_reports.utils.capacity_workers.subprocess.Popen"
        ) as launch:
            worker = launch_docker_worker(
                ["was_reports.commands.batch_runner"], run_id=identity, worker_index=0,
                image="was-reporting", output_directory=Path(directory),
            )
            self.assertEqual(worker.name, "was-batch-{}-0".format(identity))
            self.assertIn("WAS_BATCH_TRACKER_IDS", launch.call_args.args[0])
            for changes in ({"WAS_ANALYST_BATCH_ID": "bad"},
                            {"WAS_CAPACITY_TRACKER_IDS": "[2]"},
                            {"WAS_ANALYST_BATCH_ID": "00000000-0000-0000-0000-000000000002"}):
                with patch.dict(os.environ, changes), self.assertRaises(ValueError):
                    launch_docker_worker(
                        ["was_reports.commands.batch_runner"], run_id=identity, worker_index=0,
                        image="was-reporting", output_directory=Path(directory),
                    )
            del os.environ["WAS_BATCH_TRACKER_IDS"]
            with self.assertRaises(ValueError):
                launch_docker_worker(
                    ["was_reports.commands.batch_runner"], run_id=identity, worker_index=0,
                    image="was-reporting", output_directory=Path(directory),
                )

    @patch("was_reports.utils.capacity_workers.subprocess.run")
    def test_container_removal_failure_is_reported(self, run):
        """Never report a surviving container as successfully cleaned up."""
        run.side_effect = [subprocess.CompletedProcess([], 0, stdout="owner\n"),
                           subprocess.CompletedProcess([], 0),
                           subprocess.CompletedProcess([], 1, stdout="", stderr="unreachable")]
        with self.assertRaises(RuntimeError):
            DockerCapacityWorker(Mock(), "owned-container", "owner").stop()
