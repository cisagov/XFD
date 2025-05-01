"""Stats schema."""
# Standard Python Libraries
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Field


# Reusing the previously defined models
class ServiceStat(BaseModel):
    """Service stat."""

    id: str
    value: int
    label: str


class PortStat(BaseModel):
    """Port stat."""

    id: int
    value: int
    label: str


class VulnerabilityStat(BaseModel):
    """Vulnerability stat."""

    id: str
    value: int
    label: str


class SeverityCountStat(BaseModel):
    """Severity count stat."""

    id: str
    value: int
    label: str


class Domain(BaseModel):
    """Domain schema."""

    id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime]
    ip: Optional[str]
    from_root_domain: Optional[str]
    subdomain_source: Optional[str]
    ip_only: Optional[bool]
    reverse_name: Optional[str]
    name: Optional[str]
    screenshot: Optional[str]
    country: Optional[str]
    asn: Optional[str]
    cloud_hosted: Optional[bool]
    from_cidr: Optional[bool]
    is_fceb: Optional[bool]
    ssl: Optional[dict]
    censys_certificates_results: Optional[dict]
    trustymail_results: Optional[dict]


class LatestVulnerability(BaseModel):
    """Latest vulnerability."""

    created_at: datetime
    title: str
    description: Optional[str]
    severity: Optional[str]


class MostCommonVulnerability(BaseModel):
    """Most common vulnerability."""

    title: str
    description: str
    severity: Optional[str]
    count: int


class ByOrgStat(BaseModel):
    """By org stat."""

    id: str
    org_id: str
    value: int
    label: str


# Main StatsResponse model
class StatsResponse(BaseModel):
    """Stats response."""

    result: Dict[str, Any] = {
        "domains": {
            "services": List[ServiceStat],
            "ports": List[PortStat],
            "num_vulnerabilities": List[VulnerabilityStat],
            "total": int,
        },
        "vulnerabilities": {
            "severity": List[SeverityCountStat],
            "latest_vulnerabilities": List[LatestVulnerability],
            "most_common_vulnerabilities": List[MostCommonVulnerability],
            "by_org": List[ByOrgStat],
        },
    }


class TrendStatsFilterSchema(BaseModel):
    """Filter options for trend statistics queries."""

    organization_id: str
    start_date: Optional[date] = Field(
        default_factory=lambda: (
            datetime.today() - timedelta(days=180)
        ).date()  # Using `datetime.today()`
    )
    end_date: Optional[date] = Field(
        default_factory=lambda: datetime.today().date()  # Using `datetime.today()`
    )
    sources: Optional[List[str]] = ["vs"]
    enhanced_data: Optional[bool] = False


class TrendStatsPayloadSchema(BaseModel):
    """Trend Stats Payload Schema model."""

    filters: Optional[TrendStatsFilterSchema]


class CVEItem(BaseModel):
    """CVE Item model."""

    count: int
    cve_string: str
    vuln_name: Optional[str] = None
    cvss_base_score: float
    severity_string: str


class RiskyHostStats(BaseModel):
    """Risky Host Stats model."""

    low: int
    rrs: float
    high: int
    total: int
    medium: int
    critical: int


class VulnScanSummaryResponse(BaseModel):
    """Vuln Scan Summary Response model."""

    id: Optional[int] = None
    summary_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization: Optional[UUID] = None
    asset_count: Optional[int] = None
    false_positive_count: Optional[int] = None
    vulnerable_host_count: Optional[int] = None
    scanned_asset_count: Optional[int] = None
    unique_service_count: Optional[int] = None
    unique_none_severity_count: Optional[int] = None
    unique_low_severity_count: Optional[int] = None
    unique_medium_severity_count: Optional[int] = None
    unique_high_severity_count: Optional[int] = None
    unique_critical_severity_count: Optional[int] = None
    risky_services_count: Optional[int] = None
    unsupported_software_count: Optional[int] = None
    unique_os_count: Optional[int] = None
    none_severity_count: Optional[int] = None
    low_severity_count: Optional[int] = None
    medium_severity_count: Optional[int] = None
    high_severity_count: Optional[int] = None
    critical_severity_count: Optional[int] = None
    critical_max_age: Optional[int] = None
    high_max_age: Optional[int] = None
    none_kev_count: Optional[int] = None
    low_kev_count: Optional[int] = None
    medium_kev_count: Optional[int] = None
    high_kev_count: Optional[int] = None
    critical_kev_count: Optional[int] = None
    kev_max_age: Optional[int] = None
    one_to_five_vulns_count: Optional[int] = None
    six_to_nine_vulns_count: Optional[int] = None
    ten_plus_vulns_count: Optional[int] = None
    top_5_occurring_cves: Optional[List[CVEItem]] = []
    top_5_occurring_kevs: Optional[List[CVEItem]] = []
    included_tickets: Optional[List[UUID]] = None
    top_5_risky_hosts: Optional[Dict[str, RiskyHostStats]] = {}


class HostScanSummaryResponse(BaseModel):
    """Host Scan Summary Response model."""

    id: int
    summary_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization: Optional[UUID] = None

    host_done_count: Optional[int] = 0
    host_waiting_count: Optional[int] = 0
    host_running_count: Optional[int] = 0
    host_ready_count: Optional[int] = 0
    up_host_count: Optional[int] = 0
    down_host_count: Optional[int] = 0


class PortScanSummaryResponse(BaseModel):
    """Port Scan Summary Response model."""

    id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    summary_date: Optional[date] = None
    organization: Optional[UUID] = None

    open_port_count: Optional[int] = 0
    risky_port_count: Optional[int] = 0
    nmi_service_count: Optional[int] = 0
    unique_ip_count: Optional[int] = 0
    unique_service_count: Optional[int] = 0


