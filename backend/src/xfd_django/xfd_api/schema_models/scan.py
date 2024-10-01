"""Scan schemas."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Scan(BaseModel):
    """Scan schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    name: str
    arguments: Any
    frequency: int
    lastRun: Optional[datetime]
    isGranular: bool
    isUserModifiable: Optional[bool]
    isSingleScan: bool
    manualRunPending: bool
    createdBy: Optional[Any]

    class Config:
        from_attributes = True


class ScanTask(BaseModel):
    """ScanTask schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    status: str
    type: str
    fargateTaskArn: Optional[str]
    input: Optional[str]
    output: Optional[str]
    requestedAt: Optional[datetime]
    startedAt: Optional[datetime]
    finishedAt: Optional[datetime]
    queuedAt: Optional[datetime]
    organizationId: Optional[Any]
    scanId: Optional[Any]

    class Config:
        from_attributes = True
