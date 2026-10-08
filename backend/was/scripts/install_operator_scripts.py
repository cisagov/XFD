#!/usr/bin/env python3
"""Preview or install the tracked WAS operator scripts in ~/bin."""

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
from typing import Dict, List, Optional, Tuple

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIRECTORY = REPOSITORY_ROOT / "scripts" / "ec2_scripts"
DEFAULT_TARGET_DIRECTORY = Path.home() / "bin"
DEFAULT_BACKUP_ROOT = (
    Path.home() / ".local" / "state" / "was-host-rebuild" / "operator-script-backups"
)
BASH_PATH = Path("/bin/bash")
SCRIPT_NAMES = (
    "getcloneBranch",
    "refreshDailyTracker",
    "runCapacityLoadTest",
    "updateWAS",
)
INSTALL_MODE = 0o755


def write_output(message: str) -> None:
    """Write one user-facing line without exposing script contents."""
    sys.stdout.write("{}\n".format(message))
    sys.stdout.flush()


def validate_bash(path: Path) -> None:
    """Require one script to pass bounded Bash syntax validation."""
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


def validated_sources(source_directory: Path) -> List[Path]:
    """Return the exact allowlisted source scripts after structural validation."""
    if source_directory.is_symlink() or not source_directory.is_dir():
        raise RuntimeError("The tracked operator script directory is unavailable.")
    directory_entries = list(source_directory.iterdir())
    actual_names = {entry.name for entry in directory_entries}
    expected_names = set(SCRIPT_NAMES)
    if actual_names != expected_names:
        raise RuntimeError(
            "The tracked operator script directory must contain exactly: {}.".format(
                ", ".join(SCRIPT_NAMES)
            )
        )
    sources = []
    for script_name in SCRIPT_NAMES:
        source_path = source_directory / script_name
        if source_path.is_symlink() or not source_path.is_file():
            raise RuntimeError(
                "Tracked operator script {} must be a regular file.".format(script_name)
            )
        validate_bash(source_path)
        sources.append(source_path)
    return sources


def validate_target_directory(target_directory: Path) -> None:
    """Reject unsafe or foreign-owned target directory state."""
    if target_directory.is_symlink():
        raise RuntimeError("The operator script target directory cannot be a symlink.")
    if target_directory.exists():
        if not target_directory.is_dir():
            raise RuntimeError("The operator script target must be a directory.")
        if target_directory.stat().st_uid != os.getuid():
            raise RuntimeError("The operator script target is not owned by this user.")


def installation_action(source_path: Path, target_path: Path) -> str:
    """Classify one target as new, replacement, or already current."""
    if target_path.is_symlink():
        raise RuntimeError("Refusing symlinked target {}.".format(target_path.name))
    if not target_path.exists():
        return "install"
    if not target_path.is_file():
        raise RuntimeError("Target {} is not a regular file.".format(target_path.name))
    if target_path.stat().st_uid != os.getuid():
        raise RuntimeError(
            "Target {} is not owned by this user.".format(target_path.name)
        )
    target_mode = stat.S_IMODE(target_path.stat().st_mode)
    if (
        source_path.read_bytes() == target_path.read_bytes()
        and target_mode == INSTALL_MODE
    ):
        return "current"
    return "replace"


def installation_plan(
    sources: List[Path], target_directory: Path
) -> List[Tuple[Path, Path, str]]:
    """Build a complete plan before any destination changes occur."""
    plan = []
    for source_path in sources:
        target_path = target_directory / source_path.name
        plan.append(
            (
                source_path,
                target_path,
                installation_action(source_path, target_path),
            )
        )
    return plan


def create_backup_directory(backup_root: Path) -> Path:
    """Create and return a private directory for one replacement run."""
    if backup_root.is_symlink():
        raise RuntimeError("The operator script backup root cannot be a symlink.")
    backup_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not backup_root.is_dir() or backup_root.stat().st_uid != os.getuid():
        raise RuntimeError("The operator script backup root is not safely owned.")
    backup_root.chmod(0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_directory = backup_root / timestamp
    backup_directory.mkdir(mode=0o700)
    return backup_directory


def stage_script(source_path: Path, target_directory: Path) -> Path:
    """Create and validate one executable temporary copy beside its target."""
    temporary_path: Optional[Path] = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=target_directory,
            prefix=".was-operator-script-",
            delete=False,
        ) as temporary_file:
            temporary_file.write(source_path.read_bytes())
            temporary_path = Path(temporary_file.name)
        temporary_path.chmod(INSTALL_MODE)
        validate_bash(temporary_path)
        return temporary_path
    except (OSError, RuntimeError, subprocess.SubprocessError):
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise


