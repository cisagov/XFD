"""Launch and operate persistent WAS batch sessions through tmux."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
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
TMUX_ARCHIVE_VERSION = 1
DEFAULT_CLEANUP_RETENTION_HOURS = 24
MAX_CLEANUP_RETENTION_HOURS = 8760


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

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument(
        "--workflow", choices=tuple(WORKFLOWS), required=True
    )
    cleanup_parser.add_argument(
        "--working-directory", type=Path, required=True
    )
    cleanup_parser.add_argument(
        "--retention-hours",
        type=cleanup_retention_hours,
        default=DEFAULT_CLEANUP_RETENTION_HOURS,
    )
    cleanup_parser.add_argument("--apply", action="store_true")
    cleanup_parser.add_argument(
        "--acknowledge-failures", action="store_true"
    )
    cleanup_parser.add_argument("--session")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args(argv)


def cleanup_retention_hours(value):
    """Accept a bounded positive retention period for dead tmux panes."""
    try:
        hours = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Cleanup retention hours must be an integer."
        ) from error
    if not 1 <= hours <= MAX_CLEANUP_RETENTION_HOURS:
        raise argparse.ArgumentTypeError(
            "Cleanup retention hours must be from 1 through {}.".format(
                MAX_CLEANUP_RETENTION_HOURS
            )
        )
    return hours


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
    if workflow == "production":
        raw_days_back = os.environ.get("BATCH_DAYS_BACK", "7").strip()
        if raw_days_back.lower() == "all":
            return
        try:
            days_back = int(raw_days_back)
        except ValueError as error:
            raise ValueError(
                "BATCH_DAYS_BACK must be all or an integer of at least 1; "
                "1 means today only."
            ) from error
        if days_back < 1:
            raise ValueError(
                "BATCH_DAYS_BACK must be all or an integer of at least 1; "
                "1 means today only."
            )
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


def workflow_pane_states(executable, workflow, session=None):
    """Return validated pane state for WAS-owned sessions in one workflow."""
    arguments = [
        "list-panes",
    ]
    if session is None:
        arguments.append("-a")
    else:
        arguments.extend(["-t", session])
    arguments.extend([
        "-F",
        "#{session_name}\t#{pane_dead}\t#{pane_dead_status}\t"
        "#{session_created}\t#{pane_id}\t#{pane_pid}\t#{pane_dead_time}",
    ])
    result = tmux_command(
        executable,
        *arguments,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        error_text = (result.stderr or result.stdout or "").strip()
        normalized_error = error_text.lower()
        expected_missing = "no server running" in normalized_error
        if session is not None:
            expected_missing = expected_missing or (
                "can't find session" in normalized_error
                or "no current client" in normalized_error
            )
        if expected_missing:
            return []
        raise RuntimeError(
            "Unable to inspect tmux panes (status {}). {}".format(
                result.returncode,
                error_text or "No diagnostic output was returned.",
            )
        )
    states = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        name = fields[0] if fields else ""
        try:
            validated_session_name(workflow, name)
        except ValueError:
            continue
        if session is not None and name != session:
            continue
        if len(fields) != 7:
            raise RuntimeError(
                "Tmux returned malformed state for owned session {}.".format(name)
            )
        (
            name,
            pane_dead,
            raw_status,
            raw_created,
            pane_id,
            raw_pane_pid,
            raw_dead_time,
        ) = fields
        if pane_dead not in ("0", "1"):
            raise RuntimeError("Tmux returned an invalid pane state for {}.".format(name))
        if not raw_created.isdigit() or not raw_pane_pid.isdigit():
            raise RuntimeError(
                "Tmux returned invalid process metadata for {}.".format(name)
            )
        if not pane_id.startswith("%") or not pane_id[1:].isdigit():
            raise RuntimeError("Tmux returned an invalid pane ID for {}.".format(name))
        if raw_dead_time and not raw_dead_time.isdigit():
            raise RuntimeError(
                "Tmux returned an invalid pane completion time for {}.".format(name)
            )
        exit_status = None
        if raw_status:
            try:
                exit_status = int(raw_status)
            except ValueError as error:
                raise RuntimeError(
                    "Tmux returned an invalid exit status for {}.".format(name)
                ) from error
        states.append({
            "session_name": name,
            "pane_dead": pane_dead == "1",
            "exit_status": exit_status,
            "pane_id": pane_id,
            "pane_dead_time": int(raw_dead_time) if raw_dead_time else None,
            "pane_pid": int(raw_pane_pid),
            "session_created": int(raw_created),
        })
    return states


def cleanup_output_root(working_directory):
    """Resolve the operator-selected output root used for cleanup evidence."""
    configured = os.environ.get("OUTPUT_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return working_directory.joinpath("local-output").resolve()


def write_private_file(path, content):
    """Create one archive file without following or replacing an existing path."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archive_file:
        archive_file.write(content)


