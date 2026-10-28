"""Preview or remove confirmed orphaned WAS Docker worker containers."""

# Standard Python Libraries
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import shutil
import subprocess  # nosec B404
from uuid import UUID

# Third-Party Libraries
from was_reports.commands.tmux_batch import workflow_pane_states

OWNER_LABEL = "was.capacity.owner"
RUN_ID_LABEL = "was.capacity.run_id"
WORKFLOW_LABEL = "was.capacity.workflow"
WORKER_INDEX_LABEL = "was.capacity.worker_index"
DEFAULT_MINIMUM_AGE_HOURS = 12
MAXIMUM_AGE_HOURS = 168
WORKFLOW_IDENTITIES = {
    "capacity": ("was-capacity-", "was-capacity-"),
    "production": ("was-batch-", "was-production-"),
}


@dataclass(frozen=True)
class WorkerContainer:
    """Store validated immutable identity for one running WAS worker."""

    container_id: str
    name: str
    owner: str
    run_id: str
    started_at: datetime
    workflow: str
    worker_index: int

    @property
    def coordinator_session(self) -> str:
        """Return the exact tmux session expected to own this worker."""
        session_prefix = WORKFLOW_IDENTITIES[self.workflow][1]
        return "{}{}".format(session_prefix, self.run_id)


def minimum_age_hours(value: str) -> int:
    """Parse a bounded positive orphan-runtime threshold in hours."""
    try:
        hours = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Minimum container age must be an integer."
        ) from error
    if not 1 <= hours <= MAXIMUM_AGE_HOURS:
        raise argparse.ArgumentTypeError(
            "Minimum container age must be from 1 through {} hours.".format(
                MAXIMUM_AGE_HOURS
            )
        )
    return hours


