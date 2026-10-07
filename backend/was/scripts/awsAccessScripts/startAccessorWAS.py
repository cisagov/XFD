#!/usr/bin/env python3
"""Register a temporary SSH key and run the WAS SSM port-forwarding session."""

# Standard Python Libraries
import subprocess  # nosec B404

# Third-Party Libraries
# Local Libraries
from aws_access_common import (
    LOCAL_SSH_PORT,
    PUBLIC_KEY_PATH,
    REMOTE_SSH_PORT,
    REMOTE_USER,
    aws_command,
    require_instance_id,
    run_checked,
    write_output,
)


def get_availability_zone(instance_id: str) -> str:
    """Return the availability zone containing the WAS EC2 instance."""
    availability_zone = run_checked(
        aws_command(
            [
                "ec2",
                "describe-instances",
                "--instance-ids",
                instance_id,
                "--query",
                "Reservations[0].Instances[0].Placement.AvailabilityZone",
                "--output",
                "text",
            ]
        ),
        capture_output=True,
    )
    if not availability_zone or availability_zone == "None":
        raise RuntimeError("Unable to determine the WAS availability zone.")
    return availability_zone


def send_temporary_public_key(instance_id: str, availability_zone: str) -> None:
    """Register the configured public key through EC2 Instance Connect."""
    if not PUBLIC_KEY_PATH.is_file():
        raise FileNotFoundError(
            "WAS SSH public key was not found at {}.".format(PUBLIC_KEY_PATH)
        )
    public_key = PUBLIC_KEY_PATH.read_text(encoding="utf-8").strip()
    if not public_key:
        raise RuntimeError("The WAS SSH public key is empty.")
    run_checked(
        aws_command(
            [
                "ec2-instance-connect",
                "send-ssh-public-key",
                "--instance-id",
                instance_id,
                "--availability-zone",
                availability_zone,
                "--instance-os-user",
                REMOTE_USER,
                "--ssh-public-key",
                public_key,
            ]
        )
    )


def start_port_forwarding_session(instance_id: str) -> int:
    """Run the blocking Session Manager SSH port-forwarding session."""
    parameters = '{{"portNumber":["{}"],"localPortNumber":["{}"]}}'.format(
        REMOTE_SSH_PORT,
        LOCAL_SSH_PORT,
    )
    command = aws_command(
        [
            "ssm",
            "start-session",
            "--target",
            instance_id,
            "--document-name",
            "AWS-StartPortForwardingSession",
            "--parameters",
            parameters,
        ]
    )
    return subprocess.call(command)  # nosec B603


def main() -> int:
    """Prepare the temporary key and maintain the SSM tunnel process."""
    try:
        instance_id = require_instance_id()
        availability_zone = get_availability_zone(instance_id)
        send_temporary_public_key(instance_id, availability_zone)
        return start_port_forwarding_session(instance_id)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as error:
        write_output(
            "Unable to start the WAS SSM tunnel: {}".format(error),
            error=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
