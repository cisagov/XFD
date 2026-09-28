"""Launch and operate persistent WAS batch sessions through tmux."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from uuid import UUID, uuid4


WORKFLOWS = {
    "production": {
        "prefix": "was-production",
        "target": "_recent-scan-batch-foreground",
    },
    "capacity": {
        "prefix": "was-capacity",
        "target": "_capacity-test-foreground",
    },
}

LAUNCH_ENVIRONMENT_NAMES = (
    "APPLY",
    "BATCH_DAYS_BACK",
    "BATCH_RUN_ID",
    "BATCH_TEST_RECIPIENTS",
    "BATCH_WORKERS",
    "CAPACITY_ACTION",
    "CAPACITY_CONTINUE_RUN_ID",
    "CAPACITY_EXPECTED_CANDIDATES",
    "CAPACITY_RUN_ID",
    "CAPACITY_WORKLOAD_LABEL",
    "ENV_FILE",
    "IMAGE",
    "OUTPUT_DIR",
    "PYTHON",
    "TEST_RECIPIENTS",
    "TRACKER_LOOKBACK_DAYS",
)

UNSAFE_MAKE_VALUE_CHARACTERS = ('"', "\\", "$", "`", "\n", "\r")


def parse_args(argv=None):
    """Parse a tmux session operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--workflow", choices=tuple(WORKFLOWS), required=True)
    start_parser.add_argument("--working-directory", type=Path, required=True)

    for operation in ("status", "attach", "console", "stop"):
        operation_parser = subparsers.add_parser(operation)
        operation_parser.add_argument(
            "--workflow", choices=tuple(WORKFLOWS), required=True
        )

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args(argv)


def require_tmux():
    """Return the tmux executable or fail before creating launch evidence."""
    executable = shutil.which("tmux")
    if executable is None:
        raise RuntimeError("tmux is required for persistent WAS batch commands.")
    return executable


def session_name(workflow, run_id):
    """Create a workflow-owned session name from the validated batch UUID."""
    return "{}-{}".format(WORKFLOWS[workflow]["prefix"], run_id)


def validated_session_name(workflow, name):
    """Reject names that are not the exact workflow prefix plus one UUID."""
    prefix = "{}-".format(WORKFLOWS[workflow]["prefix"])
    if not name.startswith(prefix):
        raise ValueError("TMUX_SESSION does not belong to this workflow.")
    raw_run_id = name[len(prefix):]
    try:
        run_id = str(UUID(raw_run_id))
    except ValueError as error:
        raise ValueError("TMUX_SESSION does not contain a valid batch ID.") from error
    if run_id != raw_run_id:
        raise ValueError("TMUX_SESSION must use the canonical batch ID.")
    return name


def batch_identity(workflow):
    """Use an explicit batch ID when supplied, otherwise generate one now."""
    variable_name = "BATCH_RUN_ID" if workflow == "production" else "CAPACITY_RUN_ID"
    raw_run_id = os.environ.get(variable_name, "").strip()
    try:
        run_id = str(UUID(raw_run_id)) if raw_run_id else str(uuid4())
    except ValueError as error:
        raise ValueError("{} must be a UUID.".format(variable_name)) from error
    return variable_name, run_id


def launch_environment():
    """Copy only approved Make settings into the detached execution manifest."""
    environment = {
        name: os.environ[name]
        for name in LAUNCH_ENVIRONMENT_NAMES
        if name in os.environ
    }
    for name, value in environment.items():
        if any(character in value for character in UNSAFE_MAKE_VALUE_CHARACTERS):
            raise ValueError(
                "{} contains a character unsafe for the internal Make target.".format(
                    name
                )
            )
    return environment


def write_manifest(workflow, working_directory, name, variable_name, run_id):
    """Persist the exact detached Make invocation without copying secrets."""
    environment = launch_environment()
    environment[variable_name] = run_id
    environment["WAS_TMUX_LAUNCH"] = "1"
    output_root = Path(os.environ.get("OUTPUT_DIR", working_directory / "local-output"))
    manifest_directory = output_root.expanduser().resolve() / "tmux-launches"
    manifest_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_directory / "{}.json".format(name)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "environment": environment,
        "run_id": run_id,
        "session_name": name,
        "target": WORKFLOWS[workflow]["target"],
        "version": 1,
        "workflow": workflow,
        "working_directory": str(working_directory),
    }
    descriptor = os.open(
        manifest_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2, sort_keys=True)
        manifest_file.write("\n")
    return manifest_path


def tmux_command(executable, *arguments, check=True, capture_output=False):
    """Run tmux with an argument vector and never through a shell."""
    return subprocess.run(
        [executable] + list(arguments),
        check=check,
        capture_output=capture_output,
        text=True,
    )


