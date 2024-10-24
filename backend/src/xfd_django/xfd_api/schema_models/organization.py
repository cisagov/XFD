"""Schemas to support Organization endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .organization_tag import OrganizationalTags


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


class UserRoleSchema(BaseModel):
    """User role schema."""

    id: UUID
    role: str
    approved: bool


class TagSchema(BaseModel):
    """Tag schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    name: str


class GetTagSchema(BaseModel):
    """Tag simplified schema."""

    id: UUID
    name: str


class SimpleScanSchema(BaseModel):
    """Simple scan schema."""

    id: UUID
    name: str


class GranularScanSchema(BaseModel):
    """Granular task schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    name: str
    arguments: Any
    frequency: int
    lastRun: Optional[datetime]
    isGranular: bool
    isUserModifiable: Optional[bool]
    isSingleScan: bool
    manualRunPending: bool
    tags: Optional[List[OrganizationalTags]] = []
    organizations: Optional[List[Organization]] = []


class ScanTaskSchema(BaseModel):
    """Scan task schema."""

    id: UUID
    createdAt: datetime
    scan: SimpleScanSchema


class GetOrganizationSchema(BaseModel):
    """Schema for listing an organization."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    acronym: Optional[str]
    name: str
    rootDomains: List[str]
    ipBlocks: List[str]
    isPassive: bool
    pendingDomains: Optional[Any] = []
    country: Optional[str] = None
    state: Optional[str] = None
    regionId: Optional[str] = None
    stateFips: Optional[int] = None
    stateName: Optional[str] = None
    county: Optional[str] = None
    countyFips: Optional[int] = None
    type: Optional[str] = None
    userRoles: Optional[List[UserRoleSchema]] = []
    tags: Optional[List[TagSchema]] = []


class GetSingleOrganizationSchema(BaseModel):
    """Schema for listing an organization."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    acronym: Optional[str]
    name: str
    rootDomains: List[str]
    ipBlocks: List[str]
    isPassive: bool
    createdBy: Optional[Any] = {}
    pendingDomains: Optional[Any] = []
    country: Optional[str] = None
    state: Optional[str] = None
    regionId: Optional[str] = None
    stateFips: Optional[int] = None
    stateName: Optional[str] = None
    county: Optional[str] = None
    countyFips: Optional[int] = None
    type: Optional[str] = None
    userRoles: Optional[List[UserRoleSchema]] = []
    tags: Optional[List[TagSchema]] = []
    parent: Optional[Any] = {}
    children: Optional[Any] = {}
    granularScans: Optional[List[GranularScanSchema]] = []
    scanTasks: Optional[List[ScanTaskSchema]] = []


class NewTag(BaseModel):
    """Schema for tag data."""

    name: str  # Adjust this if there could be an 'id' field


class NewOrganization(BaseModel):
    """Create a new organization schema."""

    acronym: Optional[str]
    name: str
    rootDomains: List[str]
    ipBlocks: List[str]
    isPassive: bool
    pendingDomains: Optional[Any] = []
    country: Optional[str] = None
    state: Optional[str] = None
    regionId: Optional[str] = None
    stateFips: Optional[int] = None
    stateName: Optional[str] = None
    county: Optional[str] = None
    countyFips: Optional[int] = None
    type: Optional[str] = None
    parent: Optional[str] = None
    tags: Optional[List[NewTag]] = None


class NewOrgUser(BaseModel):
    """Add a user to organization schema."""

    userId: str
    role: str


class NewOrgScan(BaseModel):
    """Update an organization scan schema."""

    enabled: bool


class RegionSchema(BaseModel):
    """Update an organization scan schema."""

    regionId: str


class GenericMessageResponseModel(BaseModel):
    """Generic response model."""

    status: str
    message: str


class GenericPostResponseModel(BaseModel):
    """Generic response model."""

    statusCode: int
    body: Any
