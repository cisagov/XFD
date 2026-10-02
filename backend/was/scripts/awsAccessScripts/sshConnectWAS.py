#!/usr/bin/env python3
"""Open an interactive SSH session through the local WAS SSM tunnel."""

# Standard Python Libraries
import subprocess  # nosec B404

# Third-Party Libraries
# Local Libraries
from aws_access_common import (
    LOCAL_SSH_HOST,
    LOCAL_SSH_PORT,
    PRIVATE_KEY_PATH,
    REMOTE_USER,
    local_port_is_open,
    require_command,
    write_output,
)


def build_ssh_command() -> list[str]:
    """Build the OpenSSH command for the local WAS tunnel."""
    if not PRIVATE_KEY_PATH.is_file():
        raise FileNotFoundError(
            "WAS SSH private key was not found at {}.".format(PRIVATE_KEY_PATH)
        )
    return [
        require_command("ssh"),
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "HostKeyAlgorithms=+ssh-ed25519,ecdsa-sha2-nistp256",
        "-i",
        str(PRIVATE_KEY_PATH),
        "-p",
        str(LOCAL_SSH_PORT),
        "{}@{}".format(REMOTE_USER, LOCAL_SSH_HOST),
    ]


def main() -> int:
    """Validate the local tunnel and start the interactive SSH client."""
    try:
        if not local_port_is_open():
            raise RuntimeError(
                "No WAS tunnel is listening on local port {}. Run "
                "checkAccessorWAS.py first.".format(LOCAL_SSH_PORT)
            )
        return subprocess.call(build_ssh_command())  # nosec B603
    except (FileNotFoundError, RuntimeError) as error:
        write_output(
            "Unable to connect to the WAS instance: {}".format(error),
            error=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
