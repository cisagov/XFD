"""Schemas to support scan task endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .organization import Organization
from .scan import Scan


class ScanTaskSearch(BaseModel):
    """Scan-task search schema."""

    page: int
    pageSize: int
    sort: str
    order: str
    filters: Any


class ScanTaskList(BaseModel):
    """Single scan-task schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    status: str
    type: str
    fargateTaskArn: str
    input: str
    output: Optional[str]
    requestedAt: Optional[datetime]
    startedAt: Optional[datetime]
    finishedAt: Optional[datetime]
    queuedAt: Optional[datetime]
    scan: Optional[Scan]
    organization: Optional[List[Organization]] = []


class ScanTaskListResponse(BaseModel):
    """Scan-task list schema."""

    result: List[ScanTaskList]
    count: int


class GenericResponse(BaseModel):
    """Generic scan task response."""

    statusCode: int
    message: str
