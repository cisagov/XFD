"""Schemas to support scan task endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import List, Optional

# Third-Party Libraries
from pydantic import BaseModel


class OrgCountByStatus(BaseModel):
    """HTTP status and distinct org count."""

    http_status: int
    org_count: int


class ScanOrgCountByStatus(BaseModel):
    """Scan metadata and success counts per status."""

    id: str
    created_at: datetime
    updated_at: datetime
    name: str
    frequency: int
    last_run: Optional[datetime]
    total_orgs: int
    org_counts_by_status: List[OrgCountByStatus]


class ListScansOrgCountByStatusResponse(BaseModel):
    """Top-level response model for API."""

    scans: List[ScanOrgCountByStatus]
    metrics_window_days: int


class DailyCount(BaseModel):
    """Count for a specific date."""

    date: str
    count: int


class DailyStatusCount(BaseModel):
    """Daily Counts for a specific http_status."""

    http_status: int
    daily_counts: List[DailyCount]


class GetScanDailyStatusCountsResponse(BaseModel):
    """Top-level response model for daily status counts."""

    id: str
    created_at: datetime
    updated_at: datetime
    name: str
    frequency: int
    last_run: Optional[datetime]
    total_orgs: int
    daily_status_counts: List[DailyStatusCount]
    metrics_window_days: int