def validate_workflow_environment(workflow):
    """Enforce launch-time authorization boundaries before detaching."""
    if workflow != "capacity":
        return
    if os.environ.get("APPLY") != "1":
        raise ValueError("Applied capacity tmux sessions require APPLY=1.")
    recipients = os.environ.get("TEST_RECIPIENTS", "").strip()
    if not recipients or recipients == "operator@example.gov":
        raise ValueError("Set TEST_RECIPIENTS to approved test recipients.")
    if os.environ.get("CAPACITY_ACTION", "start") not in ("start", "continue"):
        raise ValueError("CAPACITY_ACTION must be start or continue.")


def start_session(workflow, working_directory):
    """Create a dormant session, configure retention, then start the workload."""
    validate_workflow_environment(workflow)
    executable = require_tmux()
    directory = working_directory.expanduser().resolve()
    makefile = directory / "Makefile"
    if not makefile.is_file():
        raise ValueError("Working directory does not contain the WAS Makefile.")
    variable_name, run_id = batch_identity(workflow)
    name = session_name(workflow, run_id)
    manifest_path = write_manifest(
        workflow, directory, name, variable_name, run_id
    )
    runner = shlex.join(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "run",
            "--manifest",
            str(manifest_path),
        ]
    )
    created = False
    try:
        tmux_command(
            executable, "new-session", "-d", "-s", name, "-c", str(directory)
        )
        created = True
        tmux_command(
            executable, "set-window-option", "-t", "{}:0".format(name),
            "remain-on-exit", "on"
        )
        tmux_command(
            executable, "set-window-option", "-t", "{}:0".format(name),
            "history-limit", "50000"
        )
        tmux_command(
            executable, "respawn-pane", "-k", "-t",
            "{}:0.0".format(name), runner
        )
    except BaseException:
        if created:
            tmux_command(
                executable, "kill-session", "-t", name,
                check=False
            )
        raise
    command_prefix = (
        "recent-scan-batch" if workflow == "production" else "capacity"
    )
    print("Started detached tmux session: {}".format(name))
    print("Batch ID: {}".format(run_id))
    print("Submission succeeded; batch preflight and execution are not yet verified.")
    print("Manifest: {}".format(manifest_path))
    print("Status: make {}-status TMUX_SESSION={}".format(command_prefix, name))
    print("Console: make {}-console TMUX_SESSION={}".format(command_prefix, name))
    print("Attach: make {}-attach TMUX_SESSION={}".format(command_prefix, name))
    print("Stop: make {}-stop TMUX_SESSION={}".format(command_prefix, name))
    print("Batch logs: make logs-summary LOG_BATCH_ID={}".format(run_id))
    return 0


def read_manifest(manifest_path):
    """Load and validate a launcher-owned manifest before executing Make."""
    with manifest_path.open(encoding="utf-8") as manifest_file:
        manifest = json.load(manifest_file)
    workflow = manifest.get("workflow")
    if workflow not in WORKFLOWS:
        raise ValueError("Launch manifest has an unsupported workflow.")
    if manifest.get("target") != WORKFLOWS[workflow]["target"]:
        raise ValueError("Launch manifest target does not match its workflow.")
    if manifest.get("version") != 1:
        raise ValueError("Launch manifest version is unsupported.")
    try:
        run_id = str(UUID(manifest.get("run_id", "")))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("Launch manifest batch ID is invalid.") from error
    if manifest.get("session_name") != session_name(workflow, run_id):
        raise ValueError("Launch manifest session does not match its batch ID.")
    environment = manifest.get("environment")
    if not isinstance(environment, dict) or any(
        name not in LAUNCH_ENVIRONMENT_NAMES + ("WAS_TMUX_LAUNCH",)
        or not isinstance(value, str)
        for name, value in environment.items()
    ):
        raise ValueError("Launch manifest environment is invalid.")
    directory = Path(manifest.get("working_directory", "")).resolve()
    if not directory.joinpath("Makefile").is_file():
        raise ValueError("Launch manifest working directory is invalid.")
    return manifest, directory


def run_manifest(manifest_path):
    """Run the fixed internal Make target using the saved launch settings."""
    manifest, directory = read_manifest(manifest_path.expanduser().resolve())
    make_executable = shutil.which("make")
    if make_executable is None:
        raise RuntimeError("make is required to run the detached WAS batch.")
    environment = os.environ.copy()
    environment.pop("MAKEFLAGS", None)
    environment.pop("MFLAGS", None)
    environment.update(manifest["environment"])
    environment["PYTHONUNBUFFERED"] = "1"
    result = subprocess.run(
        [make_executable, "-C", str(directory), manifest["target"]],
        cwd=directory,
        env=environment,
        check=False,
    )
    return result.returncode