def archive_dead_pane(executable, workflow, state, archive_directory, observed_at):
    """Persist retained console output and immutable first-observed metadata."""
    console_result = tmux_command(
        executable,
        "capture-pane",
        "-p",
        "-t",
        state["pane_id"],
        "-S",
        "-50000",
        capture_output=True,
    )
    archive_root = archive_directory.parent
    archive_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    staging_directory = Path(
        tempfile.mkdtemp(
            prefix=".{}-".format(state["session_name"]),
            dir=archive_root,
        )
    )
    os.chmod(staging_directory, 0o700)
    console_path = staging_directory / "console.log"
    metadata_path = staging_directory / "metadata.json"
    prefix = "{}-".format(WORKFLOWS[workflow]["prefix"])
    metadata = {
        "console_file": console_path.name,
        "exit_status": state["exit_status"],
        "observed_dead_at": observed_at.isoformat(),
        "pane_dead_time": state["pane_dead_time"],
        "pane_id": state["pane_id"],
        "pane_pid": state["pane_pid"],
        "run_id": state["session_name"][len(prefix):],
        "session_created": state["session_created"],
        "session_name": state["session_name"],
        "version": TMUX_ARCHIVE_VERSION,
        "workflow": workflow,
    }
    try:
        write_private_file(console_path, console_result.stdout)
        write_private_file(
            metadata_path,
            "{}\n".format(json.dumps(metadata, indent=2, sort_keys=True)),
        )
        current_states = workflow_pane_states(
            executable, workflow, session=state["session_name"]
        )
        if (
            len(current_states) != 1
            or current_states[0] != state
            or not current_states[0]["pane_dead"]
        ):
            raise RuntimeError(
                "Pane state changed while archiving {}.".format(
                    state["session_name"]
                )
            )
        staging_directory.rename(archive_directory)
    except BaseException:
        shutil.rmtree(staging_directory, ignore_errors=True)
        raise
    return metadata


