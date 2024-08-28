# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, EmailStr, Field, Json


class Cpe(BaseModel):
    id: UUID
    name: Optional[str]
    version: Optional[str]
    vendor: Optional[str]
    lastSeenAt: datetime


class Cve(BaseModel):
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
    ports: Optional[str] = None
    service: Optional[str] = None
    reverseName: Optional[str] = None
    ip: Optional[str] = None
    organization: Optional[str] = None
    organizationName: Optional[str] = None
    vulnerabilities: Optional[str] = None
    tag: Optional[str] = None


class DomainSearch(BaseModel):
    page: int = 1
    sort: str
    order: str
    filters: Optional[DomainFilters]
    pageSize: Optional[int] = None


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


class SearchBody(BaseModel):
    current: int
    resultsPerPage: int
    searchTerm: str
    sortDirection: str
    sortField: str
    filters: Json[Any]
    organizationId: Optional[UUID]
    tagId: Optional[UUID]


class User(BaseModel):
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
    page: int
    sort: Optional[str]
    order: str
    filters: Optional[VulnerabilityFilters]
    pageSize: Optional[int]
    groupBy: Optional[str]