class PortScanServiceSummaryResponse(BaseModel):
    """Port Scan Service Summary Response model."""

    id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    summary_date: Optional[date] = None
    organization: Optional[UUID] = None

    service_name: Optional[str] = None
    risky_ports: Optional[List[int]] = []
    unique_ip_count: Optional[int] = 0
    unique_service_count: Optional[int] = 0


class VsTrendResponse(BaseModel):
    """VS Trend Response model."""

    host_summaries: Optional[List[HostScanSummaryResponse]] = None
    port_scan_summaries: Optional[List[PortScanSummaryResponse]] = None
    port_scan_service_summaries: Optional[List[PortScanServiceSummaryResponse]] = None
    vuln_scan_summaries: Optional[List[VulnScanSummaryResponse]] = None


class VsTrendCondensedResponse(BaseModel):
    """Response schema for the VS Trend Condensed endpoint."""

    host_summary_id: Optional[List[int]] = []
    host_summary_summary_date: Optional[List[date]] = []
    host_summary_start_date: Optional[List[datetime]] = []
    host_summary_end_date: Optional[List[datetime]] = []
    host_summary_organization: Optional[List[UUID]] = []
    host_summary_host_done_count: Optional[List[int]] = []
    host_summary_host_waiting_count: Optional[List[int]] = []
    host_summary_host_running_count: Optional[List[int]] = []
    host_summary_host_ready_count: Optional[List[int]] = []
    host_summary_up_host_count: Optional[List[int]] = []
    host_summary_down_host_count: Optional[List[int]] = []

    port_scan_summary_id: Optional[List[int]] = []
    port_scan_summary_start_date: Optional[List[datetime]] = []
    port_scan_summary_end_date: Optional[List[datetime]] = []
    port_scan_summary_summary_date: Optional[List[date]] = []
    port_scan_summary_organization: Optional[List[UUID]] = []
    port_scan_summary_open_port_count: Optional[List[int]] = []
    port_scan_summary_risky_port_count: Optional[List[int]] = []
    port_scan_summary_nmi_service_count: Optional[List[int]] = []
    port_scan_summary_unique_ip_count: Optional[List[int]] = []
    port_scan_summary_unique_service_count: Optional[List[int]] = []
    port_scan_service_summary_id: Optional[List[int]] = []
    port_scan_service_summary_start_date: Optional[List[datetime]] = []
    port_scan_service_summary_end_date: Optional[List[datetime]] = []
    port_scan_service_summary_summary_date: Optional[List[date]] = []
    port_scan_service_summary_organization: Optional[List[UUID]] = []
    port_scan_service_summary_service_name: Optional[List[str]] = []
    port_scan_service_summary_risky_ports: Optional[List[List[int]]] = []
    port_scan_service_summary_unique_ip_count: Optional[List[int]] = []
    port_scan_service_summary_unique_service_count: Optional[List[int]] = []

    vuln_scan_summary_id: Optional[List[int]] = []
    vuln_scan_summary_summary_date: Optional[List[date]] = []
    vuln_scan_summary_start_date: Optional[List[datetime]] = []
    vuln_scan_summary_end_date: Optional[List[datetime]] = []
    vuln_scan_summary_organization: Optional[List[UUID]] = []
    vuln_scan_summary_asset_count: Optional[List[int]] = []
    vuln_scan_summary_false_positive_count: Optional[List[int]] = []
    vuln_scan_summary_vulnerable_host_count: Optional[List[int]] = []
    vuln_scan_summary_scanned_asset_count: Optional[List[int]] = []
    vuln_scan_summary_unique_service_count: Optional[List[int]] = []
    vuln_scan_summary_unique_none_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_low_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_medium_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_high_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_critical_severity_count: Optional[List[int]] = []
    vuln_scan_summary_risky_services_count: Optional[List[int]] = []
    vuln_scan_summary_unsupported_software_count: Optional[List[int]] = []
    vuln_scan_summary_unique_os_count: Optional[List[int]] = []
    vuln_scan_summary_none_severity_count: Optional[List[int]] = []
    vuln_scan_summary_low_severity_count: Optional[List[int]] = []
    vuln_scan_summary_medium_severity_count: Optional[List[int]] = []
    vuln_scan_summary_high_severity_count: Optional[List[int]] = []
    vuln_scan_summary_critical_severity_count: Optional[List[int]] = []
    vuln_scan_summary_critical_max_age: Optional[List[int]] = []
    vuln_scan_summary_high_max_age: Optional[List[int]] = []
    vuln_scan_summary_none_kev_count: Optional[List[int]] = []
    vuln_scan_summary_low_kev_count: Optional[List[int]] = []
    vuln_scan_summary_medium_kev_count: Optional[List[int]] = []
    vuln_scan_summary_high_kev_count: Optional[List[int]] = []
    vuln_scan_summary_critical_kev_count: Optional[List[int]] = []
    vuln_scan_summary_kev_max_age: Optional[List[int]] = []
    vuln_scan_summary_one_to_five_vulns_count: Optional[List[int]] = []
    vuln_scan_summary_six_to_nine_vulns_count: Optional[List[int]] = []
    vuln_scan_summary_ten_plus_vulns_count: Optional[List[int]] = []
    vuln_scan_summary_top_5_occurring_cves: Optional[List[List[CVEItem]]] = []
    vuln_scan_summary_top_5_occurring_kevs: Optional[List[List[CVEItem]]] = []
    vuln_scan_summary_included_tickets: Optional[List[List[UUID]]] = []
    vuln_scan_summary_top_5_risky_hosts: Optional[List[Dict[str, RiskyHostStats]]] = []
