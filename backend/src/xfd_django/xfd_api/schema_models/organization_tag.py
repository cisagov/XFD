"""Schemas to support Organization Tag endpoints."""

# Standard Python Libraries
from datetime import datetime
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class OrganizationalTags(BaseModel):
    """Organization Tags."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