def parse_args(argv=None):
    """Parse preview-first orphan cleanup arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--minimum-age-hours",
        type=minimum_age_hours,
        default=DEFAULT_MINIMUM_AGE_HOURS,
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def require_executable(name: str) -> str:
    """Resolve one required host executable before inspecting worker state."""
    executable = shutil.which(name)
    if executable is None:
        raise RuntimeError("{} is required for orphan worker cleanup.".format(name))
    return executable


def docker_command(
    executable: str,
    arguments: list[str],
    *,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Run a bounded Docker command without invoking a shell."""
    return subprocess.run(  # nosec B603
        [executable] + arguments,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def missing_container_error(result: subprocess.CompletedProcess) -> bool:
    """Return whether Docker reports that an exact container disappeared."""
    error_text = (result.stderr or result.stdout or "").lower()
    return "no such object" in error_text or "no such container" in error_text


def list_owned_container_ids(executable: str) -> list[str]:
    """List running containers carrying the exact WAS worker ownership label."""
    result = docker_command(
        executable,
        [
            "ps",
            "--filter",
            "label={}".format(OWNER_LABEL),
            "--format",
            "{{.ID}}",
        ],
    )
    if result.returncode != 0:
        raise RuntimeError("Unable to list WAS-owned Docker worker containers.")
    container_ids = []
    for container_id in result.stdout.splitlines():
        normalized_id = container_id.strip()
        if normalized_id:
            container_ids.append(normalized_id)
    return container_ids


def inspect_container(executable: str, container_id: str) -> dict | None:
    """Read one exact container, returning None only when it disappeared."""
    result = docker_command(executable, ["inspect", container_id])
    if result.returncode != 0:
        if missing_container_error(result):
            return None
        raise RuntimeError(
            "Unable to inspect WAS worker container {}.".format(container_id)
        )
    try:
        documents = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Docker returned invalid inspection data.") from error
    if not isinstance(documents, list) or len(documents) != 1:
        raise RuntimeError("Docker returned ambiguous inspection data.")
    document = documents[0]
    if not isinstance(document, dict):
        raise RuntimeError("Docker returned invalid container metadata.")
    return document


def parse_started_at(value: object) -> datetime:
    """Parse Docker's timezone-aware RFC 3339 start timestamp."""
    if not isinstance(value, str) or not value:
        raise ValueError("WAS worker start time is missing.")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        started_at = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError("WAS worker start time is invalid.") from error
    if started_at.tzinfo is None:
        raise ValueError("WAS worker start time must include a timezone.")
    return started_at.astimezone(timezone.utc)


def inspection_reports_stopped(document: dict) -> bool:
    """Return whether a valid Docker state says the worker already stopped."""
    state = document.get("State")
    return isinstance(state, dict) and state.get("Running") is False


def identity_from_name(name: str) -> tuple[str, str, int]:
    """Derive workflow, run UUID, and worker index from an exact worker name."""
    for workflow, identity_prefixes in WORKFLOW_IDENTITIES.items():
        container_prefix = identity_prefixes[0]
        if not name.startswith(container_prefix):
            continue
        raw_identity = name[len(container_prefix) :]
        raw_run_id, separator, raw_worker_index = raw_identity.rpartition("-")
        if not separator or not raw_worker_index.isdigit():
            break
        try:
            run_id = str(UUID(raw_run_id))
        except ValueError as error:
            raise ValueError("WAS worker name contains an invalid run ID.") from error
        if run_id != raw_run_id:
            raise ValueError("WAS worker name must use a canonical run ID.")
        worker_index = int(raw_worker_index)
        if not 0 <= worker_index < 30:
            raise ValueError("WAS worker name contains an invalid worker index.")
        expected_name = "{}{}-{}".format(container_prefix, run_id, worker_index)
        if name != expected_name:
            raise ValueError("WAS worker name is not canonical.")
        return workflow, run_id, worker_index
    raise ValueError("Ownership-labeled container has an unknown WAS worker name.")


def validated_worker(document: dict) -> WorkerContainer:
    """Validate Docker metadata before treating a container as WAS-owned."""
    raw_container_id = document.get("Id")
    raw_name = document.get("Name")
    configuration = document.get("Config")
    state = document.get("State")
    if not isinstance(raw_container_id, str) or not raw_container_id:
        raise ValueError("WAS worker container ID is missing.")
    if not isinstance(raw_name, str) or not raw_name.startswith("/"):
        raise ValueError("WAS worker container name is invalid.")
    if not isinstance(configuration, dict) or not isinstance(state, dict):
        raise ValueError("WAS worker inspection metadata is incomplete.")
    if state.get("Running") is not True:
        raise ValueError("Ownership-labeled WAS worker is not running.")
    labels = configuration.get("Labels")
    if not isinstance(labels, dict):
        raise ValueError("WAS worker labels are missing.")
    owner = labels.get(OWNER_LABEL)
    try:
        normalized_owner = str(UUID(owner))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("WAS worker ownership label is invalid.") from error
    if normalized_owner != owner:
        raise ValueError("WAS worker ownership label must be canonical.")
    name = raw_name[1:]
    workflow, run_id, worker_index = identity_from_name(name)
    optional_labels = {
        RUN_ID_LABEL: run_id,
        WORKFLOW_LABEL: workflow,
        WORKER_INDEX_LABEL: str(worker_index),
    }
    present_optional_labels = [
        label_name for label_name in optional_labels if label_name in labels
    ]
    if present_optional_labels and len(present_optional_labels) != len(optional_labels):
        raise ValueError("WAS worker identity labels are incomplete.")
    for label_name, expected_value in optional_labels.items():
        if label_name in labels and labels[label_name] != expected_value:
            raise ValueError("WAS worker identity labels do not match its name.")
    return WorkerContainer(
        container_id=raw_container_id,
        name=name,
        owner=owner,
        run_id=run_id,
        started_at=parse_started_at(state.get("StartedAt")),
        workflow=workflow,
        worker_index=worker_index,
    )


def coordinator_is_present(
    executable: str,
    workflow: str,
    session_name: str,
) -> bool:
    """Return whether the exact coordinator has one validated live pane."""
    states = workflow_pane_states(
        executable,
        workflow,
        session=session_name,
    )
    if not states:
        return False
    if len(states) != 1:
        raise RuntimeError(
            "Expected exactly one pane for coordinator {}.".format(session_name)
        )
    return not states[0]["pane_dead"]


def runtime_at(worker: WorkerContainer, observed_at: datetime) -> timedelta:
    """Return a nonnegative worker runtime at a timezone-aware observation."""
    if observed_at.tzinfo is None:
        raise ValueError("Orphan cleanup observation time must include a timezone.")
    runtime = observed_at.astimezone(timezone.utc) - worker.started_at
    if runtime < timedelta(0):
        raise ValueError("WAS worker start time is in the future.")
    return runtime


def stop_and_remove(executable: str, worker: WorkerContainer) -> None:
    """Stop and remove one revalidated container by immutable Docker ID."""
    stop_result = docker_command(
        executable,
        ["stop", "--time", "30", worker.container_id],
        timeout=40,
    )
    if stop_result.returncode != 0 and not missing_container_error(stop_result):
        raise RuntimeError("Unable to stop orphaned WAS worker {}.".format(worker.name))
    removal_result = docker_command(
        executable,
        ["rm", "--force", worker.container_id],
    )
    if removal_result.returncode != 0 and not missing_container_error(removal_result):
        raise RuntimeError(
            "Unable to remove orphaned WAS worker {}.".format(worker.name)
        )


def cleanup_orphaned_workers(
    *,
    apply: bool = False,
    minimum_age: timedelta = timedelta(hours=DEFAULT_MINIMUM_AGE_HOURS),
    now: datetime | None = None,
) -> int:
    """Preview or reap old labeled workers whose exact coordinator is absent."""
    if minimum_age < timedelta(hours=1) or minimum_age > timedelta(
        hours=MAXIMUM_AGE_HOURS
    ):
        raise ValueError(
            "Minimum container age must be from 1 through {} hours.".format(
                MAXIMUM_AGE_HOURS
            )
        )
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("Orphan cleanup observation time must include a timezone.")
    observed_at = observed_at.astimezone(timezone.utc)
    docker_executable = require_executable("docker")
    tmux_executable = require_executable("tmux")
    container_ids = list_owned_container_ids(docker_executable)
    if not container_ids:
        print("No running WAS-owned worker containers were found.")
        return 0
    inspected = 0
    candidates = 0
    retained = 0
    removed = 0
    for container_id in container_ids:
        document = inspect_container(docker_executable, container_id)
        if document is None:
            print("Skipped {}: container ended during inspection.".format(container_id))
            continue
        inspected += 1
        if inspection_reports_stopped(document):
            print("Skipped {}: container ended during inspection.".format(container_id))
            continue
        worker = validated_worker(document)
        runtime = runtime_at(worker, observed_at)
        if runtime < minimum_age:
            retained += 1
            print(
                "Retained {}: runtime is below {} hours.".format(
                    worker.name,
                    int(minimum_age.total_seconds() // 3600),
                )
            )
            continue
        if coordinator_is_present(
            tmux_executable,
            worker.workflow,
            worker.coordinator_session,
        ):
            retained += 1
            print(
                "Retained {}: coordinator {} is present.".format(
                    worker.name,
                    worker.coordinator_session,
                )
            )
            continue
        candidates += 1
        if not apply:
            print(
                "Would stop and remove orphaned WAS worker {} (coordinator {} absent).".format(
                    worker.name,
                    worker.coordinator_session,
                )
            )
            continue
        current_document = inspect_container(docker_executable, worker.container_id)
        if current_document is None:
            print("Skipped {}: container ended before cleanup.".format(worker.name))
            continue
        if inspection_reports_stopped(current_document):
            print("Skipped {}: container ended before cleanup.".format(worker.name))
            continue
        current_worker = validated_worker(current_document)
        if current_worker != worker:
            retained += 1
            print("Retained {}: container identity changed.".format(worker.name))
            continue
        rechecked_at = observed_at if now is not None else datetime.now(timezone.utc)
        current_runtime = runtime_at(current_worker, rechecked_at)
        if current_runtime < minimum_age:
            retained += 1
            print("Retained {}: runtime changed below threshold.".format(worker.name))
            continue
        if coordinator_is_present(
            tmux_executable,
            worker.workflow,
            worker.coordinator_session,
        ):
            retained += 1
            print("Retained {}: coordinator reappeared.".format(worker.name))
            continue
        stop_and_remove(docker_executable, worker)
        removed += 1
        print("Removed orphaned WAS worker {}.".format(worker.name))
    print(
        "Orphan worker cleanup: inspected {}; eligible {}; removed {}; retained {}.".format(
            inspected,
            candidates,
            removed,
            retained,
        )
    )
    return 0


def main(argv=None) -> int:
    """Run preview-first orphan worker cleanup from the command line."""
    arguments = parse_args(argv)
    return cleanup_orphaned_workers(
        apply=arguments.apply,
        minimum_age=timedelta(hours=arguments.minimum_age_hours),
    )


if __name__ == "__main__":
    raise SystemExit(main())
