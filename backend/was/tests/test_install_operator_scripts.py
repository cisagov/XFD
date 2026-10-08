"""Tests for installing tracked WAS operator scripts into the operator bin path."""

# Standard Python Libraries
import importlib.util
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
import unittest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "install_operator_scripts.py"
)
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "install_operator_scripts",
    SCRIPT_PATH,
)
if SCRIPT_SPEC is None or SCRIPT_SPEC.loader is None:
    raise RuntimeError("Unable to load the operator script installer.")
install_operator_scripts = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(install_operator_scripts)


class InstallOperatorScriptsTests(unittest.TestCase):
    """Keep operator script installation guarded, repeatable, and recoverable."""

    def create_sources(self, root: Path) -> Path:
        """Create the exact allowlisted source directory for one test."""
        source_directory = root / "sources"
        source_directory.mkdir()
        for script_name in install_operator_scripts.SCRIPT_NAMES:
            (source_directory / script_name).write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' '{} test'\n".format(script_name),
                encoding="utf-8",
            )
        return source_directory

    def test_preview_does_not_create_target_or_backups(self) -> None:
        """Leave all destination paths absent during preview."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_directory = self.create_sources(root)
            target_directory = root / "bin"
            backup_root = root / "backups"

            result = install_operator_scripts.install_scripts(
                source_directory,
                target_directory,
                backup_root,
                apply=False,
            )

            self.assertIsNone(result)
            self.assertFalse(target_directory.exists())
            self.assertFalse(backup_root.exists())

    def test_apply_installs_exact_executable_scripts_idempotently(self) -> None:
        """Install every source once and leave a second application unchanged."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_directory = self.create_sources(root)
            target_directory = root / "bin"
            backup_root = root / "backups"

            first_backup = install_operator_scripts.install_scripts(
                source_directory,
                target_directory,
                backup_root,
                apply=True,
            )
            second_backup = install_operator_scripts.install_scripts(
                source_directory,
                target_directory,
                backup_root,
                apply=True,
            )

            self.assertIsNone(first_backup)
            self.assertIsNone(second_backup)
            self.assertFalse(backup_root.exists())
            for script_name in install_operator_scripts.SCRIPT_NAMES:
                source_path = source_directory / script_name
                target_path = target_directory / script_name
                self.assertEqual(target_path.read_bytes(), source_path.read_bytes())
                self.assertEqual(
                    stat.S_IMODE(target_path.stat().st_mode),
                    install_operator_scripts.INSTALL_MODE,
                )

    def test_apply_backs_up_and_replaces_existing_script(self) -> None:
        """Preserve conflicting target contents privately before replacement."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_directory = self.create_sources(root)
            target_directory = root / "bin"
            target_directory.mkdir()
            existing_target = target_directory / "updateWAS"
            existing_target.write_text("#!/bin/bash\necho old\n", encoding="utf-8")
            backup_root = root / "backups"

            backup_directory = install_operator_scripts.install_scripts(
                source_directory,
                target_directory,
                backup_root,
                apply=True,
            )

            self.assertIsNotNone(backup_directory)
            assert backup_directory is not None
            backup_path = backup_directory / "updateWAS"
            self.assertEqual(
                backup_path.read_text(encoding="utf-8"),
                "#!/bin/bash\necho old\n",
            )
            self.assertEqual(stat.S_IMODE(backup_path.stat().st_mode), 0o600)
            self.assertEqual(
                existing_target.read_bytes(),
                (source_directory / "updateWAS").read_bytes(),
            )

    def test_unexpected_source_file_requires_manual_review(self) -> None:
        """Reject scripts outside the explicit source allowlist."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_directory = self.create_sources(root)
            (source_directory / "unexpected").write_text(
                "#!/bin/bash\n", encoding="utf-8"
            )

            with self.assertRaises(RuntimeError):
                install_operator_scripts.install_scripts(
                    source_directory,
                    root / "bin",
                    root / "backups",
                    apply=False,
                )

    def test_symlinked_target_requires_manual_review(self) -> None:
        """Reject an existing destination symlink instead of replacing its referent."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_directory = self.create_sources(root)
            target_directory = root / "bin"
            target_directory.mkdir()
            referent = root / "referent"
            referent.write_text("#!/bin/bash\n", encoding="utf-8")
            (target_directory / "getcloneBranch").symlink_to(referent)

            with self.assertRaises(RuntimeError):
                install_operator_scripts.install_scripts(
                    source_directory,
                    target_directory,
                    root / "backups",
                    apply=False,
                )


if __name__ == "__main__":
    unittest.main()
