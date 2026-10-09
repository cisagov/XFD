"""Tests for the Ubuntu 24.04 WAS host rebuild helper."""

# Standard Python Libraries
import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import call, patch
import zipfile

SCRIPTS_DIRECTORY = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIRECTORY))
SCRIPT_PATH = SCRIPTS_DIRECTORY / "rebuild_was_host_ubuntu24.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "rebuild_was_host_ubuntu24",
    SCRIPT_PATH,
)
if SCRIPT_SPEC is None or SCRIPT_SPEC.loader is None:
    raise RuntimeError("Unable to load the Ubuntu 24.04 host rebuild script.")
rebuild_was_host = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(rebuild_was_host)


class RebuildWasHostTests(unittest.TestCase):
    """Keep the rebuild helper aligned with the approved Ubuntu release."""

    def test_uses_ubuntu_2404_packages_and_docker_repository(self) -> None:
        """Load required packages and Docker suite from the reviewed manifest."""
        self.assertIn("tmux", rebuild_was_host.APT_PACKAGES)
        self.assertIn("Suites: noble", rebuild_was_host.DOCKER_SOURCE)
        self.assertNotIn("jammy", rebuild_was_host.DOCKER_SOURCE)
        self.assertEqual(
            rebuild_was_host.APT_PACKAGES,
            rebuild_was_host.SOFTWARE_MANIFEST.apt_packages,
        )
        self.assertNotIn("awscli", rebuild_was_host.APT_PACKAGES)

    def test_uses_checksum_pinned_aws_cli_v2(self) -> None:
        """Install the reviewed AWS CLI release independently of Ubuntu APT."""
        self.assertEqual(rebuild_was_host.AWS_CLI_VERSION, "2.37.4")
        self.assertEqual(len(rebuild_was_host.AWS_CLI_SHA256), 64)
        self.assertIn(
            "awscli-exe-linux-x86_64-2.37.4.zip",
            rebuild_was_host.AWS_CLI_URL,
        )

    def test_parses_aws_cli_version_output(self) -> None:
        """Read the stable AWS CLI version field without matching other text."""
        version = rebuild_was_host.parse_aws_cli_version(
            "aws-cli/2.37.4 Python/3.14.6 Linux/example exe/x86_64.ubuntu.24"
        )

        self.assertEqual(version, "2.37.4")

    def test_rejects_unsafe_aws_cli_archive_path(self) -> None:
        """Stop ZIP extraction before a member can escape the temporary root."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = root / "aws-cli.zip"
            destination = root / "extracted"
            destination.mkdir()
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside", "unsafe")

            with self.assertRaises(RuntimeError):
                rebuild_was_host.extract_zip_archive(archive_path, destination)

        self.assertFalse((root / "outside").exists())

    def test_grants_current_operator_docker_group_access(self) -> None:
        """Configure only the invoking operator for root-equivalent Docker access."""
        with patch.object(
            rebuild_was_host,
            "operator_identity",
            return_value=("was-operator", 1000),
        ), patch.object(
            rebuild_was_host,
            "docker_group_membership",
            side_effect=(False, True),
        ), patch.object(
            rebuild_was_host.grp,
            "getgrnam",
            return_value=object(),
        ), patch.object(
            rebuild_was_host,
            "command",
        ) as mock_command:
            changed = rebuild_was_host.grant_docker_operator_access()

        self.assertTrue(changed)
        self.assertEqual(
            mock_command.call_args,
            call(
                [
                    "sudo",
                    "usermod",
                    "--append",
                    "--groups",
                    "docker",
                    "was-operator",
                ]
            ),
        )

    def test_docker_verification_requires_configuration_and_live_access(self) -> None:
        """Fail verification when Docker access is absent or the login is stale."""
        docker_error = rebuild_was_host.subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "info"],
        )
        with patch.object(
            rebuild_was_host,
            "operator_identity",
            return_value=("was-operator", 1000),
        ), patch.object(
            rebuild_was_host,
            "docker_group_membership",
            return_value=False,
        ), patch.object(
            rebuild_was_host,
            "command",
            side_effect=docker_error,
        ):
            failures = rebuild_was_host.docker_access_failures()

        self.assertEqual(len(failures), 2)
        self.assertIn("not configured", failures[0])
        self.assertIn("cannot access", failures[1])

    def test_check_host_accepts_ubuntu_2404_x86_64_operator(self) -> None:
        """Allow installation only on the selected Ubuntu 24.04 architecture."""
        os_release = 'ID=ubuntu\nVERSION_ID="24.04"\n'
        with patch.object(rebuild_was_host, "Path") as mock_path, patch.object(
            rebuild_was_host.platform,
            "machine",
            return_value="x86_64",
        ), patch.object(
            rebuild_was_host.os,
            "geteuid",
            return_value=1000,
        ), patch.dict(
            rebuild_was_host.os.environ,
            {},
            clear=True,
        ):
            mock_path.return_value.read_text.return_value = os_release
            rebuild_was_host.check_host()

    def test_check_host_rejects_ubuntu_2204(self) -> None:
        """Stop rather than installing Noble packages on Ubuntu 22.04."""
        os_release = 'ID=ubuntu\nVERSION_ID="22.04"\n'
        with patch.object(rebuild_was_host, "Path") as mock_path:
            mock_path.return_value.read_text.return_value = os_release
            with self.assertRaises(RuntimeError) as raised:
                rebuild_was_host.check_host()

        self.assertEqual(
            str(raised.exception),
            "Installation and verification require Ubuntu 24.04.",
        )

    def test_accepts_signed_noble_docker_list_source(self) -> None:
        """Accept the Docker source created by Terraform user data."""
        contents = (
            "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] "
            "https://download.docker.com/linux/ubuntu noble stable\n"
        )

        self.assertTrue(rebuild_was_host.docker_source_is_compatible(contents))

    def test_accepts_signed_noble_docker_deb822_source(self) -> None:
        """Accept the helper's signed Noble Deb822 repository format."""
        self.assertTrue(
            rebuild_was_host.docker_source_is_compatible(rebuild_was_host.DOCKER_SOURCE)
        )

    def test_rejects_unsigned_noble_docker_source(self) -> None:
        """Reject a Noble repository that has no scoped signing key."""
        contents = (
            "deb [arch=amd64] https://download.docker.com/linux/ubuntu "
            "noble stable\n"
        )

        self.assertFalse(rebuild_was_host.docker_source_is_compatible(contents))

    def test_rejects_jammy_docker_source(self) -> None:
        """Reject an existing source for the previous Ubuntu release."""
        contents = (
            "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] "
            "https://download.docker.com/linux/ubuntu jammy stable\n"
        )

        self.assertFalse(rebuild_was_host.docker_source_is_compatible(contents))


if __name__ == "__main__":
    unittest.main()
