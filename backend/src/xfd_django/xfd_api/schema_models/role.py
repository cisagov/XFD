"""Role schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Role(BaseModel):
    """Role schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    role: str
    approved: bool
    createdById: Optional[Any]
    approvedById: Optional[Any]
    userId: Optional[Any]
    organizationId: Optional[Any]

    class Config:
        from_attributes = True
