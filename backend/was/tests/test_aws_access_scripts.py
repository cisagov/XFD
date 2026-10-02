"""Tests for the cross-platform WAS EC2 access scripts."""

# Standard Python Libraries
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch

SCRIPT_DIRECTORY = Path(__file__).resolve().parents[1] / "scripts" / "awsAccessScripts"
sys.path.insert(0, str(SCRIPT_DIRECTORY))

# Third-Party Libraries
# First-Party Libraries
import aws_access_common
import checkAccessorWAS
import screenConnectAccessorWAS
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


class TunnelSupervisorTests(unittest.TestCase):
    """Validate that recorded PIDs are bound to the managed tunnel identity."""

    def test_process_identity_requires_matching_script_and_token(self) -> None:
        """Reject a reused PID even when it runs the same starter script."""
        tunnel = screenConnectAccessorWAS.ManagedTunnel(1234, "expected-token")
        starter_path = str(
            Path(screenConnectAccessorWAS.__file__).resolve().parent
            / "startAccessorWAS.py"
        )

        with patch.object(
            screenConnectAccessorWAS,
            "process_is_running",
            return_value=True,
        ), patch.object(
            screenConnectAccessorWAS,
            "process_arguments",
            return_value=[
                sys.executable,
                starter_path,
                "--managed-tunnel-token=another-token",
            ],
        ):
            self.assertFalse(
                screenConnectAccessorWAS.process_matches_managed_tunnel(tunnel)
            )

        with patch.object(
            screenConnectAccessorWAS,
            "process_is_running",
            return_value=True,
        ), patch.object(
            screenConnectAccessorWAS,
            "process_arguments",
            return_value=[
                sys.executable,
                starter_path,
                "--managed-tunnel-token=expected-token",
            ],
        ):
            self.assertTrue(
                screenConnectAccessorWAS.process_matches_managed_tunnel(tunnel)
            )

    def test_stop_refuses_unrelated_live_pid(self) -> None:
        """Do not signal a live process whose identity does not match the record."""
        with tempfile.TemporaryDirectory() as directory:
            pid_path = Path(directory) / "tunnel.pid"
            pid_path.write_text(
                json.dumps({"process_id": 1234, "token": "expected-token"}),
                encoding="utf-8",
            )
            with patch.object(
                screenConnectAccessorWAS,
                "TUNNEL_PID_PATH",
                pid_path,
            ), patch.object(
                screenConnectAccessorWAS,
                "process_matches_managed_tunnel",
                return_value=False,
            ), patch.object(
                screenConnectAccessorWAS,
                "process_is_running",
                return_value=True,
            ), patch.object(
                screenConnectAccessorWAS.os,
                "killpg",
            ) as mock_kill_process_group, patch.object(
                screenConnectAccessorWAS,
                "write_output",
            ) as mock_write_output:
                screenConnectAccessorWAS.stop_managed_tunnel()

        mock_kill_process_group.assert_not_called()
        mock_write_output.assert_called_once()
        self.assertFalse(pid_path.exists())

    def test_start_records_token_used_by_child_process(self) -> None:
        """Persist the same random token supplied to the detached starter."""
        with tempfile.TemporaryDirectory() as directory:
            state_directory = Path(directory)
            pid_path = state_directory / "tunnel.pid"
            log_path = state_directory / "tunnel.log"
            process = Mock(pid=4321)
            with patch.object(
                screenConnectAccessorWAS,
                "TUNNEL_PID_PATH",
                pid_path,
            ), patch.object(
                screenConnectAccessorWAS,
                "TUNNEL_LOG_PATH",
                log_path,
            ), patch.object(
                screenConnectAccessorWAS,
                "ensure_state_directory",
                return_value=state_directory,
            ), patch.object(
                screenConnectAccessorWAS,
                "detached_process_flags",
                return_value=(True, 0),
            ), patch.object(
                screenConnectAccessorWAS.secrets,
                "token_hex",
                return_value="launch-token",
            ), patch.object(
                screenConnectAccessorWAS.subprocess,
                "Popen",
                return_value=process,
            ) as mock_popen:
                result = screenConnectAccessorWAS.start_managed_tunnel()

            state = json.loads(pid_path.read_text(encoding="utf-8"))
            state_mode = pid_path.stat().st_mode & 0o777

        self.assertIs(result, process)
        self.assertEqual(
            state,
            {"process_id": 4321, "token": "launch-token"},
        )
        self.assertEqual(state_mode, 0o600)
        self.assertIn(
            "--managed-tunnel-token=launch-token",
            mock_popen.call_args.args[0],
        )


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
