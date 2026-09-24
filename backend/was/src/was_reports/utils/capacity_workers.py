"""Launch isolated capacity workers as sibling Docker containers from the host."""

import os
from pathlib import Path
import subprocess  # nosec B404
from uuid import UUID, uuid4

from was_reports.utils.capacity_scope import capacity_tracker_ids


def _container_path(value: str, root: Path, destination: str) -> str:
    """Translate absolute output paths, leaving unrelated values unchanged."""
    if not value.startswith("/"):
        return value
    try:
        relative = Path(value).relative_to(root)
    except ValueError:
        return value
    return str(Path(destination) / relative)


class DockerCapacityWorker:
    """Represent one foreground Docker client and its explicitly owned container."""

    def __init__(self, process: subprocess.Popen, name: str, ownership: str) -> None:
        """Retain the process and validated container identity for cleanup."""
        self.process = process
        self.name = name
        self.ownership = ownership

    def poll(self) -> int | None:
        """Return the worker exit code once the Docker client has exited."""
        return self.process.poll()

    def wait(self, timeout: float | None = None) -> int:
        """Wait for the worker using the coordinator's remaining time budget."""
        return self.process.wait(timeout=timeout)

    def _stop_client(self) -> None:
        """Reap the client so cancellation cannot race its pending container creation."""
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def stop(self) -> None:
        """Stop and remove only this worker, even if its Docker client exited."""
        inspection = subprocess.run(  # nosec B603 B607
            ["docker", "inspect", "--format",
             '{{index .Config.Labels "was.capacity.owner"}}', self.name],
            check=False, capture_output=True, text=True, timeout=10,
        )
        if inspection.returncode != 0:
            if "No such object" in inspection.stderr or "No such container" in inspection.stderr:
                if self.process.poll() is None:
                    self._stop_client()
                    self.stop()
                return
            self._stop_client()
            raise RuntimeError("Could not verify capacity worker ownership during cleanup.")
        if inspection.stdout.strip() != self.ownership:
            self._stop_client()
            return
        try:
            subprocess.run(  # nosec B603 B607
                ["docker", "stop", "--time", "30", self.name], check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40,
            )
        finally:
            try:
                removal = subprocess.run(  # nosec B603 B607
                    ["docker", "rm", "--force", self.name], check=False,
                    capture_output=True, text=True, timeout=10,
                )
                if removal.returncode != 0 and not any(
                    message in removal.stderr for message in ("No such object", "No such container")
                ):
                    raise RuntimeError("Could not remove capacity worker container during cleanup.")
            finally:
                self._stop_client()


def launch_docker_worker(
    arguments: list[str], *, run_id: str, worker_index: int, image: str,
    output_directory: Path, container_output_directory: str = "/output",
) -> DockerCapacityWorker:
    """Launch a scoped worker without exposing environment secrets in arguments."""
    identity = str(UUID(run_id))
    if type(worker_index) is not int or not 0 <= worker_index < 30:
        raise ValueError("Capacity worker index must be from 0 through 29.")
    if not image or image.startswith("-") or any(value.isspace() for value in image):
        raise ValueError("A valid Docker image reference is required.")
    root = output_directory.resolve()
    if not root.is_dir() or ":" in str(root):
        raise ValueError("The capacity output directory must exist and cannot contain a colon.")
    if not container_output_directory.startswith("/") or ":" in container_output_directory:
        raise ValueError("The container output directory must be an absolute mount path.")
    module_arguments = list(arguments)
    if len(module_arguments) >= 3 and module_arguments[1] == "-m":
        module_arguments = module_arguments[2:]
    if not module_arguments or module_arguments[0] != "was_reports.commands.batch_runner":
        raise ValueError("Only the capacity batch worker module can be launched.")
    mode = os.environ.get("WAS_RUN_MODE")
    if mode not in {"capacity", "production"} or capacity_tracker_ids() is None:
        raise ValueError("Docker workers require explicit coordinator workload scope.")
    if mode == "production" and str(UUID(os.environ["WAS_ANALYST_BATCH_ID"])) != identity:
        raise ValueError("Docker worker identity must match its batch scope.")
    if mode == "capacity" or "--test-recipients" in module_arguments:
        try:
            recipients = module_arguments[module_arguments.index("--test-recipients") + 1]
        except (ValueError, IndexError) as error:
            raise ValueError("Docker capacity workers require explicit test recipients.") from error
        if not recipients.strip() or recipients.startswith("-"):
            raise ValueError("Docker workers require nonempty explicit test recipients.")
    environment = dict(os.environ)
    aws_variables = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
                     "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_EC2_METADATA_DISABLED",
                     "AWS_METADATA_SERVICE_TIMEOUT", "AWS_METADATA_SERVICE_NUM_ATTEMPTS"}
    forwarded = sorted(name for name in environment
                       if (name.startswith("WAS_") and name != "WAS_RESOURCE_ROOT")
                       or name in aws_variables)
    for name in forwarded:
        if name.endswith(("_DIRECTORY", "_PATH", "_FILE")):
            environment[name] = _container_path(environment[name], root, container_output_directory)
    if "WAS_METRICS_DIRECTORY" in environment:
        environment["WAS_METRICS_DIRECTORY"] = str(
            Path(environment["WAS_METRICS_DIRECTORY"]) / "worker-{}".format(worker_index)
        )
    name = "was-{}-{}-{}".format("capacity" if mode == "capacity" else "batch", identity, worker_index)
    ownership = str(uuid4())
    command = ["docker", "run", "--rm", "--name", name, "--init",
               "--user", "{}:{}".format(os.getuid(), os.getgid()),
               "--label", "was.capacity.owner={}".format(ownership),
               "-v", "{}:{}".format(root, container_output_directory)]
    for variable in forwarded:
        command.extend(["-e", variable])
    command.extend(["--entrypoint", "python", image, "-m"])
    command.extend(_container_path(value, root, container_output_directory)
                   for value in module_arguments)
    process = subprocess.Popen(command, env=environment, start_new_session=True)  # nosec B603
    return DockerCapacityWorker(process, name, ownership)
