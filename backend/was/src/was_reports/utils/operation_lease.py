"""Background lease heartbeats for long-running WAS operations."""

# Standard Python Libraries
from contextlib import contextmanager
import logging
from threading import Event, Thread
from typing import Callable, Iterator

# First-Party Libraries
from was_reports.utils.env import getenv

DEFAULT_HEARTBEAT_SECONDS = 30
LOGGER = logging.getLogger(__name__)


def heartbeat_seconds() -> int:
    """Return the configured positive heartbeat interval."""
    raw_value = getenv(
        "WAS_OPERATION_HEARTBEAT_SECONDS",
        str(DEFAULT_HEARTBEAT_SECONDS),
    )
    try:
        value = int(raw_value or DEFAULT_HEARTBEAT_SECONDS)
    except ValueError as error:
        raise ValueError(
            "WAS_OPERATION_HEARTBEAT_SECONDS must be an integer."
        ) from error
    if value < 1:
        raise ValueError("WAS_OPERATION_HEARTBEAT_SECONDS must be at least 1.")
    return value


def _heartbeat_loop(
    stop_event: Event,
    interval_seconds: int,
    heartbeat: Callable[[], bool],
    operation_name: str,
) -> None:
    """Refresh one operation lease until completion or ownership loss."""
    while not stop_event.wait(interval_seconds):
        try:
            if not heartbeat():
                LOGGER.error("WAS operation lease was lost: %s", operation_name)
                return
        except Exception:
            LOGGER.exception(
                "Unable to refresh WAS operation lease: %s",
                operation_name,
            )


@contextmanager
def operation_heartbeat(
    heartbeat: Callable[[], bool],
    operation_name: str,
) -> Iterator[None]:
    """Refresh an operation lease in the background while work executes."""
    interval_seconds = heartbeat_seconds()
    stop_event = Event()
    thread = Thread(
        target=_heartbeat_loop,
        args=(stop_event, interval_seconds, heartbeat, operation_name),
        daemon=True,
        name="was-operation-heartbeat",
    )
    thread.start()
    try:
        yield
    finally:
        stop_event.set()
        thread.join(timeout=interval_seconds + 1)
