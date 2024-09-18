"""Pydantic models used by FastAPI."""
from collections import UserDict
# Standard Python Libraries
from datetime import date, datetime
from decimal import Decimal

# from pydantic.types import UUID1, UUID
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from matplotlib.text import OffsetFrom
# Third-Party Libraries
from pydantic import BaseModel, EmailStr, Field, UUID4
from pygments.lexers.configs import UnixConfigLexer

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
    syncedAt: Optional[datetime]
    ip: Optional[str]
    fromRootDomain: Optional[str]
    subdomainSource: Optional[str]
    ipOnly: bool
    reverseName: str
    name: str
    screenshot: Optional[str]
    country: Optional[str]
    asn: Optional[str]
    cloudHosted: bool
    ssl: Optional[Dict]
    censysCertificatesResults: Dict
    trustymailResults: Dict
    discoveredById_id: Optional[UUID4]
    organizationId_id: Optional[UUID4]

    class Config:
        """Domain base schema schema config."""

        orm_mode = True
        validate_assignment = True


class Organization(BaseModel):
    id: UUID
    createdAt: datetime
    updatedAt: datetime
    acronym: Optional[str]
    name: str
    rootDomains: str
    ipBlocks: str
    isPassive: bool
    pendingDomains: str
    country: Optional[str]
    state: Optional[str]
    regionId: Optional[str]
    stateFips: Optional[int]
    stateName: Optional[str]
    county: Optional[str]
    countyFips: Optional[int]
    type: Optional[str]

    class Config:
        """Organization base schema schema config."""

        orm_mode = True
        validate_assignment = True