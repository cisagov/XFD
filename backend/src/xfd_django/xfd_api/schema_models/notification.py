"""Notification schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Notification(BaseModel):
    """Notification schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    startDatetime: Optional[datetime]
    endDateTime: Optional[datetime]
    maintenanceType: Optional[str]
    status: Optional[str]
    updatedBy: datetime
    message: Optional[str]