def read_cleanup_metadata(path, workflow, state):
    """Load trusted cleanup timing only from a matching immutable archive."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Cleanup metadata must be a regular file.")
    with path.open(encoding="utf-8") as metadata_file:
        metadata = json.load(metadata_file)
    expected = {
        "session_name": state["session_name"],
        "session_created": state["session_created"],
        "exit_status": state["exit_status"],
        "pane_dead_time": state["pane_dead_time"],
        "pane_id": state["pane_id"],
        "pane_pid": state["pane_pid"],
        "workflow": workflow,
        "version": TMUX_ARCHIVE_VERSION,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(
                "Cleanup metadata {} does not match the retained pane.".format(key)
            )
    raw_observed_at = metadata.get("observed_dead_at")
    if not isinstance(raw_observed_at, str):
        raise ValueError("Cleanup metadata observed_dead_at is invalid.")
    try:
        observed_at = datetime.fromisoformat(raw_observed_at)
    except ValueError as error:
        raise ValueError(
            "Cleanup metadata observed_dead_at is invalid."
        ) from error
    if observed_at.tzinfo is None:
        raise ValueError("Cleanup metadata observed_dead_at must include a timezone.")
    console_file = metadata.get("console_file")
    if console_file != "console.log":
        raise ValueError("Cleanup metadata console_file is invalid.")
    console_path = path.parent / console_file
    if console_path.is_symlink() or not console_path.is_file():
        raise ValueError("Cleanup console archive is missing or invalid.")
    return metadata, observed_at.astimezone(timezone.utc)


def cleanup_sessions(
    workflow,
    working_directory,
    apply=False,
    acknowledge_failures=False,
    retention_hours=DEFAULT_CLEANUP_RETENTION_HOURS,
    now=None,
    session=None,
):
    """Archive dead panes and reap only reviewed sessions past retention."""
    directory = working_directory.expanduser().resolve()
    if not directory.joinpath("Makefile").is_file():
        raise ValueError("Working directory does not contain the WAS Makefile.")
    if not 1 <= retention_hours <= MAX_CLEANUP_RETENTION_HOURS:
        raise ValueError(
            "Cleanup retention hours must be from 1 through {}.".format(
                MAX_CLEANUP_RETENTION_HOURS
            )
        )
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise ValueError("Cleanup time must include a timezone.")
    observed_at = observed_at.astimezone(timezone.utc)
    acknowledged_session = None
    if acknowledge_failures:
        if not session:
            raise ValueError(
                "Failure acknowledgement requires an exact tmux session."
            )
        acknowledged_session = validated_session_name(workflow, session)
    elif session:
        raise ValueError(
            "An exact cleanup session is used only with failure acknowledgement."
        )
    executable = require_tmux()
    states = workflow_pane_states(executable, workflow)
    if not states:
        print("No matching tmux sessions were found.")
        return 0
    state_counts = {}
    for state in states:
        name = state["session_name"]
        state_counts[name] = state_counts.get(name, 0) + 1
    output_root = cleanup_output_root(directory)
    archive_root = output_root / "tmux-archives"
    retention = timedelta(hours=retention_hours)
    unacknowledged_failures = 0
    for state in states:
        name = state["session_name"]
        if state_counts[name] != 1:
            print("Retained {}: expected exactly one pane.".format(name))
            continue
        if not state["pane_dead"]:
            print("Retained {}: pane is still running.".format(name))
            continue
        if state["exit_status"] != 0 and name != acknowledged_session:
            unacknowledged_failures += 1
        archive_directory = archive_root / name
        if archive_root.is_symlink() or archive_directory.is_symlink():
            raise ValueError("Cleanup archive paths cannot be symbolic links.")
        metadata_path = archive_directory / "metadata.json"
        if not metadata_path.exists():
            if not apply:
                print(
                    "Would archive {} and start its retention period.".format(name)
                )
                continue
            if archive_directory.exists():
                raise ValueError(
                    "Incomplete cleanup archive already exists for {}.".format(name)
                )
            current_states = workflow_pane_states(
                executable, workflow, session=name
            )
            if (
                len(current_states) != 1
                or current_states[0] != state
                or not current_states[0]["pane_dead"]
            ):
                print(
                    "Retained {}: pane state changed before archival.".format(name)
                )
                continue
            archive_dead_pane(
                executable,
                workflow,
                state,
                archive_directory,
                observed_at,
            )
            print(
                "Archived {} and started its retention period.".format(name)
            )
            continue
        metadata, first_observed_at = read_cleanup_metadata(
            metadata_path, workflow, state
        )
        eligible_at = first_observed_at + retention
        if observed_at < eligible_at:
            print(
                "Retained {} until {}.".format(name, eligible_at.isoformat())
            )
            continue
        if metadata["exit_status"] != 0 and name != acknowledged_session:
            print(
                "Retained {}: failed or unknown exit requires acknowledgement."
                .format(name)
            )
            continue
        if not apply:
            print("Would remove archived tmux session {}.".format(name))
            continue
        current_states = workflow_pane_states(executable, workflow, session=name)
        if len(current_states) != 1:
            print(
                "Retained {}: exact pane state could not be reconfirmed.".format(name)
            )
            continue
        current_state = current_states[0]
        if current_state != state or not current_state["pane_dead"]:
            print("Retained {}: pane state changed during cleanup.".format(name))
            continue
        tmux_command(executable, "kill-session", "-t", name)
        print("Removed archived tmux session {}.".format(name))
    if apply and unacknowledged_failures:
        print(
            "Cleanup retained {} unacknowledged failed session(s).".format(
                unacknowledged_failures
            ),
            file=sys.stderr,
        )
        return 2
    return 0


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
    if arguments.operation == "cleanup":
        return cleanup_sessions(
            arguments.workflow,
            arguments.working_directory,
            apply=arguments.apply,
            acknowledge_failures=arguments.acknowledge_failures,
            retention_hours=arguments.retention_hours,
            session=arguments.session,
        )
    raise RuntimeError("Unsupported tmux batch operation.")


if __name__ == "__main__":
    raise SystemExit(main())
