"""Service schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json


class Service(BaseModel):
    """Service schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    serviceSource: Optional[str]
    port: int
    service: Optional[str]
    lastSeen: Optional[datetime]
    banner: Optional[str]
    products: Json[Any]
    censysMetadata: Json[Any]
    censysIpv4Results: Json[Any]
    shodanResults: Json[Any]
    wappalyzerResults: Json[Any]
    domainId: Optional[Any]
    discoveredById: Optional[Any]
