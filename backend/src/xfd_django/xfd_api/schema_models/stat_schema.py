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
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    sources: Optional[List[str]] = ["vs"]
    enhanced_data: Optional[bool] = False


class TrendStatsPayloadSchema(BaseModel):
    """Trend Stats Payload Schema model."""

    filters: Optional[TrendStatsFilterSchema]


class StatsComparisonPayloadSchema(BaseModel):
    """Stats Comparison request payload schema."""

    organization_id: str
    base_date: Optional[date] = Field(
        default_factory=lambda: (datetime.today() - timedelta(days=7)).date()
    )
    compare_date: Optional[date] = None
    sources: Optional[List[str]] = ["vs"]
    enhanced_data: Optional[bool] = False


class CVEItem(BaseModel):
    """CVE Item model."""

    count: int
    cve_string: str
    vuln_name: Optional[str] = None
    cvss_base_score: float
    severity_string: str


class RiskyHostStats(BaseModel):
    """Risky Host Stats model."""

    rrs: float
    low: int
    medium: int
    high: int
    critical: int
    total: int
    domain_id: Optional[str] = None


class TicketMetadata(BaseModel):
    """Ticket severity metadata."""

    severity: Optional[str]
    is_kev: Optional[bool]


class VulnScanSummaryResponse(BaseModel):
    """Vuln Scan Summary Response model."""

    id: Optional[int] = None
    summary_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization: Optional[UUID] = None
    enrolled_in_vs_timestamp: Optional[datetime] = None
    assets_owned_count: Optional[int] = None
    false_positive_count: Optional[int] = None
    vulnerable_host_count: Optional[int] = None
    unique_service_count: Optional[int] = None
    unique_low_severity_count: Optional[int] = None
    unique_medium_severity_count: Optional[int] = None
    unique_high_severity_count: Optional[int] = None
    unique_critical_severity_count: Optional[int] = None
    risky_services_count: Optional[int] = None
    unsupported_software_count: Optional[int] = None
    unique_os_count: Optional[int] = None
    low_severity_count: Optional[int] = None
    medium_severity_count: Optional[int] = None
    high_severity_count: Optional[int] = None
    critical_severity_count: Optional[int] = None
    critical_max_age: Optional[int] = None
    high_max_age: Optional[int] = None
    medium_max_age: Optional[int] = None
    low_max_age: Optional[int] = None
    low_kev_count: Optional[int] = None
    medium_kev_count: Optional[int] = None
    high_kev_count: Optional[int] = None
    critical_kev_count: Optional[int] = None
    kev_max_age: Optional[int] = None
    critical_kev_max_age: Optional[int] = None
    high_kev_max_age: Optional[int] = None
    medium_kev_max_age: Optional[int] = None
    low_kev_max_age: Optional[int] = None
    one_to_five_vulns_count: Optional[int] = None
    six_to_nine_vulns_count: Optional[int] = None
    ten_plus_vulns_count: Optional[int] = None
    top_5_occurring_cves: Optional[List[CVEItem]] = []
    top_5_occurring_kevs: Optional[List[CVEItem]] = []
    included_tickets: Optional[Dict[str, TicketMetadata]] = None
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
    scanned_asset_count: Optional[int] = 0
    port_scan_min_timestamp: Optional[datetime] = None
    port_scan_max_timestamp: Optional[datetime] = None
    vuln_scan_min_timestamp: Optional[datetime] = None
    vuln_scan_max_timestamp: Optional[datetime] = None
    net_scan1_min_timestamp: Optional[datetime] = None
    net_scan1_max_timestamp: Optional[datetime] = None
    net_scan2_min_timestamp: Optional[datetime] = None
    net_scan2_max_timestamp: Optional[datetime] = None


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
    risky_service_group_counts: Optional[dict] = {}


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


