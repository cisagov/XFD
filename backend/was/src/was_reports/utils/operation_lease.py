"""Background lease heartbeats for long-running WAS operations."""

# Standard Python Libraries
from contextlib import contextmanager
from contextvars import ContextVar
import logging
from threading import Event, Lock, Thread
from typing import Callable, Iterator

# Third-Party Libraries
# First-Party Libraries
from was_reports.utils.env import getenv

DEFAULT_HEARTBEAT_SECONDS = 30
LOGGER = logging.getLogger(__name__)
CURRENT_OWNERSHIP_CHECK: ContextVar[Callable[[], None] | None] = ContextVar(
    "was_ownership_check", default=None
)


class OperationLeaseLostError(RuntimeError):
    """Indicate that ownership cannot be established for an operation."""


def check_operation_ownership() -> None:
    """Check the active lease before beginning an external side effect."""
    ownership_check = CURRENT_OWNERSHIP_CHECK.get()
    if ownership_check is not None:
        ownership_check()


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
    heartbeat: Callable[[], None],
    operation_name: str,
) -> None:
    """Refresh one operation lease until completion or ownership loss."""
    while not stop_event.wait(interval_seconds):
        try:
            heartbeat()
        except Exception:
            LOGGER.error(
                "Unable to refresh WAS operation lease: %s",
                operation_name,
            )
            return


@contextmanager
def operation_heartbeat(
    heartbeat: Callable[[], bool],
    operation_name: str,
) -> Iterator[Callable[[], None]]:
    """Refresh an operation lease in the background while work executes."""
    interval_seconds = heartbeat_seconds()
    stop_event = Event()
    lost_event = Event()
    heartbeat_lock = Lock()
    parent_check = CURRENT_OWNERSHIP_CHECK.get()

    def check_ownership() -> None:
        """Fail closed on a rejected or uncertain lease refresh."""
        with heartbeat_lock:
            if lost_event.is_set():
                raise OperationLeaseLostError("WAS operation ownership was lost.")
            try:
                if parent_check is not None:
                    parent_check()
                if not heartbeat():
                    raise OperationLeaseLostError("WAS operation ownership was lost.")
            except Exception as error:
                lost_event.set()
                raise OperationLeaseLostError(
                    "WAS operation ownership could not be verified."
                ) from error

    check_ownership()
    context_token = CURRENT_OWNERSHIP_CHECK.set(check_ownership)
    thread = Thread(
        target=_heartbeat_loop,
        args=(stop_event, interval_seconds, check_ownership, operation_name),
        daemon=True,
        name="was-operation-heartbeat",
    )
    try:
        thread.start()
        try:
            yield check_ownership
        finally:
            stop_event.set()
            thread.join(timeout=interval_seconds + 1)
    finally:
        CURRENT_OWNERSHIP_CHECK.reset(context_token)
    if lost_event.is_set() or thread.is_alive():
        raise OperationLeaseLostError("WAS operation ownership was lost.")
