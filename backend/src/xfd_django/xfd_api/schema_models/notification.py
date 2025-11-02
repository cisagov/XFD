"""Notification schema."""
# Standard Python Libraries
from datetime import datetime
from typing import Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Notification(BaseModel):
    """Notification schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    start_datetime: Optional[datetime]
    end_datetime: Optional[datetime]
    maintenance_type: Optional[str]
    updated_by: Optional[str]
    status: Optional[str]
    message: Optional[str]

    class Config:
        """Config."""

        from_attributes = True


class CreateNotificationSchema(BaseModel):
    """Create notification schema."""

    maintenance_type: str
    status: str
    updated_by: str
    message: str
    start_datetime: datetime
    end_datetime: datetime
