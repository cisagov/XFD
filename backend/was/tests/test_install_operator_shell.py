"""Tests for installing the tracked WAS operator shell configuration."""

# Standard Python Libraries
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "install_operator_shell.py"
)
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "install_operator_shell",
    SCRIPT_PATH,
)
if SCRIPT_SPEC is None or SCRIPT_SPEC.loader is None:
    raise RuntimeError("Unable to load the operator shell installer.")
install_operator_shell = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(install_operator_shell)


class InstallOperatorShellTests(unittest.TestCase):
    """Keep Bash configuration installation guarded and repeatable."""

    def create_files(self, root: Path) -> tuple[Path, Path, Path]:
        """Create valid source, target, and backup paths for one test."""
        source_path = root / "was-operator-shell.sh"
        source_path.write_text("alias cdwas='cd /tmp'\n", encoding="utf-8")
        bashrc_path = root / ".bashrc"
        bashrc_path.write_text("alias ll='ls -al'\n", encoding="utf-8")
        backup_directory = root / "backups"
        return source_path, bashrc_path, backup_directory

    def test_preview_does_not_modify_bashrc(self) -> None:
        """Leave the target and backup directory untouched during preview."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, bashrc_path, backup_directory = self.create_files(root)
            original_contents = bashrc_path.read_text(encoding="utf-8")

            result = install_operator_shell.install_loader(
                source_path,
                bashrc_path,
                backup_directory,
                apply=False,
            )

            self.assertIsNone(result)
            self.assertEqual(bashrc_path.read_text(encoding="utf-8"), original_contents)
            self.assertFalse(backup_directory.exists())

    def test_apply_appends_once_and_creates_private_backup(self) -> None:
        """Append one loader atomically while preserving the prior target."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, bashrc_path, backup_directory = self.create_files(root)
            original_contents = bashrc_path.read_text(encoding="utf-8")

            backup_path = install_operator_shell.install_loader(
                source_path,
                bashrc_path,
                backup_directory,
                apply=True,
            )

            self.assertIsNotNone(backup_path)
            assert backup_path is not None
            self.assertEqual(backup_path.read_text(encoding="utf-8"), original_contents)
            self.assertEqual(backup_path.stat().st_mode & 0o777, 0o600)
            installed_contents = bashrc_path.read_text(encoding="utf-8")
            self.assertTrue(
                install_operator_shell.loader_is_installed(installed_contents)
            )
            self.assertTrue(
                installed_contents.rstrip().endswith(install_operator_shell.LOADER_END)
            )

            second_result = install_operator_shell.install_loader(
                source_path,
                bashrc_path,
                backup_directory,
                apply=True,
            )

            self.assertIsNone(second_result)
            self.assertEqual(
                bashrc_path.read_text(encoding="utf-8").count(
                    install_operator_shell.LOADER_START
                ),
                1,
            )
            self.assertEqual(len(list(backup_directory.iterdir())), 1)

    def test_partial_loader_requires_manual_review(self) -> None:
        """Refuse to append when a partial managed block already exists."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path, bashrc_path, backup_directory = self.create_files(root)
            bashrc_path.write_text(
                "{}\n".format(install_operator_shell.LOADER_START),
                encoding="utf-8",
            )

            with self.assertRaises(RuntimeError):
                install_operator_shell.install_loader(
                    source_path,
                    bashrc_path,
                    backup_directory,
                    apply=True,
                )

            self.assertFalse(backup_directory.exists())

    def test_tracked_fragment_uses_named_environment_without_env_file(self) -> None:
        """Keep shell setup on the named environment without loading secrets."""
        fragment_path = (
            Path(__file__).resolve().parents[1] / "config" / "was-operator-shell.sh"
        )
        contents = fragment_path.read_text(encoding="utf-8")

        self.assertIn("was_reporting/was_reporting", contents)
        self.assertIn('source "$WAS_VIRTUAL_ENV/bin/activate"', contents)
        self.assertNotIn(".env", contents)


if __name__ == "__main__":
    unittest.main()
