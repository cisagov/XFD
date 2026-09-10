#!/usr/bin/env python3
"""Start and supervise a detached, cross-platform WAS SSM tunnel."""

# Standard Python Libraries
import os
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


def read_managed_pid() -> int | None:
    """Return the recorded tunnel supervisor process ID when valid."""
    if not TUNNEL_PID_PATH.is_file():
        return None
    try:
        return int(TUNNEL_PID_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
        TUNNEL_PID_PATH.unlink(missing_ok=True)
        return None


def process_is_running(process_id: int) -> bool:
    """Return whether a process currently exists."""
    try:
        os.kill(process_id, 0)
    except OSError:
        return False
    return True


def stop_managed_tunnel() -> None:
    """Stop only the tunnel process recorded by this script."""
    process_id = read_managed_pid()
    if process_id is None:
        return
    if process_is_running(process_id):
        if os.name == "nt":
            subprocess.run(  # nosec B603
                [
                    require_command("taskkill"),
                    "/PID",
                    str(process_id),
                    "/T",
                    "/F",
                ],
                check=False,
                capture_output=True,
            )
        else:
            try:
                os.killpg(process_id, signal.SIGTERM)
            except ProcessLookupError:
                pass
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
    starter_path = os.path.join(os.path.dirname(__file__), "startAccessorWAS.py")
    start_new_session, creation_flags = detached_process_flags()
    with TUNNEL_LOG_PATH.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(  # nosec B603
            [sys.executable, starter_path],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            start_new_session=start_new_session,
        )
    TUNNEL_PID_PATH.write_text(str(process.pid), encoding="utf-8")
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
