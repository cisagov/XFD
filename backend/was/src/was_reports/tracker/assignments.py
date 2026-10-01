"""Assignment helpers for WAS tracker rows."""

# Standard Python Libraries
from typing import Sequence


def round_robin_assignee(
    assignees: Sequence[str],
    item_index: int,
    reverse_order: bool = True,
) -> str:
    """Return the assignee for an item using even round-robin distribution."""
    if not assignees:
        raise ValueError("At least one assignee is required.")

    if item_index < 0:
        raise ValueError("Item index must not be negative.")

    if reverse_order:
        ordered_assignees = list(assignees)[::-1]
    else:
        ordered_assignees = list(assignees)

    return ordered_assignees[item_index % len(ordered_assignees)]