def matching_sessions(executable, workflow):
    """List exact WAS-owned sessions for one workflow."""
    result = tmux_command(
        executable,
        "list-sessions",
        "-F",
        "#{session_created}\t#{session_name}",
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return []
    sessions = []
    for line in result.stdout.splitlines():
        created, separator, name = line.partition("\t")
        if not separator or not created.isdigit():
            continue
        try:
            validated_session_name(workflow, name)
        except ValueError:
            continue
        sessions.append((int(created), name))
    return [name for created, name in sorted(sessions)]


def selected_session(executable, workflow, require_explicit=False):
    """Select an explicit owned session, or the latest matching session."""
    explicit = os.environ.get("TMUX_SESSION", "").strip()
    if explicit:
        return validated_session_name(workflow, explicit)
    if require_explicit:
        raise ValueError("Set TMUX_SESSION to the exact session before stopping it.")
    sessions = matching_sessions(executable, workflow)
    if not sessions:
        raise RuntimeError("No matching tmux sessions were found.")
    return sessions[-1]


def show_status(workflow):
    """Show retained pane state for all sessions in one workflow."""
    executable = require_tmux()
    if os.environ.get("TMUX_SESSION", "").strip():
        sessions = [selected_session(executable, workflow)]
    else:
        sessions = matching_sessions(executable, workflow)
    if not sessions:
        print("No matching tmux sessions were found.")
        return 0
    for name in sessions:
        result = tmux_command(
            executable,
            "list-panes",
            "-t",
            name,
            "-F",
            "#{session_name} pane_dead=#{pane_dead} "
            "exit=#{pane_dead_status} command=#{pane_current_command}",
            capture_output=True,
        )
        print(result.stdout.rstrip())
    return 0


def attach_session(workflow):
    """Attach the terminal to an explicit or latest matching session."""
    executable = require_tmux()
    name = selected_session(executable, workflow)
    os.execv(executable, [executable, "attach-session", "-t", name])


def show_console(workflow):
    """Print recent retained pane output without attaching."""
    executable = require_tmux()
    name = selected_session(executable, workflow)
    raw_lines = os.environ.get("TMUX_LINES", "200")
    try:
        line_count = int(raw_lines)
    except ValueError as error:
        raise ValueError("TMUX_LINES must be an integer.") from error
    if not 1 <= line_count <= 50000:
        raise ValueError("TMUX_LINES must be from 1 through 50000.")
    result = tmux_command(
        executable,
        "capture-pane",
        "-p",
        "-t",
        "{}:0.0".format(name),
        "-S",
        "-{}".format(line_count),
        capture_output=True,
    )
    print(result.stdout, end="")
    return 0


def stop_session(workflow):
    """Interrupt an explicit live session so coordinator cleanup can run."""
    executable = require_tmux()
    name = selected_session(executable, workflow, require_explicit=True)
    raw_wait_seconds = os.environ.get("TMUX_STOP_WAIT_SECONDS", "60")
    try:
        wait_seconds = int(raw_wait_seconds)
    except ValueError as error:
        raise ValueError("TMUX_STOP_WAIT_SECONDS must be an integer.") from error
    if not 0 <= wait_seconds <= 60:
        raise ValueError("TMUX_STOP_WAIT_SECONDS must be from 0 through 60.")
    tmux_command(
        executable, "send-keys", "-t", "{}:0.0".format(name), "C-c"
    )
    print("Sent SIGINT to tmux session: {}".format(name))
    for remaining_checks in range(wait_seconds + 1):
        result = tmux_command(
            executable,
            "list-panes",
            "-t",
            name,
            "-F",
            "#{pane_dead}\t#{pane_dead_status}",
            check=False,
            capture_output=True,
        )
        if result.returncode == 0 and result.stdout.startswith("1\t"):
            status = result.stdout.partition("\t")[2].strip() or "unknown"
            print("Coordinator exited after cleanup with status {}.".format(status))
            return 0
        if remaining_checks < wait_seconds:
            time.sleep(1)
    print(
        "Coordinator cleanup is still running after {} seconds. "
        "Check status and console output.".format(wait_seconds)
    )
    return 0


def main(argv=None):
    """Dispatch one persistent batch session operation."""
    arguments = parse_args(argv)
    if arguments.operation == "start":
        return start_session(arguments.workflow, arguments.working_directory)
    if arguments.operation == "run":
        return run_manifest(arguments.manifest)
    if arguments.operation == "status":
        return show_status(arguments.workflow)
    if arguments.operation == "attach":
        return attach_session(arguments.workflow)
    if arguments.operation == "console":
        return show_console(arguments.workflow)
    if arguments.operation == "stop":
        return stop_session(arguments.workflow)
    raise RuntimeError("Unsupported tmux batch operation.")


if __name__ == "__main__":
    raise SystemExit(main())
