"""Cve schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Cve(BaseModel):
    """Cve schema."""

    id: UUID
    name: Optional[str]
    publishedAt: datetime
    modifiedAt: datetime
    status: str
    description: Optional[str]
    cvssV2Source: Optional[str]
    cvssV2Type: Optional[str]
    cvssV2VectorString: Optional[str]
    cvssV2BaseSeverity: Optional[str]
    cvssV2ExploitabilityScore: Optional[str]
    cvssV2ImpactScore: Optional[str]
    cvssV3Source: Optional[str]
    cvssV3Type: Optional[str]
    cvssV3VectorString: Optional[str]
    cvssV3BaseSeverity: Optional[str]
    cvssV3ExploitabilityScore: Optional[str]
    cvssV3ImpactScore: Optional[str]
    cvssV4Source: Optional[str]
    cvssV4Type: Optional[str]
    cvssV4VectorString: Optional[str]
    cvssV4BaseSeverity: Optional[str]
    cvssV4ExploitabilityScore: Optional[str]
    cvssV4ImpactScore: Optional[str]
    weaknesses: Optional[str]
    references: Optional[str]

    class Config:
        from_attributes = True
