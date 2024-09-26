"""Cpe schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Cpe(BaseModel):
    """Cpe schema."""

    id: UUID
    name: Optional[str]
    version: Optional[str]
    vendor: Optional[str]
    lastSeenAt: datetime
