"""Role schema."""
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Role(BaseModel):
    """Role schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    role: str
    approved: bool
    created_by_id: Optional[Any]
    approved_by_id: Optional[Any]
    user: Optional[Any]
    organization_id: Optional[Any]

    class Config:
        """Config."""

        from_attributes = True
