"""Pydantic models used by FastAPI."""
# Standard Python Libraries
from datetime import date, datetime
from decimal import Decimal

# from pydantic.types import UUID1, UUID
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, EmailStr, Field, UUID4

"""
Developer Note: If there comes an instance as in class Cidrs where there are
foreign keys. The data type will not be what is stated in the database. What is
happening is the data base is making a query back to the foreign key table and
returning it as the column in its entirety i.e. select * from <table>, so it
will error and not be able to report on its data type. In these scenario's use
the data type "Any" to see what the return is.
"""


class Point(BaseModel):
    id: str
    label: str
    value: int

class Stats(BaseModel):
    id: UUID4
    value: int

    class Config:
        from_attributes = True

class Ports(BaseModel):
    id: UUID4
    value: int

    class Config:
        from_attributes = True

class StatsFilters(BaseModel):
    organization: Optional[UUID4]
    tag: Optional[UUID4]

class StatsSearch(BaseModel):
    filters: Optional[StatsFilters]

class Domain(BaseModel):
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
    discoveredById: Optional[Any]
    organizationId: Optional[Any]
    