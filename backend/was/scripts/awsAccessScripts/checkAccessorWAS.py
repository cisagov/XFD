#!/usr/bin/env python3
"""Start the WAS EC2 instance when needed and prepare its SSH tunnel."""

# Standard Python Libraries
import logging
import os
import subprocess  # nosec B404
import sys
import time

# Third-Party Libraries
# Local Libraries
from aws_access_common import aws_command, require_instance_id, run_checked

logging.basicConfig(
    format="%(asctime)-15s %(levelname)s %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)
INSTANCE_READY_TIMEOUT_SECONDS = 300


def get_instance_state(instance_id: str) -> str:
    """Return the current EC2 instance state."""
    return run_checked(
        aws_command(
            [
                "ec2",
                "describe-instances",
                "--instance-ids",
                instance_id,
                "--query",
                "Reservations[0].Instances[0].State.Name",
                "--output",
                "text",
            ]
        ),
        capture_output=True,
    )


def start_instance(instance_id: str) -> None:
    """Request startup for a stopped WAS EC2 instance."""
    run_checked(
        aws_command(
            [
                "ec2",
                "start-instances",
                "--instance-ids",
                instance_id,
            ]
        )
    )
    LOGGER.info("WAS instance start requested.")


def launch_tunnel_supervisor() -> None:
    """Run the sibling Python tunnel supervisor and require success."""
    script_path = os.path.join(
        os.path.dirname(__file__),
        "screenConnectAccessorWAS.py",
    )
    subprocess.run([sys.executable, script_path], check=True)  # nosec B603
    LOGGER.info("The WAS SSH tunnel is ready. Run sshConnectWAS.py to connect.")


def ensure_instance_running(instance_id: str) -> None:
    """Wait through valid EC2 transitions until the instance is running."""
    deadline = time.monotonic() + INSTANCE_READY_TIMEOUT_SECONDS
    start_requested = False
    while time.monotonic() < deadline:
        instance_state = get_instance_state(instance_id)
        LOGGER.info("Current WAS instance state: %s", instance_state)
        if instance_state == "running":
            return
        if instance_state == "stopped" and not start_requested:
            start_instance(instance_id)
            start_requested = True
        elif instance_state not in {"pending", "stopped", "stopping"}:
            raise RuntimeError(
                "WAS instance is in an unsupported state: {}".format(instance_state)
            )
        time.sleep(5)
    raise TimeoutError(
        "WAS instance did not become running within {} seconds.".format(
            INSTANCE_READY_TIMEOUT_SECONDS
        )
    )


def check_vm_running() -> bool:
    """Start the WAS instance if needed, then prepare its SSH tunnel."""
    try:
        instance_id = require_instance_id()
        ensure_instance_running(instance_id)
        launch_tunnel_supervisor()
        return True
    except (
        FileNotFoundError,
        RuntimeError,
        TimeoutError,
        subprocess.CalledProcessError,
    ):
        LOGGER.exception("Unable to check or connect to the WAS instance.")
        return False


if __name__ == "__main__":
    raise SystemExit(0 if check_vm_running() else 1)
