"""Pydantic schemas for dnstwist PE API endpoints."""

# Standard Python Libraries
from typing import List, Optional

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
    exec_url: Optional[str] = None


class DNSMonitorDomainMapTable(BaseModel):
    """Serialized dnsmonitor_domain_map row."""

    model_config = ConfigDict(from_attributes=True)

    dnsmonitor_domain_map_uid: Optional[str] = None
    domain: Optional[str] = None
    organization: Optional[str] = None
    date: Optional[str] = None


class DomainPermuInsert(BaseModel):
    """Individual row of request body for domain_permu_insert."""

    organizations_uid: str
    sub_domain_uid: Optional[str] = None
    data_source_uid: Optional[str] = None
    domain_permutation: str
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    mail_server: Optional[str] = None
    name_server: Optional[str] = None
    date_observed: Optional[str] = None


class DomainPermuInsertInput(BaseModel):
    """Request body for domain_permu_insert."""

    insert_data: List[DomainPermuInsert]


class DomainAlertsInsert(BaseModel):
    """Individual row of request body for domain_alerts_insert."""

    organizations_uid: str
    sub_domain_uid: Optional[str] = None
    data_source_uid: Optional[str] = None
    alert_type: Optional[str] = None
    message: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    date: Optional[str] = None


class DomainAlertsInsertInput(BaseModel):
    """Request body for domain_alerts_insert."""

    insert_data: List[DomainAlertsInsert]


# --- insert_shodan_assets(), Issue 016 atc-framework ---
# Insert bulk Shodan data into shodan_assets table
class ShodanAssetsInsert(BaseModel):
    """ShodanAssetsInsert schema class."""

    model_config = ConfigDict(from_attributes=True)

    organizations_uid: Optional[str] = None
    organization: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    timestamp: Optional[str] = None
    product: Optional[str] = None
    server: Optional[str] = None
    tags: Optional[List[str]] = None
    domains: Optional[List[str]] = None
    hostnames: Optional[List[str]] = None
    isn: Optional[str] = None
    asn: Optional[int] = None
    data_source_uid: Optional[str] = None
    country_code: Optional[str] = None
    location: Optional[str] = None


# --- insert_shodan_assets(), Issue 016 atc-framework ---
# Insert bulk Shodan data into shodan_assets table, input
class ShodanAssetsInsertInput(BaseModel):
    """ShodanAssetsInsertInput schema class."""

    model_config = ConfigDict(from_attributes=True)

    asset_data: List[ShodanAssetsInsert]


# --- insert_shodan_vulns(), Issue 017 atc-framework ---
# Insert bulk Shodan data into shodan_vulns table
class ShodanVulnsInsert(BaseModel):
    """ShodanVulnsInsert schema class."""

    model_config = ConfigDict(from_attributes=True)

    organizations_uid: Optional[str] = None
    organization: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    timestamp: Optional[str] = None
    cve: Optional[str] = None
    severity: Optional[str] = None
    cvss: Optional[float] = None
    summary: Optional[str] = None
    product: Optional[str] = None
    attack_vector: Optional[str] = None
    av_description: Optional[str] = None
    attack_complexity: Optional[str] = None
    ac_description: Optional[str] = None
    confidentiality_impact: Optional[str] = None
    ci_description: Optional[str] = None
    integrity_impact: Optional[str] = None
    ii_description: Optional[str] = None
    availability_impact: Optional[str] = None
    ai_description: Optional[str] = None
    tags: Optional[List[str]] = None
    domains: Optional[List[str]] = None
    hostnames: Optional[List[str]] = None
    isn: Optional[str] = None
    asn: Optional[int] = None
    data_source_uid: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    potential_vulns: Optional[List[str]] = None
    mitigation: Optional[str] = None
    server: Optional[str] = None
    is_verified: Optional[bool] = None
    banner: Optional[str] = None
    version: Optional[str] = None
    cpe: Optional[List[str]] = None


# --- insert_shodan_vulns(), Issue 017 atc-framework ---
# Insert bulk Shodan data into shodan_vulns table, input
class ShodanVulnsInsertInput(BaseModel):
    """ShodanVulnsInsertInput schema class."""

    model_config = ConfigDict(from_attributes=True)

    vuln_data: List[ShodanVulnsInsert]


# Insert bulk Shodan data into top_cves table
class ShodanTopCvesInsert(BaseModel):
    """ShodanTopCvesInsert schema class."""

    model_config = ConfigDict(from_attributes=True)

    cve_id: Optional[str] = None
    dynamic_rating: Optional[str] = None
    nvd_base_score: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None
    data_source_uid: Optional[str] = None


# Insert bulk Shodan data into top_cves table, input
class ShodanTopCvesInsertInput(BaseModel):
    """ShodanTopCvesInsertInput schema class."""

    model_config = ConfigDict(from_attributes=True)

    top_epss_cves_dict: List[ShodanTopCvesInsert]
