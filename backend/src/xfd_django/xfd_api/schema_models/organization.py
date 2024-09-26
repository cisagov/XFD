"""Schemas to support Organization endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json


class Organization(BaseModel):
    """Organization schema reflecting model."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    acronym: Optional[str]
    name: str
    rootDomains: List[str]
    ipBlocks: List[str]
    isPassive: bool
    pendingDomains: Optional[List[dict]]
    country: Optional[str]
    state: Optional[str]
    regionId: Optional[str]
    stateFips: Optional[int]
    stateName: Optional[str]
    county: Optional[str]
    countyFips: Optional[int]
    type: Optional[str]