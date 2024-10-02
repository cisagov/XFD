"""Domain schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


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

    model_config = {
        """Organization base schema schema config.""" "from_attributes": True,
        "validate_assignment": True,
    }


class DomainFilters(BaseModel):
    """DomainFilters schema."""

    ports: Optional[str] = None
    service: Optional[str] = None
    reverseName: Optional[str] = None
    ip: Optional[str] = None
    organization: Optional[str] = None
    organizationName: Optional[str] = None
    vulnerabilities: Optional[str] = None
    tag: Optional[str] = None


class DomainSearch(BaseModel):
    """DomainSearch schema."""

    page: int = 1
    sort: str
    order: str
    filters: Optional[DomainFilters]
    pageSize: Optional[int] = None
