"""Schemas.py."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json


class Assessment(BaseModel):
    """Assessment schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    rscId: str
    type: str
    userId: Optional[Any]


class Category(BaseModel):
    """Category schema."""

    id: UUID
    name: str
    number: str
    shortName: Optional[str]


class Cpe(BaseModel):
    """Cpe schema."""

    id: UUID
    name: Optional[str]
    version: Optional[str]
    vendor: Optional[str]
    lastSeenAt: datetime


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
    discoveredById: Optional[Any]
    organizationId: Any


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


class Notification(BaseModel):
    """Notification schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    startDatetime: Optional[datetime]
    endDateTime: Optional[datetime]
    maintenanceType: Optional[str]
    status: Optional[str]
    updatedBy: datetime
    message: Optional[str]


class Organization(BaseModel):
    """Organization schema."""

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


class Question(BaseModel):
    """Question schema."""

    id: UUID
    name: str
    description: str
    longForm: str
    number: str
    categoryId: Optional[Any]


class Resource(BaseModel):
    """Resource schema."""

    id: UUID
    description: str
    name: str
    type: str
    url: str


class Response(BaseModel):
    """Response schema."""

    id: UUID
    selection: str
    assessmentId: Optional[Any]
    questionId: Optional[Any]


class Role(BaseModel):
    """Role schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    role: str
    createdBy: Optional[Any]
    approvedBy: Optional[Any]
    userId: Optional[Any]
    organizationId: Optional[Any]


class Scan(BaseModel):
    """Scan schema."""

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
    createdBy: Optional[Any]


class ScanTask(BaseModel):
    """ScanTask schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    status: str
    type: str
    fargateTaskArn: Optional[str]
    input: Optional[str]
    output: Optional[str]
    requestedAt: Optional[datetime]
    startedAt: Optional[datetime]
    finishedAt: Optional[datetime]
    queuedAt: Optional[datetime]
    organizationId: Optional[Any]
    scanId: Optional[Any]


class SearchBody(BaseModel):
    """SearchBody schema."""

    current: int
    resultsPerPage: int
    searchTerm: str
    sortDirection: str
    sortField: str
    filters: Json[Any]
    organizationId: Optional[UUID]
    tagId: Optional[UUID]


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


class User(BaseModel):
    """User schema."""

    id: UUID
    cognitoId: Optional[str]
    loginGovId: Optional[str]
    createdAt: datetime
    updatedAt: datetime
    firstName: str
    lastName: str
    fullName: str
    email: str
    invitePending: bool
    loginBlockedByMaintenance: bool
    dateAcceptedTerms: Optional[datetime]
    acceptedTermsVersion: Optional[datetime]
    lastLoggedIn: Optional[datetime]
    userType: str
    regionId: Optional[str]
    state: Optional[str]
    oktaId: Optional[str]


class Vulnerability(BaseModel):
    """Vulnerability schema."""

    id: UUID
    createdAt: datetime
    updatedAt: datetime
    lastSeen: datetime
    title: Optional[str]
    cve: Optional[str]
    cwe: Optional[str]
    cpe: Optional[str]
    description: Optional[str]
    references: Json[Any]
    cvss: float
    severity: Optional[str]
    needsPopulation: bool
    state: Optional[str]
    substate: Optional[str]
    source: Optional[str]
    notes: Optional[str]
    actions: Json[Any]
    structuredData: Json[Any]
    isKev: bool
    domainId: UUID
    serviceId: UUID


class VulnerabilityFilters(BaseModel):
    """VulnerabilityFilters schema."""

    id: Optional[UUID]
    title: Optional[str]
    domain: Optional[str]
    severity: Optional[str]
    cpe: Optional[str]
    state: Optional[str]
    substate: Optional[str]
    organization: Optional[UUID]
    tag: Optional[UUID]
    isKev: Optional[bool]


class VulnerabilitySearch(BaseModel):
    """VulnerabilitySearch schema."""

    page: int
    sort: Optional[str]
    order: str
    filters: Optional[VulnerabilityFilters]
    pageSize: Optional[int]
    groupBy: Optional[str]