class VulnScanSummaryV2Response(BaseModel):
    """Vuln Scan Summary Response model."""

    id: Optional[int] = None
    summary_date: Optional[date] = None
    avg_summary_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization: Optional[UUID] = None
    enrolled_in_vs_timestamp: Optional[datetime] = None
    assets_owned_count: Optional[int] = None
    false_positive_count: Optional[int] = None
    vulnerable_host_count: Optional[int] = None
    unique_service_count: Optional[int] = None
    unique_low_severity_count: Optional[int] = None
    unique_medium_severity_count: Optional[int] = None
    unique_high_severity_count: Optional[int] = None
    unique_critical_severity_count: Optional[int] = None
    risky_services_count: Optional[int] = None
    unsupported_software_count: Optional[int] = None
    unique_os_count: Optional[int] = None
    low_severity_count: Optional[int] = None
    medium_severity_count: Optional[int] = None
    high_severity_count: Optional[int] = None
    critical_severity_count: Optional[int] = None
    critical_max_age: Optional[int] = None
    high_max_age: Optional[int] = None
    medium_max_age: Optional[int] = None
    low_max_age: Optional[int] = None
    low_kev_count: Optional[int] = None
    medium_kev_count: Optional[int] = None
    high_kev_count: Optional[int] = None
    critical_kev_count: Optional[int] = None
    kev_max_age: Optional[int] = None
    critical_kev_max_age: Optional[int] = None
    high_kev_max_age: Optional[int] = None
    medium_kev_max_age: Optional[int] = None
    low_kev_max_age: Optional[int] = None
    one_to_five_vulns_count: Optional[int] = None
    six_to_nine_vulns_count: Optional[int] = None
    ten_plus_vulns_count: Optional[int] = None
    top_5_occurring_cves: Optional[List[CVEItem]] = None
    top_5_occurring_kevs: Optional[List[CVEItem]] = None
    included_tickets: Optional[List[UUID]] = None
    top_5_risky_hosts: Optional[Dict[str, RiskyHostStats]] = None


class HostScanSummaryV2Response(BaseModel):
    """Host Scan Summary Response model."""

    id: Optional[int]
    summary_date: Optional[date] = None
    avg_summary_date: Optional[date] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    organization: Optional[UUID] = None

    host_done_count: Optional[int] = 0
    host_waiting_count: Optional[int] = 0
    host_running_count: Optional[int] = 0
    host_ready_count: Optional[int] = 0
    up_host_count: Optional[int] = 0
    down_host_count: Optional[int] = 0
    scanned_asset_count: Optional[int] = 0
    port_scan_min_timestamp: Optional[datetime] = None
    port_scan_max_timestamp: Optional[datetime] = None
    vuln_scan_min_timestamp: Optional[datetime] = None
    vuln_scan_max_timestamp: Optional[datetime] = None
    net_scan1_min_timestamp: Optional[datetime] = None
    net_scan1_max_timestamp: Optional[datetime] = None
    net_scan2_min_timestamp: Optional[datetime] = None
    net_scan2_max_timestamp: Optional[datetime] = None


class PortScanSummaryV2Response(BaseModel):
    """Port Scan Summary Response model."""

    id: Optional[int]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    summary_date: Optional[date] = None
    avg_summary_date: Optional[date] = None
    organization: Optional[UUID] = None

    open_port_count: Optional[int] = 0
    risky_port_count: Optional[int] = 0
    nmi_service_count: Optional[int] = 0
    unique_ip_count: Optional[int] = 0
    unique_service_count: Optional[int] = 0
    risky_service_group_counts: Optional[dict] = {}


class PortScanServiceSummaryV2Response(BaseModel):
    """Port Scan Service Summary Response model."""

    id: Optional[int]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    summary_date: Optional[date] = None
    avg_summary_date: Optional[date] = None
    organization: Optional[UUID] = None

    service_name: Optional[str] = None
    risky_ports: Optional[List[int]] = []
    unique_ip_count: Optional[int] = 0
    unique_service_count: Optional[int] = 0


class V2TrendResponse(BaseModel):
    """VS Trend Response model."""

    host_summaries: Optional[List[HostScanSummaryV2Response]] = None
    port_scan_summaries: Optional[List[PortScanSummaryV2Response]] = None
    port_scan_service_summaries: Optional[List[PortScanServiceSummaryV2Response]] = None
    vuln_scan_summaries: Optional[List[VulnScanSummaryV2Response]] = None


