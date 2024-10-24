"""Domain schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from ..schema_models.service import Service
from ..schema_models.vulnerability import Vulnerability


class Domain(BaseModel):
    """Domain schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    syncedAt: datetime
    ip: str
    fromRootDomain: Optional[str]
    subdomainSource: Optional[str]
    ipOnly: bool
    reverseName: Optional[str]
    name: Optional[str]
    screenshot: Optional[str]
    country: Optional[str]
    asn: Optional[str]
    cloudHosted: bool
    ssl: Optional[Any]
    censysCertificatesResults: Optional[dict]
    trustymailResults: Optional[dict]
    discoveredById_id: Optional[UUID]
    organizationId_id: Optional[UUID]

    class Config:
        """Domain base schema config."""

        from_attributes = True
        validate_assignment = True


class DomainFilters(BaseModel):
    """DomainFilters schema."""

    port: Optional[int] = None
    service: Optional[str] = None
    reverseName: Optional[str] = None
    ip: Optional[str] = None
    organization: Optional[str] = None
    organizationName: Optional[str] = None
    vulnerabilities: Optional[str] = None
    tag: Optional[str] = None

    class Config:
        from_attributes = True


class DomainSearch(BaseModel):
    """DomainSearch schema."""

    page: int = 1
    sort: Optional[str] = "ASC"
    order: Optional[str] = "id"
    filters: Optional[DomainFilters] = None
    pageSize: Optional[int] = 25

    class Config:
        from_attributes = True
