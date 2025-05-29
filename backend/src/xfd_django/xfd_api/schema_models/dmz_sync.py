"""DmzSync API."""
# Standard Python Libraries
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Field


class SixgillAlert(BaseModel):
    """A single CyberSix alert record."""

    alerts_uid: UUID
    alert_name: Optional[str] = None
    content: Optional[str] = None
    date: Optional[datetime] = None
    sixgill_id: Optional[str] = None
    read: Optional[str] = None
    severity: Optional[str] = None
    site: Optional[str] = None
    threat_level: Optional[str] = None
    threats: Optional[str] = None
    title: Optional[str] = None
    user_id: Optional[str] = None
    category: Optional[str] = None
    lang: Optional[str] = None
    organization_id: UUID
    data_source_id: UUID
    content_snip: Optional[str] = None
    asset_mentioned: Optional[str] = None
    asset_type: Optional[str] = None


class Mentions(BaseModel):
    """A single CyberSix mention record."""

    mentions_uid: UUID
    category: Optional[str] = None
    collection_date: Optional[datetime] = None
    content: Optional[str] = None
    creator: Optional[str] = None
    date: Optional[datetime] = None
    sixgill_mention_id: str
    post_id: Optional[str] = None
    lang: Optional[str] = None
    rep_grade: Optional[str] = None
    site: Optional[str] = None
    site_grade: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    comments_count: Optional[str] = None
    sub_category: Optional[str] = None
    tags: Optional[str] = None
    title_translated: Optional[str] = None
    content_translated: Optional[str] = None
    detected_lang: Optional[str] = None
    organization_id: UUID
    data_source_id: UUID


class CredentialBreach(BaseModel):
    """A single CyberSix credential breach record."""

    credential_breaches_uid: UUID
    breach_name: str
    description: Optional[str] = None
    exposed_cred_count: Optional[int] = None
    breach_date: Optional[date] = None
    added_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    data_classes: Optional[List[str]] = None
    password_included: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_fabricated: Optional[bool] = None
    is_sensitive: Optional[bool] = None
    is_retired: Optional[bool] = None
    is_spam_list: Optional[bool] = None
    data_source_id: UUID


class CredentialExposure(BaseModel):
    """A single CyberSix credential exposure record."""

    credential_exposures_uid: UUID
    email: str
    organization_id: UUID
    root_domain: Optional[str] = None
    sub_domain_string: Optional[str] = None
    sub_domain_id: Optional[UUID] = None
    breach_name: Optional[str] = None
    modified_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    credential_breach_id: UUID
    data_source_id: Optional[UUID] = None
    name: Optional[str] = None
    login_id: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    hash_type: Optional[str] = None
    intelx_system_id: Optional[str] = None


class SubDomain(BaseModel):
    """A single CyberSix subdomain record."""

    sub_domain_uid: UUID
    sub_domain: str
    root_domain_id: Optional[UUID] = None
    is_root_domain: Optional[bool] = None
    data_source_id: UUID
    dns_record_id: Optional[UUID] = None
    status: Optional[bool] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    current: Optional[bool] = None
    identified: Optional[bool] = None
    ip_address: Optional[str] = None
    synced_at: Optional[datetime] = None
    from_root_domain: Optional[str] = None
    enumerate_subs: Optional[bool] = None
    subdomain_source: Optional[str] = None
    organization_id: UUID
    ip_only: Optional[bool] = None
    reverse_name: str
    screenshot: Optional[str] = None
    country: Optional[str] = None
    asn: Optional[str] = None
    cloud_hosted: Optional[bool] = None
    ssl: Optional[dict] = None
    censys_certificates_results: dict
    trustymail_results: dict


class TopCve(BaseModel):
    """A single CyberSix top CVE record."""

    top_cves_uid: UUID
    cve_id: Optional[str] = None
    dynamic_rating: Optional[str] = None
    nvd_base_score: Optional[str] = None
    date: Optional[datetime] = None
    summary: Optional[str] = None
    data_source_id: UUID


class CybersixPayload(BaseModel):
    """The payload of the CyberSixSyncResponse."""

    alerts: List[SixgillAlert]
    mentions: List[Mentions]
    breaches: List[CredentialBreach]
    exposures: List[CredentialExposure]
    subdomains: List[SubDomain]
    topcves: List[TopCve]

    current_page: int = Field(
        ..., ge=1, description="Which page this payload represents"
    )
    total_pages: int = Field(
        ..., ge=1, description="How many pages are available in total"
    )


class CybersixSyncResponse(BaseModel):
    """The response model for the CyberSixSync API."""

    status: str
    payload: CybersixPayload
