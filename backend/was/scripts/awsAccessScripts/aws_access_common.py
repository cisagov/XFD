"""Shared configuration and subprocess helpers for WAS AWS access scripts."""

# Standard Python Libraries
import os
from pathlib import Path
import shutil
import socket
import subprocess  # nosec B404
import sys
from typing import Sequence

AWS_PROFILE = os.getenv("WAS_AWS_PROFILE", "default")
AWS_REGION = os.getenv("WAS_AWS_REGION", "us-east-1")
INSTANCE_ID_VARIABLE = "INSTANCE_ID_WAS"
LOCAL_SSH_HOST = "127.0.0.1"
LOCAL_SSH_PORT = int(os.getenv("WAS_LOCAL_SSH_PORT", "7777"))
REMOTE_SSH_PORT = 22
REMOTE_USER = os.getenv("WAS_EC2_USER", "ubuntu")
STATE_DIRECTORY = Path.home() / ".was-access"
TUNNEL_PID_PATH = STATE_DIRECTORY / "tunnel.pid"
TUNNEL_LOG_PATH = STATE_DIRECTORY / "tunnel.log"
PRIVATE_KEY_PATH = Path(
    os.getenv("WAS_SSH_PRIVATE_KEY", str(Path.home() / ".ssh" / "accessor_rsa"))
).expanduser()
PUBLIC_KEY_PATH = Path(
    os.getenv(
        "WAS_SSH_PUBLIC_KEY",
        str(Path.home() / ".ssh" / "accessor_rsa.pub"),
    )
).expanduser()


def require_command(command_name: str) -> str:
    """Return an executable path or raise a clear prerequisite error."""
    executable = shutil.which(command_name)
    if executable is None:
        raise FileNotFoundError(
            "Required command '{}' was not found on PATH.".format(command_name)
        )
    return executable


def require_instance_id() -> str:
    """Return the configured WAS EC2 instance ID."""
    instance_id = os.getenv(INSTANCE_ID_VARIABLE, "").strip()
    if not instance_id:
        raise RuntimeError("{} is not set.".format(INSTANCE_ID_VARIABLE))
    return instance_id


def aws_command(service_arguments: Sequence[str]) -> list[str]:
    """Build an AWS CLI command using the configured profile and region."""
    return [
        require_command("aws"),
        *service_arguments,
        "--profile",
        AWS_PROFILE,
        "--region",
        AWS_REGION,
    ]


def run_checked(command: Sequence[str], capture_output: bool = False) -> str:
    """Run a command and return stripped standard output when requested."""
    result = subprocess.run(  # nosec B603
        list(command),
        check=True,
        capture_output=capture_output,
        text=True,
    )
    return result.stdout.strip() if capture_output else ""


def write_output(message: str, error: bool = False) -> None:
    """Write one user-facing line to the requested standard stream."""
    stream = sys.stderr if error else sys.stdout
    stream.write("{}\n".format(message))
    stream.flush()


def local_port_is_open(
    host: str = LOCAL_SSH_HOST,
    port: int = LOCAL_SSH_PORT,
    timeout_seconds: float = 0.5,
) -> bool:
    """Return whether a TCP listener accepts connections on the local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(timeout_seconds)
        return connection.connect_ex((host, port)) == 0


def ensure_state_directory() -> Path:
    """Create and return the private directory used for tunnel state."""
    STATE_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    return STATE_DIRECTORY
