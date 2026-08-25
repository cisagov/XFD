"""Pydantic schemas for report API endpoints (from ATC CD-add-CODEOWNERS)."""
# Standard Python Libraries
from typing import List, Optional

# Third-Party Libraries
from pydantic import BaseModel


class DomainAlertsTable(BaseModel):
    """DomainAlertsTable schema class."""

    domain_alert_uid: str
    sub_domain_uid_id: Optional[str] = None
    data_source_uid_id: Optional[str] = None
    organizations_uid_id: Optional[str] = None
    alert_type: Optional[str] = None
    message: Optional[str] = None
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    date: Optional[str] = None

    class Config:
        """DomainAlertsTable schema config class."""

        orm_mode = True


# --- query_domMasq(), Issue 563
# Return all the fields of the domain_permutation table


class DomainPermuTable(BaseModel):
    """DomainPermuTable schema class."""

    suspected_domain_uid: str
    organizations_uid_id: str
    domain_permutation: Optional[str] = None
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    mail_server: Optional[str] = None
    name_server: Optional[str] = None
    fuzzer: Optional[str] = None
    date_observed: Optional[str] = None
    ssdeep_score: Optional[str] = None
    malicious: Optional[bool] = None
    blocklist_attack_count: Optional[int] = None
    blocklist_report_count: Optional[int] = None
    data_source_uid_id: Optional[str] = None
    sub_domain_uid_id: Optional[str] = None
    dshield_record_count: Optional[int] = None
    date_active: Optional[str] = None

    class Config:
        """DomainPermuTable schema config class."""

        orm_mode = True


# --- insert_roots(), Issue 564
# Return all the fields of the domain_permutation table


class RSSTable(BaseModel):
    """RSSTable schema class."""

    report_uid: Optional[str]
    organizations_uid_id: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    ip_count: Optional[int]
    root_count: Optional[int]
    sub_count: Optional[int]
    ports_count: Optional[int]
    creds_count: Optional[int]
    breach_count: Optional[int]
    cred_password_count: Optional[int]
    domain_alert_count: Optional[int]
    suspected_domain_count: Optional[int]
    insecure_port_count: Optional[int]
    verified_vuln_count: Optional[int]
    suspected_vuln_count: Optional[int]
    threat_actor_count: Optional[int]
    dark_web_alerts_count: Optional[int]
    dark_web_mentions_count: Optional[int]
    dark_web_executive_alerts_count: Optional[int]
    dark_web_asset_alerts_count: Optional[int]
    pe_number_score: Optional[str]  # ?
    pe_letter_grade: Optional[str]
    pe_percent_score: Optional[float]  # ?
    cidr_count: Optional[int]
    port_protocol_count: Optional[int]
    software_count: Optional[int]
    foreign_ips_count: Optional[int]

    class Config:
        """RSSTable schema config class."""

        orm_mode = True


# --- get_org_assets_count(), Issue 604 ---
# Get asset counts for the specified org_uid


class GenInputOrgUIDDateSingle(BaseModel):
    """GenInputOrgUIDDateSingle schema class."""

    org_uid: str
    date: str

    class Config:
        """GenInputOrgUIDDateSingle schema config class."""

        orm_mode = True


# Generalized list of org_uids input schema


class ExtraIpsByOrg(BaseModel):
    """ExtraIpsByOrg schema class."""

    ip_hash: str
    ip: str

    class Config:
        """ExtraIpsByOrg schema config class."""

        orm_mode = True


# --- set_from_cidr(), Issue 616 ---
# Set from_cidr to True for any IPs that have an origin_cidr, task resp


class GenInputOrgUIDSingle(BaseModel):
    """GenInputOrgUIDSingle schema class."""

    org_uid: str

    class Config:
        """GenInputOrgUIDSingle schema config class."""

        orm_mode = True


# Generalized 1 org cyhy_db_name input schema


class CidrsByOrg(BaseModel):
    """CidrsByOrg schema class."""

    cidr_uid: Optional[str] = None
    network: Optional[str] = None
    organizations_uid_id: Optional[str] = None
    data_source_uid_id: Optional[str] = None
    insert_alert: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    current: Optional[bool] = None

    class Config:
        """CidrsByOrg schema config class."""

        orm_mode = True


# --- query_ports_protocols(), Issue 619 ---
# Get distinct ports/protocols for specified org


class SoftwareByOrg(BaseModel):
    """SoftwareByOrg schema class."""

    product: Optional[str] = None

    class Config:
        """SoftwareByOrg schema config class."""

        orm_mode = True


# --- query_foreign_ips(), Issue 621 ---
# Get assets outside the US for specified org


class ForeignIpsByOrg(BaseModel):
    """ForeignIpsByOrg schema class."""

    shodan_asset_uid: Optional[str] = None
    organizations_uid_id: Optional[str] = None
    organization: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None
    timestamp: Optional[str] = None
    product: Optional[str] = None
    server: Optional[str] = None
    tags: Optional[List[str]] = None  # List
    domains: Optional[List[str]] = None  # List
    hostnames: Optional[List[str]] = None  # List
    isn: Optional[str] = None
    asn: Optional[int] = None
    data_source_uid_id: Optional[str] = None
    country_code: Optional[str] = None
    location: Optional[str] = None

    class Config:
        """ForeignIpsByOrg schema config class."""

        orm_mode = True


# --- query_roots(), Issue 622 ---
# Get root domains for specified org


class RootDomainsByOrg(BaseModel):
    """RootDomainsByOrg schema class."""

    root_domain_uid: Optional[str] = None
    root_domain: Optional[str] = None

    class Config:
        """RootDomainsByOrg schema config class."""

        orm_mode = True


