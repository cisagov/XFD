#!/usr/bin/env python3
"""Start and supervise a detached, cross-platform WAS SSM tunnel."""

# Standard Python Libraries
from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import shlex
import signal
import subprocess  # nosec B404
import sys
import time

# Third-Party Libraries
# Local Libraries
from aws_access_common import (
    LOCAL_SSH_PORT,
    TUNNEL_LOG_PATH,
    TUNNEL_PID_PATH,
    ensure_state_directory,
    local_port_is_open,
    require_command,
    write_output,
)

TUNNEL_READY_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ManagedTunnel:
    """Identity recorded for a tunnel process started by this supervisor."""

    process_id: int
    token: str


def read_managed_tunnel() -> ManagedTunnel | None:
    """Return the recorded tunnel identity when its state is well formed."""
    if not TUNNEL_PID_PATH.is_file():
        return None
    try:
        state = json.loads(TUNNEL_PID_PATH.read_text(encoding="utf-8"))
        process_id = int(state["process_id"])
        token = state["token"]
        if process_id < 1 or not isinstance(token, str) or not token:
            raise ValueError("Invalid managed tunnel identity.")
        return ManagedTunnel(process_id=process_id, token=token)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        TUNNEL_PID_PATH.unlink(missing_ok=True)
        return None


def process_is_running(process_id: int) -> bool:
    """Return whether a process currently exists."""
    try:
        os.kill(process_id, 0)
    except OSError:
        return False
    return True


def process_arguments(process_id: int) -> list[str]:
    """Return process arguments without invoking a command shell."""
    proc_command_line = Path("/proc") / str(process_id) / "cmdline"
    if proc_command_line.is_file():
        return [
            argument.decode("utf-8", errors="replace")
            for argument in proc_command_line.read_bytes().split(b"\0")
            if argument
        ]
    if os.name == "nt":
        command = [
            require_command("powershell"),
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-CimInstance Win32_Process -Filter 'ProcessId = {}').CommandLine".format(
                process_id
            ),
        ]
        result = subprocess.run(  # nosec B603
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        return shlex.split(result.stdout.strip(), posix=False) if result.stdout else []
    result = subprocess.run(  # nosec B603
        [require_command("ps"), "-p", str(process_id), "-o", "command="],
        check=False,
        capture_output=True,
        text=True,
    )
    return shlex.split(result.stdout.strip()) if result.stdout else []


def process_matches_managed_tunnel(tunnel: ManagedTunnel) -> bool:
    """Return whether the live PID has this supervisor's script and launch token."""
    if not process_is_running(tunnel.process_id):
        return False
    expected_script = str(
        (Path(__file__).resolve().parent / "startAccessorWAS.py").resolve()
    )
    expected_token = "--managed-tunnel-token={}".format(tunnel.token)
    arguments = process_arguments(tunnel.process_id)
    return expected_script in arguments and expected_token in arguments


def stop_managed_tunnel() -> None:
    """Stop a recorded tunnel only after validating its live process identity."""
    tunnel = read_managed_tunnel()
    if tunnel is None:
        return
    if process_matches_managed_tunnel(tunnel):
        if os.name == "nt":
            subprocess.run(  # nosec B603
                [
                    require_command("taskkill"),
                    "/PID",
                    str(tunnel.process_id),
                    "/T",
                    "/F",
                ],
                check=False,
                capture_output=True,
            )
        else:
            try:
                os.killpg(tunnel.process_id, signal.SIGTERM)
            except ProcessLookupError:
                pass
    elif process_is_running(tunnel.process_id):
        write_output(
            "Recorded tunnel PID {} belongs to another process. Refusing to "
            "terminate it.".format(tunnel.process_id),
            error=True,
        )
    TUNNEL_PID_PATH.unlink(missing_ok=True)


def wait_for_port_to_close(timeout_seconds: int = 10) -> None:
    """Wait for the previous managed tunnel to release the local SSH port."""
    deadline = time.monotonic() + timeout_seconds
    while local_port_is_open() and time.monotonic() < deadline:
        time.sleep(1)
    if local_port_is_open():
        raise RuntimeError(
            "Local port {} remains occupied. Refusing to terminate an unknown "
            "process.".format(LOCAL_SSH_PORT)
        )


def detached_process_flags() -> tuple[bool, int]:
    """Return platform-specific subprocess detachment options."""
    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        return False, creation_flags
    return True, 0


def start_managed_tunnel() -> subprocess.Popen:
    """Launch the tunnel starter with output written to a persistent log."""
    ensure_state_directory()
    starter_path = str(Path(__file__).resolve().parent / "startAccessorWAS.py")
    tunnel_token = secrets.token_hex(16)
    start_new_session, creation_flags = detached_process_flags()
    with TUNNEL_LOG_PATH.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(  # nosec B603
            [
                sys.executable,
                starter_path,
                "--managed-tunnel-token={}".format(tunnel_token),
            ],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            start_new_session=start_new_session,
        )
    try:
        state_descriptor = os.open(
            TUNNEL_PID_PATH,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        with os.fdopen(state_descriptor, "w", encoding="utf-8") as state_file:
            json.dump({"process_id": process.pid, "token": tunnel_token}, state_file)
    except OSError as error:
        process.terminate()
        raise RuntimeError("Unable to record the managed tunnel identity.") from error
    return process


def print_log_tail(maximum_lines: int = 20) -> None:
    """Print recent tunnel diagnostics without requiring platform utilities."""
    if not TUNNEL_LOG_PATH.is_file():
        return
    lines = TUNNEL_LOG_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()
    if lines:
        write_output("Recent tunnel log output:", error=True)
        for line in lines[-maximum_lines:]:
            write_output(line, error=True)


def main() -> int:
    """Replace a prior managed tunnel and wait for the new listener."""
    try:
        stop_managed_tunnel()
        wait_for_port_to_close()
        process = start_managed_tunnel()
        deadline = time.monotonic() + TUNNEL_READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if local_port_is_open():
                write_output(
                    "The WAS SSH tunnel is listening on local port {}.".format(
                        LOCAL_SSH_PORT
                    )
                )
                write_output("Tunnel log: {}".format(TUNNEL_LOG_PATH))
                return 0
            if process.poll() is not None:
                print_log_tail()
                raise RuntimeError("The WAS SSM tunnel process exited early.")
            time.sleep(1)
        print_log_tail()
        raise RuntimeError(
            "The WAS SSH tunnel did not become ready within {} seconds.".format(
                TUNNEL_READY_TIMEOUT_SECONDS
            )
        )
    except (FileNotFoundError, RuntimeError, subprocess.SubprocessError) as error:
        write_output(
            "Unable to prepare the WAS SSH tunnel: {}".format(error),
            error=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
