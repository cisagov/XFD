"""Assessment Schemas."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Assessment(BaseModel):
    """Assessment schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    rscId: str
    type: str
    userId: Optional[Any]

    class Config:
        from_attributes = True
