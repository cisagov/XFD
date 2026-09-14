"""Tests for cooperative cancellation of interactive WAS operations."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.utils.operation_cancellation import (
    OperationCancelledError,
    cancellable_sleep,
    clear_operation_cancellation,
    raise_if_operation_cancelled,
    request_operation_cancellation,
)


class OperationCancellationTests(unittest.TestCase):
    """Validate cancellation checks without interrupting unsafe side effects."""

    def tearDown(self) -> None:
        """Prevent cancellation state from leaking into another test."""
        clear_operation_cancellation()

    def test_requested_cancellation_raises_at_checkpoint(self) -> None:
        """Stop an operation when it reaches a cooperative checkpoint."""
        request_operation_cancellation()

        with self.assertRaises(OperationCancelledError):
            raise_if_operation_cancelled()

    def test_cancellable_sleep_stops_before_custom_delay_returns(self) -> None:
        """Check cancellation after an injected delay used by unit tests."""
        request_operation_cancellation()

        with self.assertRaises(OperationCancelledError):
            cancellable_sleep(1, sleep_function=lambda seconds: None)
