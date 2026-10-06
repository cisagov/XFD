"""Verify host software Make targets without changing the workstation."""

# Standard Python Libraries
from pathlib import Path
import subprocess
import unittest


class HostSoftwareMakefileTests(unittest.TestCase):
    """Keep the repeatable host workflow on the reviewed scripts."""

    def run_plan(self, target: str, *variables: str) -> str:
        """Return a dry-run Make plan for one host software target."""
        directory = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["make", "-n", "-C", str(directory), target] + list(variables),
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return result.stdout

    def test_capture_uses_timestamped_private_inventory(self) -> None:
        """Route capture through the host inventory script and explicit output."""
        plan = self.run_plan(
            "host-software-capture",
            "HOST_SOFTWARE_INVENTORY_DIR=/tmp/reviewed-host-inventory",
            "HOST_SOFTWARE_SINCE=2026-09-01",
        )

        self.assertIn("scripts/capture_host_packages.py", plan)
        self.assertIn('--output "/tmp/reviewed-host-inventory"', plan)
        self.assertIn('--since "2026-09-01"', plan)

    def test_preview_and_verify_use_ubuntu_2404_helper(self) -> None:
        """Keep non-mutating commands on the reviewed Ubuntu 24.04 helper."""
        preview = self.run_plan("host-software-preview")
        verify = self.run_plan("host-software-verify")

        self.assertIn("rebuild_was_host_ubuntu24.py", preview)
        self.assertNotIn("--apply", preview)
        self.assertIn("rebuild_was_host_ubuntu24.py --verify", verify)

    def test_apply_requires_explicit_make_acknowledgement(self) -> None:
        """Keep host package writes behind the established APPLY gate."""
        plan = self.run_plan("host-software-apply", "APPLY=1")

        self.assertIn('test "1" = 1', plan)
        self.assertIn("--apply --acknowledge-manual-items", plan)

    def test_shell_install_requires_explicit_make_acknowledgement(self) -> None:
        """Keep operator Bash configuration writes behind the apply gate."""
        preview = self.run_plan("host-shell-preview")
        install = self.run_plan("host-shell-install", "APPLY=1")

        self.assertIn("scripts/install_operator_shell.py", preview)
        self.assertNotIn("--apply", preview)
        self.assertIn('test "1" = 1', install)
        self.assertIn("scripts/install_operator_shell.py --apply", install)


if __name__ == "__main__":
    unittest.main()
