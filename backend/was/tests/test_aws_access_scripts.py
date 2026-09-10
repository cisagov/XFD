"""Tests for the cross-platform WAS EC2 access scripts."""

# Standard Python Libraries
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import call, patch

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1] / "scripts" / "awsAccessScripts"
sys.path.insert(0, str(SCRIPT_DIRECTORY))

# Third-Party Libraries
# First-Party Libraries
import aws_access_common
import checkAccessorWAS
import sshConnectWAS
import startAccessorWAS


class AwsAccessCommonTests(unittest.TestCase):
    """Validate shared AWS command construction."""

    @patch("aws_access_common.require_command", return_value="aws")
    def test_aws_command_adds_profile_and_region(self, mock_require_command) -> None:
        """Apply the configured AWS execution context to every command."""
        command = aws_access_common.aws_command(["ec2", "describe-instances"])

        self.assertEqual(
            command,
            [
                "aws",
                "ec2",
                "describe-instances",
                "--profile",
                aws_access_common.AWS_PROFILE,
                "--region",
                aws_access_common.AWS_REGION,
            ],
        )
        mock_require_command.assert_called_once_with("aws")


class StartAccessorTests(unittest.TestCase):
    """Validate key registration and SSM command preparation."""

    @patch("startAccessorWAS.run_checked", return_value="us-east-1a")
    def test_get_availability_zone_queries_instance(self, mock_run_checked) -> None:
        """Read the target availability zone before sending the SSH key."""
        availability_zone = startAccessorWAS.get_availability_zone("i-example")

        self.assertEqual(availability_zone, "us-east-1a")
        self.assertIn("i-example", mock_run_checked.call_args.args[0])

    @patch("startAccessorWAS.run_checked")
    def test_send_temporary_public_key_uses_file_contents(
        self,
        mock_run_checked,
    ) -> None:
        """Pass the public key value without platform-specific file URLs."""
        with tempfile.TemporaryDirectory() as directory:
            public_key_path = Path(directory) / "accessor_rsa.pub"
            public_key_path.write_text("ssh-rsa public-key-value", encoding="utf-8")
            with patch.object(startAccessorWAS, "PUBLIC_KEY_PATH", public_key_path):
                startAccessorWAS.send_temporary_public_key(
                    "i-example",
                    "us-east-1a",
                )

        command = mock_run_checked.call_args.args[0]
        self.assertIn("ssh-rsa public-key-value", command)
        self.assertIn("i-example", command)


class CheckAccessorTests(unittest.TestCase):
    """Validate EC2 startup state handling."""

    @patch("checkAccessorWAS.time.sleep")
    @patch("checkAccessorWAS.start_instance")
    @patch(
        "checkAccessorWAS.get_instance_state",
        side_effect=["stopping", "stopped", "pending", "running"],
    )
    def test_waits_for_stopping_instance_then_starts_it(
        self,
        mock_get_state,
        mock_start_instance,
        mock_sleep,
    ) -> None:
        """Start an instance after an in-progress stop reaches stopped."""
        checkAccessorWAS.ensure_instance_running("i-example")

        mock_start_instance.assert_called_once_with("i-example")
        self.assertEqual(mock_get_state.call_count, 4)
        self.assertEqual(mock_sleep.call_args_list, [call(5), call(5), call(5)])


class SshConnectTests(unittest.TestCase):
    """Validate portable OpenSSH command construction."""

    @patch("sshConnectWAS.require_command", return_value="ssh")
    def test_build_ssh_command_uses_configured_key_and_port(
        self,
        mock_require_command,
    ) -> None:
        """Build the same SSH connection without relying on a shell script."""
        with tempfile.TemporaryDirectory() as directory:
            private_key_path = Path(directory) / "accessor_rsa"
            private_key_path.write_text("private-key-placeholder", encoding="utf-8")
            with patch.object(sshConnectWAS, "PRIVATE_KEY_PATH", private_key_path):
                command = sshConnectWAS.build_ssh_command()

        self.assertEqual(command[0], "ssh")
        self.assertIn(str(aws_access_common.LOCAL_SSH_PORT), command)
        self.assertIn(
            "{}@{}".format(
                aws_access_common.REMOTE_USER,
                aws_access_common.LOCAL_SSH_HOST,
            ),
            command,
        )
        mock_require_command.assert_called_once_with("ssh")


if __name__ == "__main__":
    unittest.main()
