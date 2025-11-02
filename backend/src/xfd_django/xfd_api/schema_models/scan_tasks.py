"""Schemas to support scan task endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .organization_schema import Organization
from .scan import Scan


class ScanTaskSearch(BaseModel):
    """Scan-task search schema."""

    page: Optional[int] = 1
    page_size: Optional[int] = 10
    sort: Optional[str] = "created_at"
    order: Optional[str] = "DESC"
    filters: Optional[Dict[str, Optional[str]]] = {}


class ScanTaskList(BaseModel):
    """Single scan-task schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    status: str
    type: str
    fargate_task_arn: Optional[str]
    input: Optional[str]
    output: Optional[str]
    requested_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    queued_at: Optional[datetime]
    concurrency_index: Optional[int]
    scan: Optional[Scan]
    organization: Optional[List[Organization]] = []


class ScanTaskListResponse(BaseModel):
    """Scan-task list schema."""

    result: List[ScanTaskList] = []
    count: int


class GenericResponse(BaseModel):
    """Generic scan task response."""

    status_code: int
    message: str