# --- query_creds_view(), Issue 623 ---
# Uses VwBreachcomp schema


# --- query_credsbyday_view(), Issue 624 ---


# --- query_subs(), Issue 633 ---


class VwBreachcomp(BaseModel):
    """VwBreachcomp schema."""

    credential_exposures_uid: str
    email: str
    breach_name: str
    organizations_uid: str
    root_domain: str
    sub_domain: str
    hash_type: str
    name: str
    login_id: str
    password: str
    phone: str
    data_source_uid: str
    description: str
    breach_date: str
    added_date: str
    modified_date: str
    data_classes: str
    password_included: str
    is_verified: str
    is_fabricated: str
    is_sensitive: str
    is_retired: str
    is_spam_list: str


class GenInputOrgUIDDateRange(BaseModel):
    """GenInputOrgUIDDateRange schema class."""

    org_uid: str
    start_date: str
    end_date: str

    class Config:
        """GenInputOrgUIDDateRange schema config class."""


# Generalized start/end date input schema


class CredsbydateByOrg(BaseModel):
    """CredsbydateByOrg schema class."""

    mod_date: Optional[str] = None
    no_password: Optional[int] = None
    password_included: Optional[int] = None

    class Config:
        """CredsbydateByOrg schema config class."""

        orm_mode = True


# --- query_breachdetails_view(), Issue 625 ---


class BreachdetailsByOrg(BaseModel):
    """BreachdetailsByOrg schema class."""

    breach_name: Optional[str] = None
    mod_date: Optional[str] = None
    breach_date: Optional[str] = None
    password_included: Optional[int] = None
    number_of_creds: Optional[int] = None

    class Config:
        """BreachdetailsByOrg schema config class."""

        orm_mode = True


# --- query_shodan(), Issue 628 ---


class DarkWebDataInput(BaseModel):
    """DarkWebDataInput schema class."""

    org_uid: str
    start_date: str
    end_date: str
    table: str

    class Config:
        """DarkWebDataInput schema config class."""

        orm_mode = True


# --- query_darkweb(), Issue 629 ---


class TopCvesTable(BaseModel):
    """TopCvesRecord schema class."""

    top_cves_uid: Optional[str] = None
    cve_id: Optional[str] = None
    dynamic_rating: Optional[str] = None
    nvd_base_score: Optional[str] = None
    date: Optional[str] = None
    summary: Optional[str] = None
    data_source_uid_id: Optional[str] = None

    class Config:
        """TopCvesRecord schema config class."""

        orm_mode = True


class RSSInsertInput(BaseModel):
    """RSSInsertInput schema class."""

    organizations_uid: str
    start_date: str
    end_date: str
    ip_count: int
    root_count: int
    sub_count: int
    num_ports: int  # ports_count: int
    creds_count: int
    breach_count: int
    cred_password_count: int
    domain_alert_count: int
    suspected_domain_count: int
    insecure_port_count: int
    verified_vuln_count: int
    suspected_vuln_count: int
    suspected_vuln_addrs_count: int
    threat_actor_count: int
    dark_web_alerts_count: int
    dark_web_mentions_count: int
    dark_web_executive_alerts_count: int
    dark_web_asset_alerts_count: int
    pe_number_score: str  # may be "NA"
    pe_letter_grade: str  # may be "NA"
    cidr_count: int
    port_protocol_count: int
    software_count: int
    foreign_ips_count: int

    class Config:
        """RSSInsertInput schema config class."""

        orm_mode = True


# --- query_previous_period(), Issue 634 ---
# Get prev. report period data from report_summary_stats


class SubDomainTable(BaseModel):
    """SubDomainTable schema class."""

    sub_domain_uid: Optional[str] = None
    sub_domain: Optional[str] = None
    root_domain_uid_id: Optional[str] = None
    root_domain_uid__root_domain: Optional[str] = None
    data_source_uid_id: Optional[str] = None
    dns_record_uid_id: Optional[str] = None
    status: Optional[bool] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    current: Optional[bool] = None
    identified: Optional[bool] = None

    class Config:
        """SubDomainTable schema config class."""

        orm_mode = True


class SubDomainPagedResult(BaseModel):
    """SubDomainPagedResult schema class."""

    total_pages: int
    current_page: int
    data: List[SubDomainTable]


class SubDomainPagedInput(BaseModel):
    """SubDomainPagedInput schema class."""

    org_uid: str
    page: int
    per_page: int

    class Config:
        """SubDomainPagedInput schema config class."""

        orm_mode = True


# --- query_darkweb_cves(), Issue 630 ---


class RSSPrevPeriod(BaseModel):
    """RSSPrevPeriod schema class."""

    ip_count: Optional[int] = None
    root_count: Optional[int] = None
    sub_count: Optional[int] = None
    cred_password_count: Optional[int] = None
    suspected_vuln_addrs_count: Optional[int] = None
    suspected_vuln_count: Optional[int] = None
    insecure_port_count: Optional[int] = None
    threat_actor_count: Optional[int] = None

    class Config:
        """RSSPrevPeriod schema config class."""

        orm_mode = True


# --- query_previous_period(), Issue 634 ---
# Get prev. report period data from report_summary_stats, input


class RSSPrevPeriodInput(BaseModel):
    """RSSPrevPeriodInput schema class."""

    org_uid: str
    prev_end_date: str

    class Config:
        """RSSPrevPeriodInput schema config class."""

        orm_mode = True
