"""Cooperative cancellation state for interactive WAS operations."""

# Standard Python Libraries
from threading import Event
import time
from typing import Callable


class OperationCancelledError(RuntimeError):
    """Indicate that an operator requested cancellation at a safe boundary."""


OPERATION_CANCEL_EVENT = Event()


def clear_operation_cancellation() -> None:
    """Clear cancellation state before starting an interactive operation."""
    OPERATION_CANCEL_EVENT.clear()


def request_operation_cancellation() -> None:
    """Record an operator request to stop at the next safe boundary."""
    OPERATION_CANCEL_EVENT.set()


def raise_if_operation_cancelled() -> None:
    """Stop the active operation when cancellation has been requested."""
    if OPERATION_CANCEL_EVENT.is_set():
        raise OperationCancelledError("Operation cancelled by the operator.")


def cancellable_sleep(
    seconds: float,
    sleep_function: Callable[[float], None] = time.sleep,
) -> None:
    """Wait for a delay while allowing menu cancellation to end it promptly."""
    if sleep_function is time.sleep:
        if OPERATION_CANCEL_EVENT.wait(seconds):
            raise_if_operation_cancelled()
        return
    sleep_function(seconds)
    raise_if_operation_cancelled()
