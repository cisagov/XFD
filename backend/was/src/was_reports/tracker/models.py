"""Data models used while building the WAS daily tracker."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class TrackerStakeholder:
    """Qualys schedule details required to locate stakeholder scans."""

    name: str
    tag_id: int
    next_scan_date: str
    launched_date: str
    schedule_id: int
    cadence: str
    tag: str = ""
    schedule_name: str = ""
    latest_scan_name: str = ""
    latest_scan_status: str = ""
    scan_started_at: datetime | None = None
    scan_ended_at: datetime | None = None


def scheduled_execution_key(schedule_id: int, launched_date: str) -> str:
    """Identify a schedule execution using its actual UTC launch instant."""
    launch = datetime.fromisoformat(launched_date.replace("Z", "+00:00"))
    if launch.tzinfo is None:
        raise ValueError("Qualys launch timestamp must include a timezone.")
    return "schedule:{}:{}".format(
        schedule_id, launch.astimezone(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class TrackerItem:
    """Consolidated Qualys scan information for one tracker row."""

    tag: str
    scan_name: str
    status: str
    result: str
    launched_date: str
    next_scan_date: str
    nws: bool
    recent_nws: str
    removed_nws: str
    manual: str
    fceb: bool
    schedule_id: int
    qualys_errors: str
    tag_id: int | None = None
    scan_execution_key: str | None = None
    scan_started_at: datetime | None = None
    scan_ended_at: datetime | None = None


QualysScan = Any


def scan_time_bounds(scans: list[QualysScan]) -> tuple[datetime | None, datetime | None]:
    """Return complete, timezone-aware actual scan bounds without inventing times."""
    starts = []
    ends = []
    for scan in scans:
        values = []
        for field in ("launchedDate", "endScanDate"):
            value = scan.findtext(field)
            try:
                timestamp = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
                if timestamp is not None and timestamp.tzinfo is not None:
                    timestamp = timestamp.astimezone(timezone.utc)
                else:
                    timestamp = None
            except ValueError:
                timestamp = None
            values.append(timestamp)
        start, end = values
        if start is not None and not scan.findtext("endScanDate") and scan.findtext("status") == "FINISHED":
            duration = (scan.findtext("scanDuration") or "").strip()
            if duration.isascii() and duration.isdigit():
                try:
                    end = start + timedelta(seconds=int(duration))
                except OverflowError:
                    end = None
        starts.append(start)
        ends.append(end if start is not None and end is not None and end >= start else None)
    started = min(starts) if starts and all(value is not None for value in starts) else None
    ended = max(ends) if ends and all(value is not None for value in ends) else None
    return started, ended
