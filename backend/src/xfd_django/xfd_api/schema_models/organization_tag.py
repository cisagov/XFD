"""Schemas to support Organization Tag endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json

class OrganizationalTags(BaseModel):
    """Organization Tags."""
    id: UUID
    createdAt: datetime
    updatedAt: datetime
    name: str