"""Data models used while building the WAS daily tracker."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass
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


QualysScan = Any