class V2TrendStatsPayloadSchema(BaseModel):
    """Trend Stats Payload Schema model."""

    filters: Optional[TrendStatsFilterSchema]
    fields: Optional[Dict[str, List[str]]] = None
    segment_size: Optional[int] = 14


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
    host_summary_scanned_asset_count: Optional[List[int]] = []

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
    vuln_scan_summary_unique_service_count: Optional[List[int]] = []
    vuln_scan_summary_unique_low_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_medium_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_high_severity_count: Optional[List[int]] = []
    vuln_scan_summary_unique_critical_severity_count: Optional[List[int]] = []
    vuln_scan_summary_risky_services_count: Optional[List[int]] = []
    vuln_scan_summary_unsupported_software_count: Optional[List[int]] = []
    vuln_scan_summary_unique_os_count: Optional[List[int]] = []
    vuln_scan_summary_low_severity_count: Optional[List[int]] = []
    vuln_scan_summary_medium_severity_count: Optional[List[int]] = []
    vuln_scan_summary_high_severity_count: Optional[List[int]] = []
    vuln_scan_summary_critical_severity_count: Optional[List[int]] = []
    vuln_scan_summary_critical_max_age: Optional[List[int]] = []
    vuln_scan_summary_high_max_age: Optional[List[int]] = []
    vuln_scan_summary_medium_max_age: Optional[List[int]] = []
    vuln_scan_summary_low_max_age: Optional[List[int]] = []
    vuln_scan_summary_low_kev_count: Optional[List[int]] = []
    vuln_scan_summary_medium_kev_count: Optional[List[int]] = []
    vuln_scan_summary_high_kev_count: Optional[List[int]] = []
    vuln_scan_summary_critical_kev_count: Optional[List[int]] = []
    vuln_scan_summary_kev_max_age: Optional[List[int]] = []
    vuln_scan_summary_critical_kev_max_age: Optional[List[int]] = []
    vuln_scan_summary_high_kev_max_age: Optional[List[int]] = []
    vuln_scan_summary_medium_kev_max_age: Optional[List[int]] = []
    vuln_scan_summary_low_kev_max_age: Optional[List[int]] = []
    vuln_scan_summary_one_to_five_vulns_count: Optional[List[int]] = []
    vuln_scan_summary_six_to_nine_vulns_count: Optional[List[int]] = []
    vuln_scan_summary_ten_plus_vulns_count: Optional[List[int]] = []
    vuln_scan_summary_top_5_occurring_cves: Optional[List[List[CVEItem]]] = []
    vuln_scan_summary_top_5_occurring_kevs: Optional[List[List[CVEItem]]] = []
    vuln_scan_summary_included_tickets: Optional[List[Dict[str, Dict[str, Any]]]] = []
    vuln_scan_summary_top_5_risky_hosts: Optional[List[Dict[str, RiskyHostStats]]] = []


# ---------- Base Models ----------


class BaseSummaryModel(BaseModel):
    """Base Summary Comparison Model Schema."""

    summary_date: Optional[date]
    start_date: Optional[datetime]
    end_date: Optional[datetime]


# ---------- VS Summary Model ----------


class VsSummaryModel(BaseSummaryModel):
    """Vuln Scan Summary Model Schema."""

    assets_owned_count: Optional[int]
    false_positive_count: Optional[int]
    vulnerable_host_count: Optional[int]
    unique_service_count: Optional[int]
    unique_low_severity_count: Optional[int]
    unique_medium_severity_count: Optional[int]
    unique_high_severity_count: Optional[int]
    unique_critical_severity_count: Optional[int]
    risky_services_count: Optional[int]
    unsupported_software_count: Optional[int]
    unique_os_count: Optional[int]
    low_severity_count: Optional[int]
    medium_severity_count: Optional[int]
    high_severity_count: Optional[int]
    critical_severity_count: Optional[int]
    critical_max_age: Optional[int]
    high_max_age: Optional[int]
    low_kev_count: Optional[int]
    medium_kev_count: Optional[int]
    high_kev_count: Optional[int]
    critical_kev_count: Optional[int]
    kev_max_age: Optional[int]
    one_to_five_vulns_count: Optional[int]
    six_to_nine_vulns_count: Optional[int]
    ten_plus_vulns_count: Optional[int]

    included_tickets: Optional[Dict[str, Dict[str, Any]]] = None
    top_5_occurring_cves: Optional[List[Dict[str, Any]]] = None
    top_5_occurring_kevs: Optional[List[Dict[str, Any]]] = None
    top_5_risky_hosts: Optional[Dict[str, Dict[str, Any]]] = None


