"""Optional secret-free endpoint events and container resource samples."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
from threading import Event, Thread
from time import monotonic
from typing import Iterator

LOGGER = logging.getLogger(__name__)


def emit_metric(event: str, **fields: object) -> None:
    """Append one process-local JSON event without impacting report execution."""
    directory = os.environ.get("WAS_METRICS_DIRECTORY")
    if not directory:
        return
    record = {
        "event": event,
        "time": datetime.now(timezone.utc).isoformat(),
        "monotonic_seconds": monotonic(),
        "batch_id": os.environ.get("WAS_ANALYST_BATCH_ID"),
        "pid": os.getpid(),
        **fields,
    }
    try:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(
            path / "metrics-{}.jsonl".format(os.getpid()),
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    except (OSError, TypeError, ValueError):
        LOGGER.warning("Capacity metric could not be written; telemetry is incomplete.")


def resource_sample(output_directory: Path) -> dict[str, object]:
    """Read cgroup-v2 totals and output-filesystem space, not host-wide CPU."""
    result: dict[str, object] = {
        "scope": "container_cgroup_v2",
        "cpu_usage_usec": None,
        "memory_current_bytes": None,
        "memory_peak_bytes": None,
        "output_filesystem_used_bytes": None,
        "output_filesystem_free_bytes": None,
    }
    root = Path("/sys/fs/cgroup")
    try:
        values = dict(line.split() for line in (root / "cpu.stat").read_text().splitlines())
        result["cpu_usage_usec"] = int(values["usage_usec"])
    except (OSError, ValueError, KeyError):
        pass
    for filename, field in (("memory.current", "memory_current_bytes"),
                            ("memory.peak", "memory_peak_bytes")):
        try:
            result[field] = int((root / filename).read_text().strip())
        except (OSError, ValueError):
            pass
    try:
        usage = shutil.disk_usage(output_directory)
        result["output_filesystem_used_bytes"] = usage.used
        result["output_filesystem_free_bytes"] = usage.free
    except OSError:
        pass
    return result


@contextmanager
def resource_monitor(output_directory: str | Path, interval: float = 5.0) -> Iterator[None]:
    """Sample the coordinator container, including child workers, until exit."""
    if interval <= 0:
        raise ValueError("Resource sample interval must be positive.")
    stopped = Event()

    def sample() -> None:
        """Record one sample without collecting process arguments or secrets."""
        emit_metric("resources", **resource_sample(Path(output_directory)))

    def monitor() -> None:
        """Wait interruptibly between samples."""
        while not stopped.wait(interval):
            sample()

    sample()
    thread = Thread(target=monitor, name="was-capacity-resources", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set()
        thread.join(timeout=interval + 1)
        sample()
