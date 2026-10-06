"""Tests for the repeatable WAS host software inventory manifest."""

# Standard Python Libraries
import importlib.util
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

SCRIPTS_DIRECTORY = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIRECTORY))

CAPTURE_PATH = SCRIPTS_DIRECTORY / "capture_host_packages.py"
CAPTURE_SPEC = importlib.util.spec_from_file_location(
    "capture_host_packages",
    CAPTURE_PATH,
)
if CAPTURE_SPEC is None or CAPTURE_SPEC.loader is None:
    raise RuntimeError("Unable to load the host software capture script.")
capture_host_packages = importlib.util.module_from_spec(CAPTURE_SPEC)
CAPTURE_SPEC.loader.exec_module(capture_host_packages)


class HostSoftwareInventoryTests(unittest.TestCase):
    """Keep inventory comparison aligned with the reviewed manifest."""

    def test_manifest_targets_ubuntu_2404_and_required_tools(self) -> None:
        """Load the committed Ubuntu release and required operator tools."""
        manifest = capture_host_packages.SOFTWARE_MANIFEST

        self.assertEqual(manifest.os_id, "ubuntu")
        self.assertEqual(manifest.os_version, "24.04")
        self.assertEqual(manifest.docker_suite, "noble")
        self.assertIn("tmux", manifest.apt_packages)
        self.assertNotIn("awscli", manifest.apt_packages)
        self.assertIn("docker-ce", manifest.docker_packages)
        self.assertIn("aws", {tool.name for tool in manifest.required_tools})
        self.assertEqual(manifest.aws_cli_version, "2.37.4")
        self.assertEqual(len(manifest.aws_cli_sha256), 64)

    def test_version_capture_accepts_standard_error_output(self) -> None:
        """Retain versions from tools such as AWS CLI that may use stderr."""
        completed = subprocess.CompletedProcess(
            args=["aws", "--version"],
            returncode=0,
            stdout="",
            stderr="aws-cli/2.example\n",
        )
        with patch.object(
            capture_host_packages.subprocess,
            "run",
            return_value=completed,
        ):
            version = capture_host_packages.run_version_command(
                ["aws", "--version"],
                {"PATH": "/usr/bin"},
            )

        self.assertEqual(version, "aws-cli/2.example")

    def test_executable_checksum_is_stable(self) -> None:
        """Record binary identity without copying executable contents."""
        with TemporaryDirectory() as directory:
            executable = Path(directory) / "tool"
            executable.write_bytes(b"reviewed tool\n")

            checksum = capture_host_packages.file_sha256(executable)

        self.assertEqual(
            checksum,
            "7ef6070432e4bf93d45456d2f8c77fbc8bf8b39816ee677d85705c3ec89e5902",
        )

    def test_comparison_reports_missing_and_review_candidate_software(self) -> None:
        """Separate missing requirements from extra manual package evidence."""
        manifest = capture_host_packages.SOFTWARE_MANIFEST
        packages = [
            {
                "package": manifest.apt_packages[0],
                "version": "example",
                "architecture": "amd64",
            }
        ]
        tools = [
            {
                "tool": manifest.required_tools[0].name,
                "version": "example",
                "executable": "/usr/bin/example",
                "resolved_path": "/usr/bin/example",
                "dpkg_owner": "example",
                "installation_source": "dpkg-owned",
            }
        ]

        result = capture_host_packages.compare_to_manifest(
            packages,
            [manifest.apt_packages[0], "operator-added-package"],
            tools,
            manifest,
        )

        self.assertIn("tmux", result["missing_required_packages"])
        self.assertIn("docker", result["missing_required_tools"])
        self.assertEqual(
            result["manual_packages_not_in_manifest"],
            ["operator-added-package"],
        )


if __name__ == "__main__":
    unittest.main()
