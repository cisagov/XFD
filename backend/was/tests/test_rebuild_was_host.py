"""Tests for the Ubuntu 22.04 WAS host rebuild helper."""

# Standard Python Libraries
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "rebuild_was_host_ubuntu22.py"
)
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "rebuild_was_host_ubuntu22",
    SCRIPT_PATH,
)
if SCRIPT_SPEC is None or SCRIPT_SPEC.loader is None:
    raise RuntimeError("Unable to load the Ubuntu 22.04 host rebuild script.")
rebuild_was_host = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(rebuild_was_host)


class RebuildWasHostTests(unittest.TestCase):
    """Keep the rebuild helper aligned with the approved Ubuntu release."""

    def test_uses_ubuntu_2204_packages_and_docker_repository(self) -> None:
        """Install the required host tools from Docker's Jammy repository."""
        self.assertIn("tmux", rebuild_was_host.APT_PACKAGES)
        self.assertIn("Suites: jammy", rebuild_was_host.DOCKER_SOURCE)
        self.assertNotIn("noble", rebuild_was_host.DOCKER_SOURCE)

    def test_check_host_accepts_ubuntu_2204_x86_64_operator(self) -> None:
        """Allow installation only on the selected Ubuntu 22.04 architecture."""
        os_release = 'ID=ubuntu\nVERSION_ID="22.04"\n'
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

    def test_check_host_rejects_ubuntu_2404(self) -> None:
        """Stop rather than installing Jammy packages on Ubuntu 24.04."""
        os_release = 'ID=ubuntu\nVERSION_ID="24.04"\n'
        with patch.object(rebuild_was_host, "Path") as mock_path:
            mock_path.return_value.read_text.return_value = os_release
            with self.assertRaises(RuntimeError) as raised:
                rebuild_was_host.check_host()

        self.assertEqual(
            str(raised.exception),
            "Installation and verification require Ubuntu 22.04.",
        )


if __name__ == "__main__":
    unittest.main()
