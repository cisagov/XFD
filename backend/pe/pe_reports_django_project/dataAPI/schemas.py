"""Pydantic schemas for dnstwist PE API endpoints."""

# Standard Python Libraries
from typing import Optional

# Third-Party Libraries
from pydantic import BaseModel, ConfigDict


class DataSourceByNameInput(BaseModel):
    """Request body for data_source_by_name."""

    name: str


class DataSourceFullTable(BaseModel):
    """Serialized data_sources row."""

    data_source_uid: str
    name: str
    description: str
    last_run: str


class SubDomainsSingleInsertInput(BaseModel):
    """Request body for sub_domains_single_insert."""

    domain: str
    pe_org_uid: str
    root: bool


class SubdomainUIDByDomainInput(BaseModel):
    """Request body for subdomain_uid_by_domain."""

    domain: str


class SubdomainUIDByDomain(BaseModel):
    """Serialized sub_domain_uid lookup result."""

    sub_domain_uid: str


class RootdomainsByOrgUIDInput(BaseModel):
    """Request body for rootdomains_by_org_uid."""

    org_uid: str


class RootDomainsTable(BaseModel):
    """Serialized root_domains row."""

    model_config = ConfigDict(from_attributes=True)

    root_domain_uid: Optional[str] = None
    organizations_uid_id: Optional[str] = None
    root_domain: Optional[str] = None
    ip_address: Optional[str] = None
    data_source_uid_id: Optional[str] = None
    enumerate_subs: Optional[bool] = None


class OrganizationsFullTable(BaseModel):
    """Serialized organizations row."""

    model_config = ConfigDict(from_attributes=True)

    organizations_uid: Optional[str] = None
    name: Optional[str] = None
    cyhy_db_name: Optional[str] = None
    org_type_uid: Optional[str] = None
    report_on: Optional[bool] = None
    password: Optional[str] = None
    date_first_reported: Optional[str] = None
    parent_org_uid: Optional[str] = None
    premium_report: Optional[bool] = None
    agency_type: Optional[str] = None
    demo: Optional[bool] = None
    scorecard: Optional[bool] = None
    fceb: Optional[bool] = None
    receives_cyhy_report: Optional[bool] = None
    receives_bod_report: Optional[bool] = None
    receives_cybex_report: Optional[bool] = None
    run_scans: Optional[bool] = None
    is_parent: Optional[bool] = None
    ignore_roll_up: Optional[bool] = None
    retired: Optional[bool] = None
    cyhy_period_start: Optional[str] = None
    fceb_child: Optional[bool] = None
    election: Optional[bool] = None
    scorecard_child: Optional[bool] = None
    location_name: Optional[str] = None
    county: Optional[str] = None
    county_fips: Optional[int] = None
    state_abbreviation: Optional[str] = None
    state_fips: Optional[int] = None
    state_name: Optional[str] = None
    country: Optional[str] = None
    country_name: Optional[str] = None
