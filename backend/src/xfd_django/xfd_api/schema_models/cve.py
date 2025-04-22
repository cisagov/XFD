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
    published_at: datetime
    modified_at: datetime
    status: str
    description: Optional[str]
    cvss_v2_source: Optional[str]
    cvss_v2_type: Optional[str]
    cvss_v2_vector_string: Optional[str]
    cvss_v2_base_severity: Optional[str]
    cvss_v2_exploitability_score: Optional[str]
    cvss_v2_impact_score: Optional[str]
    cvss_v3_source: Optional[str]
    cvss_v3_type: Optional[str]
    cvss_v3_vector_string: Optional[str]
    cvss_v3_base_severity: Optional[str]
    cvss_v3_exploitability_score: Optional[str]
    cvss_v3_impact_score: Optional[str]
    cvss_v4_source: Optional[str]
    cvss_v4_type: Optional[str]
    cvss_v4_vector_string: Optional[str]
    cvss_v4_base_severity: Optional[str]
    cvss_v4_exploitability_score: Optional[str]
    cvss_v4_impact_score: Optional[str]
    weaknesses: Optional[str]
    references: Optional[str]

    class Config:
        """Config."""

        from_attributes = True