def verify_installation(plan: List[Tuple[Path, Path, str]]) -> None:
    """Require every installed target to match its tracked source and mode."""
    for source_path, target_path, unused_action in plan:
        if target_path.is_symlink() or not target_path.is_file():
            raise RuntimeError(
                "Installed target {} is unavailable.".format(target_path.name)
            )
        if target_path.stat().st_uid != os.getuid():
            raise RuntimeError(
                "Installed target {} is not owned by this user.".format(
                    target_path.name
                )
            )
        if source_path.read_bytes() != target_path.read_bytes():
            raise RuntimeError(
                "Installed target {} differs from source.".format(target_path.name)
            )
        if stat.S_IMODE(target_path.stat().st_mode) != INSTALL_MODE:
            raise RuntimeError(
                "Installed target {} has the wrong mode.".format(target_path.name)
            )
        validate_bash(target_path)


def install_scripts(
    source_directory: Path,
    target_directory: Path,
    backup_root: Path,
    apply: bool,
) -> Optional[Path]:
    """Validate, preview, install, back up, and verify operator scripts."""
    sources = validated_sources(source_directory)
    validate_target_directory(target_directory)
    plan = installation_plan(sources, target_directory)

    write_output("Source directory: {}".format(source_directory))
    write_output("Target directory: {}".format(target_directory))
    write_output("Backup root: {}".format(backup_root))
    for source_path, target_path, action in plan:
        write_output(
            "{}: {} -> {}".format(action.upper(), source_path.name, target_path)
        )
    write_output(
        "REVIEW REQUIRED: installation does not approve the legacy script behavior."
    )
    if not apply:
        write_output("PREVIEW ONLY: no directories or files were changed.")
        return None

    target_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    staged_paths: Dict[Path, Path] = {}
    backup_directory: Optional[Path] = None
    try:
        for source_path, target_path, action in plan:
            if action != "current":
                staged_paths[target_path] = stage_script(source_path, target_directory)
        replacement_targets = [
            target_path
            for unused_source, target_path, action in plan
            if action == "replace"
        ]
        if replacement_targets:
            backup_directory = create_backup_directory(backup_root)
            for target_path in replacement_targets:
                backup_path = backup_directory / target_path.name
                shutil.copy2(target_path, backup_path)
                backup_path.chmod(0o600)
        for target_path, staged_path in staged_paths.items():
            os.replace(staged_path, target_path)
        staged_paths.clear()
    finally:
        for staged_path in staged_paths.values():
            if staged_path.exists():
                staged_path.unlink()

    verify_installation(plan)
    write_output("Installed and verified {} operator scripts.".format(len(plan)))
    if backup_directory is not None:
        write_output("Backups: {}".format(backup_directory))
    return backup_directory


def main() -> int:
    """Parse explicit paths and keep destination writes behind the apply flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--source-directory", type=Path, default=DEFAULT_SOURCE_DIRECTORY
    )
    parser.add_argument(
        "--target-directory", type=Path, default=DEFAULT_TARGET_DIRECTORY
    )
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    arguments = parser.parse_args()

    if os.geteuid() == 0 or os.environ.get("SUDO_USER"):
        write_output("STOPPED: run as the normal EC2 operator, without sudo.")
        return 1
    try:
        install_scripts(
            source_directory=arguments.source_directory,
            target_directory=arguments.target_directory,
            backup_root=arguments.backup_root,
            apply=arguments.apply,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        if isinstance(error, RuntimeError):
            write_output("STOPPED: {}".format(error))
        else:
            write_output(
                "STOPPED ({}). Review the target and backup state.".format(
                    type(error).__name__
                )
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
