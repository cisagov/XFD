"""Create isolated filesystems and locks for concurrent WAS reports."""

# Standard Python Libraries
from contextlib import contextmanager
from datetime import date
import fcntl
from pathlib import Path
import shutil
import tempfile
from typing import Iterator, TextIO

# Third-Party Libraries
# First-Party Libraries
from was_reports.reporting.latex_renderer import validate_filename_component


@contextmanager
def isolated_report_workspace(
    resource_root: Path,
    workspace_root: Path,
    stakeholder_tag: str,
) -> Iterator[Path]:
    """Yield a private resource copy and delete it after report generation."""
    if not resource_root.is_dir():
        raise FileNotFoundError(
            "WAS report resource root not found at {}.".format(resource_root)
        )
    safe_tag = validate_filename_component(stakeholder_tag)
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace_path = Path(
        tempfile.mkdtemp(
            prefix="was-{}-".format(safe_tag),
            dir=workspace_root,
        )
    )
    try:
        shutil.copytree(resource_root, workspace_path, dirs_exist_ok=True)
        yield workspace_path
    finally:
        shutil.rmtree(workspace_path, ignore_errors=True)


@contextmanager
def report_output_lock(
    output_directory: Path,
    stakeholder_tag: str,
    report_date: date,
) -> Iterator[None]:
    """Prevent concurrent generation of the same stakeholder report."""
    safe_tag = validate_filename_component(stakeholder_tag)
    output_directory.mkdir(parents=True, exist_ok=True)
    lock_path = output_directory / ".{}_{}.lock".format(
        safe_tag,
        report_date.isoformat(),
    )
    lock_file: TextIO = lock_path.open("a", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(
                "A WAS report is already running for {} on {}.".format(
                    safe_tag,
                    report_date.isoformat(),
                )
            ) from error
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
