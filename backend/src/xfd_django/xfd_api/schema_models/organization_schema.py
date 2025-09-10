"""Schemas to support Organization endpoints."""

# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Field

from .organization_tag import OrganizationalTags


class Organization(BaseModel):
    """Organization schema reflecting model."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    acronym: Optional[str]
    name: str
    root_domains: List[str]
    ip_blocks: List[str]
    is_passive: bool
    pending_domains: Optional[List[Union[Dict[str, Any], str]]]
    country: Optional[str]
    state: Optional[str]
    region_id: Optional[str]
    state_fips: Optional[int]
    state_name: Optional[str]
    county: Optional[str]
    county_fips: Optional[int]
    type: Optional[str]


class UserRoleSchema(BaseModel):
    """User role schema."""

    id: UUID
    role: str
    approved: bool
    user: Optional[dict] = {}


class TagSchema(BaseModel):
    """Tag schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
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
    created_at: datetime
    updated_at: datetime
    name: str
    arguments: Any
    frequency: int
    last_run: Optional[datetime]
    is_granular: bool
    is_user_modifiable: Optional[bool]
    is_single_scan: bool
    manual_run_pending: bool
    tags: Optional[List[OrganizationalTags]] = []
    organizations: Optional[List[Organization]] = []


class ScanTaskSchema(BaseModel):
    """Scan task schema."""

    id: UUID
    created_at: datetime
    scan: Optional[SimpleScanSchema] = None


class GetOrganizationSchema(BaseModel):
    """Schema for listing an organization."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    acronym: Optional[str] = None
    name: str
    root_domains: Optional[Any] = None
    ip_blocks: Optional[Any] = None
    is_passive: Optional[bool]
    pending_domains: Optional[Any] = []
    country: Optional[str] = None
    state: Optional[str] = None
    region_id: Optional[str] = None
    state_fips: Optional[int] = None
    state_name: Optional[str] = None
    county: Optional[str] = None
    county_fips: Optional[int] = None
    type: Optional[str] = None
    user_roles: Optional[List[UserRoleSchema]] = []
    tags: Optional[List[TagSchema]] = []


class GetSingleOrganizationSchema(BaseModel):
    """Schema for listing an organization."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    acronym: Optional[str]
    name: str
    root_domains: List[str]
    ip_blocks: List[str]
    is_passive: bool
    created_by: Optional[Any] = {}
    pending_domains: Optional[Any] = []
    country: Optional[str] = None
    state: Optional[str] = None
    region_id: Optional[str] = None
    state_fips: Optional[int] = None
    state_name: Optional[str] = None
    county: Optional[str] = None
    county_fips: Optional[int] = None
    type: Optional[str] = None
    user_roles: Optional[List[UserRoleSchema]] = []
    tags: Optional[List[TagSchema]] = []
    parent: Optional[Any] = {}
    children: Optional[Any] = {}
    granular_scans: Optional[List[GranularScanSchema]] = []
    scan_tasks: Optional[List[ScanTaskSchema]] = []


class NewTag(BaseModel):
    """Schema for tag data."""

    name: str  # Adjust this if there could be an 'id' field


class NewOrganization(BaseModel):
    """Create a new organization schema."""

    acronym: Optional[str]
    name: str
    root_domains: List[str]
    ip_blocks: List[str]
    is_passive: bool
    pending_domains: Optional[Any] = []
    country: Optional[str] = None
    state: Optional[str] = None
    region_id: Optional[str] = None
    state_fips: Optional[int] = None
    state_name: Optional[str] = None
    county: Optional[str] = None
    county_fips: Optional[int] = None
    type: Optional[str] = None
    parent: Optional[str] = None
    tags: Optional[List[NewTag]] = None


class NewOrgUser(BaseModel):
    """Add a user to organization schema."""

    user_id: str
    role: str


class NewOrgScan(BaseModel):
    """Update an organization scan schema."""

    enabled: bool


class RegionSchema(BaseModel):
    """Update an organization scan schema."""

    region_id: str


class GenericMessageResponseModel(BaseModel):
    """Generic response model."""

    status: str
    message: str


class RemoveRoleResponseModel(BaseModel):
    """Remove role response model."""

    status: str
    message: str


class DeleteUserResponseModel(BaseModel):
    """Delete user response model."""

    status: str
    message: str
    user_deleted: Any


class OrganizationSearchBody(BaseModel):
    """Elastic search orgnaization model."""

    regions: Optional[List[str]]
    search_term: str


class FilterSchema(BaseModel):
    """Elastic search orgnaization model."""

    regions: Optional[List[str]] = []
    organizations: Optional[List[str]] = []
    tags: Optional[List[str]] = []


class StatsPayloadSchema(BaseModel):
    """Elastic search orgnaization model."""

    filters: Optional[FilterSchema]


class OrganizationSearch(BaseModel):
    """Organization search schema."""

    page: int = Field(1, ge=1)
    pageSize: int = Field(15, ge=1, le=200)
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort: Optional[str] = None  # e.g., "name"
    order: Optional[Literal["asc", "desc"]] = None


class PaginatedOrganizationsResponse(BaseModel):
    """Paginated organization response schema."""

    result: List[GetOrganizationSchema]
    count: int