# ---------- Port Summary Model ----------


class PortSummaryModel(BaseSummaryModel):
    """Port Summary Model Schema."""

    open_port_count: Optional[int]
    risky_port_count: Optional[int]
    nmi_service_count: Optional[int]
    unique_ip_count: Optional[int]
    unique_service_count: Optional[int]

    risky_service_group_counts: Optional[Dict[str, int]] = None


# ---------- Host Summary Model ----------


class HostSummaryModel(BaseSummaryModel):
    """Host Summary Model Schema."""

    host_done_count: Optional[int]
    host_waiting_count: Optional[int]
    host_running_count: Optional[int]
    host_ready_count: Optional[int]
    up_host_count: Optional[int]
    down_host_count: Optional[int]
    scanned_asset_count: Optional[int]
    port_scan_min_timestamp: Optional[datetime]
    port_scan_max_timestamp: Optional[datetime]
    vuln_scan_min_timestamp: Optional[datetime]
    vuln_scan_max_timestamp: Optional[datetime]
    net_scan1_min_timestamp: Optional[datetime]
    net_scan1_max_timestamp: Optional[datetime]
    net_scan2_min_timestamp: Optional[datetime]
    net_scan2_max_timestamp: Optional[datetime]


# ---------- Common Comparison Result ----------


class DeltaFieldChange(BaseModel):
    """Metric Delta Schema."""

    count_change: Optional[int]
    percent_change: Optional[float]
    note: Optional[str] = None


# ---------- Included Tickets Breakdown ----------


class TicketBreakdown(BaseModel):
    """Ticket comparison Breakdown schema."""

    total_count: int
    total_percent: float
    by_severity: Dict[str, int]
    by_severity_percent: Dict[str, float]
    kev_count: int
    kev_by_severity: Dict[str, int]


class IncludedTicketsComparison(BaseModel):
    """Included Tickets Comparison Schema."""

    new: TicketBreakdown
    closed: TicketBreakdown
    note: Optional[str] = None


# ---------- Scan Comparison Result Models ----------


class VsScanComparisonResult(BaseModel):
    """Vuln Scan Summary Comparison Schema."""

    base_summary: Optional[VsSummaryModel]
    compare_summary: Optional[VsSummaryModel]
    delta: Dict[str, DeltaFieldChange]
    included_tickets_comparison: Optional[IncludedTicketsComparison]


class RiskyServiceGroupChange(BaseModel):
    """Risky Service Group Change Schema."""

    base: int
    compare: int
    count_change: int
    percent_change: float
    note: Optional[str] = None


class PortScanComparisonResult(BaseModel):
    """Port Scan Comparison Schema."""

    base_summary: Optional[PortSummaryModel]
    compare_summary: Optional[PortSummaryModel]
    delta: Dict[str, DeltaFieldChange]

    risky_service_group_comparison: Optional[Dict[str, RiskyServiceGroupChange]] = None


class HostScanComparisonResult(BaseModel):
    """Host Scan Comparison schema."""

    base_summary: Optional[HostSummaryModel]
    compare_summary: Optional[HostSummaryModel]
    delta: Dict[str, DeltaFieldChange]


# ---------- Final Response Schema ----------


class StatsComparisonResponse(BaseModel):
    """Response schema for the Summary Comparison endpoint."""

    vs_scans: Optional[VsScanComparisonResult] = None
    port_scans: Optional[PortScanComparisonResult] = None
    host_scans: Optional[HostScanComparisonResult] = None
