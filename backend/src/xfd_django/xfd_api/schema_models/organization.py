"""Organization schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Organization(BaseModel):
    """Organization schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    acronym: Optional[str]
    name: str
    rootDomains: List[str]
    ipBlocks: List[str]
    isPassive: bool
    pendingDomains: List[str]
    country: Optional[str]
    state: Optional[str]
    regionId: Optional[str]
    stateFips: Optional[int]
    stateName: Optional[str]
    county: Optional[str]
    countyFips: Optional[int]
    type: Optional[str]
