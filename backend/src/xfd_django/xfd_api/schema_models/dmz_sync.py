"""ASM sync schemas."""
# Standard Python Libraries
from datetime import datetime
from typing import List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class SyncRequest(BaseModel):
    """SyncRequest schema."""

    page: int = 1
    page_size: Optional[int] = 25
    acronym: str = "DHS"
    since_date: Optional[datetime] = None

    class Config:
        """Config."""

        from_attributes = True


class ShodanAssetItem(BaseModel):
    """Schema for a single Shodan asset."""

    shodan_asset_uid: UUID
    created_at: Optional[datetime]
    organization_name: Optional[str]
    ip_string: Optional[str]
    port: Optional[int]
    protocol: Optional[str]
    timestamp: Optional[datetime]
    product: Optional[str]
    server: Optional[str]
    tags: Optional[List[str]]
    domains: Optional[List[str]]
    hostnames: Optional[List[str]]
    isp: Optional[str]
    asn: Optional[int]
    country_code: Optional[str]
    location: Optional[str]
    organization_acronym: Optional[str]
    data_source_name: Optional[str]

    class Config:
        """Config."""

        from_attributes = True


class ShodanVulnItem(BaseModel):
    """Schema for a single Shodan vulnerability."""

    shodan_vuln_uid: UUID
    created_at: Optional[datetime]
    organization_name: Optional[str]
    ip_string: Optional[str]
    port: Optional[str]
    protocol: Optional[str]
    timestamp: Optional[datetime]
    cve: Optional[str]
    severity: Optional[str]
    cvss: Optional[int]
    summary: Optional[str]
    product: Optional[str]
    attack_vector: Optional[str]
    av_description: Optional[str]
    attack_complexity: Optional[str]
    ac_description: Optional[str]
    confidentiality_impact: Optional[str]
    ci_description: Optional[str]
    integrity_impact: Optional[str]
    ii_description: Optional[str]
    availability_impact: Optional[str]
    ai_description: Optional[str]
    tags: Optional[List[str]]
    domains: Optional[List[str]]
    hostnames: Optional[List[str]]
    isp: Optional[str]
    asn: Optional[int]
    type: Optional[str]
    name: Optional[str]
    potential_vulns: Optional[List[str]]
    mitigation: Optional[str]
    server: Optional[str]
    is_verified: Optional[bool]
    banner: Optional[str]
    version: Optional[str]
    cpe: Optional[List[str]]
    organization_acronym: Optional[str]
    data_source_name: Optional[str]

    class Config:
        """Config."""

        from_attributes = True


class ShodanVulnsAssets(BaseModel):
    """Shodan vulns ans assets schema."""

    shodan_assets: Optional[List[ShodanAssetItem]] = None
    shodan_vulns: Optional[List[ShodanVulnItem]] = None

    class Config:
        """Config."""

        from_attributes = True


class ShodanAPIMethodResponse(BaseModel):
    """Shodan API schema."""

    total_pages: int
    current_page: int
    data: Optional[ShodanVulnsAssets] = None

    class Config:
        """Config."""

        from_attributes = True


class ShodanSyncResponse(BaseModel):
    """Shodan sync response schema."""

    status: str
    payload: ShodanAPIMethodResponse

    class Config:
        """Config."""

        from_attributes = True
