#!/usr/bin/env python3
"""Preview or install the tracked WAS operator shell loader in ~/.bashrc."""

# Standard Python Libraries
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import stat
import subprocess  # nosec B404
import sys
from tempfile import NamedTemporaryFile
from typing import Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PATH = REPOSITORY_ROOT / "config" / "was-operator-shell.sh"
DEFAULT_BASHRC_PATH = Path.home() / ".bashrc"
DEFAULT_BACKUP_DIRECTORY = (
    Path.home() / ".local" / "state" / "was-host-rebuild" / "bashrc-backups"
)
BASH_PATH = Path("/bin/bash")
LOADER_START = "# BEGIN WAS OPERATOR SHELL CONFIG"
LOADER_END = "# END WAS OPERATOR SHELL CONFIG"
LOADER_SIGNATURE = (
    'WAS_SHELL_CONFIG="$HOME/code/cd_WAS_update/backend/was/config/'
    'was-operator-shell.sh"'
)
LOADER_BLOCK = """# BEGIN WAS OPERATOR SHELL CONFIG
WAS_SHELL_CONFIG="$HOME/code/cd_WAS_update/backend/was/config/was-operator-shell.sh"

if [[ -r "$WAS_SHELL_CONFIG" ]]; then
    source "$WAS_SHELL_CONFIG"
fi

unset WAS_SHELL_CONFIG
# END WAS OPERATOR SHELL CONFIG
"""


def write_output(message: str) -> None:
    """Write one user-facing line without exposing file contents."""
    sys.stdout.write("{}\n".format(message))
    sys.stdout.flush()


def validate_bash(path: Path) -> None:
    """Require a file to pass Bash syntax validation without printing it."""
    if not BASH_PATH.is_file():
        raise RuntimeError("The required /bin/bash executable is unavailable.")
    result = subprocess.run(  # nosec B603
        [str(BASH_PATH), "-n", str(path)],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError("Bash syntax validation failed for {}.".format(path.name))


def loader_is_installed(contents: str) -> bool:
    """Return whether exactly one complete managed loader block is present."""
    return (
        contents.count(LOADER_BLOCK) == 1
        and contents.count(LOADER_START) == 1
        and contents.count(LOADER_END) == 1
        and contents.count(LOADER_SIGNATURE) == 1
    )


def reject_partial_loader(contents: str) -> None:
    """Refuse partial or duplicate loader state that needs operator review."""
    if any(
        marker in contents for marker in (LOADER_START, LOADER_END, LOADER_SIGNATURE)
    ):
        raise RuntimeError(
            "The Bash configuration contains a partial or duplicate WAS loader; "
            "review it manually before retrying."
        )


def updated_bashrc(contents: str) -> str:
    """Return Bash configuration with one managed loader appended at the end."""
    if not contents:
        return LOADER_BLOCK
    separator = "\n" if contents.endswith("\n") else "\n\n"
    return "{}{}{}".format(contents, separator, LOADER_BLOCK)


def create_backup(source: Path, backup_directory: Path) -> Path:
    """Create a private timestamped backup and return its path."""
    backup_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup_directory.chmod(0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_directory / "bashrc.{}.backup".format(timestamp)
    shutil.copy2(source, backup_path)
    backup_path.chmod(0o600)
    return backup_path


def install_loader(
    source_path: Path,
    bashrc_path: Path,
    backup_directory: Path,
    apply: bool,
) -> Optional[Path]:
    """Validate, preview, or atomically append the managed Bash loader."""
    if source_path.is_symlink() or not source_path.is_file():
        raise RuntimeError("The tracked WAS shell configuration is unavailable.")
    if bashrc_path.is_symlink() or not bashrc_path.is_file():
        raise RuntimeError("The operator .bashrc must be an existing regular file.")

    validate_bash(source_path)
    validate_bash(bashrc_path)
    contents = bashrc_path.read_text(encoding="utf-8")
    if loader_is_installed(contents):
        write_output("The WAS operator shell loader is already installed once.")
        return None
    reject_partial_loader(contents)

    write_output("Source: {}".format(source_path))
    write_output("Target: {}".format(bashrc_path))
    write_output("Backup directory: {}".format(backup_directory))
    if not apply:
        write_output("PREVIEW ONLY: one managed loader would be appended.")
        return None

    target_mode = stat.S_IMODE(bashrc_path.stat().st_mode)
    temporary_path: Optional[Path] = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=bashrc_path.parent,
            prefix=".bashrc.was-",
            delete=False,
        ) as temporary_file:
            temporary_file.write(updated_bashrc(contents))
            temporary_path = Path(temporary_file.name)
        temporary_path.chmod(target_mode)
        validate_bash(temporary_path)
        backup_path = create_backup(bashrc_path, backup_directory)
        os.replace(temporary_path, bashrc_path)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    write_output("Installed one WAS loader at the end of {}.".format(bashrc_path))
    write_output("Backup: {}".format(backup_path))
    write_output("Open a new login shell to load the tracked configuration.")
    return backup_path


def main() -> int:
    """Parse explicit paths and keep writes behind the apply flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--bashrc", type=Path, default=DEFAULT_BASHRC_PATH)
    parser.add_argument(
        "--backup-directory",
        type=Path,
        default=DEFAULT_BACKUP_DIRECTORY,
    )
    arguments = parser.parse_args()

    if os.geteuid() == 0 or os.environ.get("SUDO_USER"):
        write_output("STOPPED: run as the normal EC2 operator, without sudo.")
        return 1
    try:
        install_loader(
            source_path=arguments.source,
            bashrc_path=arguments.bashrc,
            backup_directory=arguments.backup_directory,
            apply=arguments.apply,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        if isinstance(error, RuntimeError):
            write_output("STOPPED: {}".format(error))
        else:
            write_output(
                "STOPPED ({}). No automatic recovery was attempted.".format(
                    type(error).__name__
                )
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
