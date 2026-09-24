"""Validate the immutable tracker workload passed to capacity subprocesses."""

import json
import os


def capacity_tracker_ids() -> frozenset[int] | None:
    """Return explicit capacity scope, leaving ordinary batch selection unchanged."""
    encoded_ids = os.environ.get("WAS_CAPACITY_TRACKER_IDS")
    if os.environ.get("WAS_RUN_MODE") != "capacity":
        if encoded_ids is not None:
            raise ValueError("Capacity tracker scope requires capacity mode")
        return None
    if encoded_ids is None:
        raise ValueError("Capacity tracker scope is required")
    if not os.environ.get("WAS_DB_NAME", "").startswith("was_capacity_"):
        raise ValueError("Capacity tracker scope requires an isolated database")
    try:
        tracker_ids = json.loads(encoded_ids)
    except (ValueError, TypeError) as error:
        raise ValueError("Invalid capacity tracker scope") from error
    if not isinstance(tracker_ids, list) or any(
        type(tracker_id) is not int or tracker_id <= 0 for tracker_id in tracker_ids
    ):
        raise ValueError("Capacity tracker scope must contain positive integer IDs")
    return frozenset(tracker_ids)
