"""Schema models for WAS scan summaries."""
# Standard Python Libraries
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, ConfigDict, Field


class WasScanSummarySchema(BaseModel):
    """Serializable representation of a WAS scan summary for API transport."""

    summary_uid: UUID
    start_date: date
    end_date: date
    scan_identifier: List[str]
    was_org_id: str

    assets_scanned_count: int
    unique_vulnerabilities_critical: int
    unique_vulnerabilities_high: int
    unique_vulnerabilities_medium: int
    unique_vulnerabilities_low: int
    unique_vulnerabilities_info: int

    total_vulnerabilities_critical: int
    total_vulnerabilities_high: int
    total_vulnerabilities_medium: int
    total_vulnerabilities_low: int
    total_vulnerabilities_info: int

    max_age_days_critical: Optional[int]
    max_age_days_high: Optional[int]
    median_age_days_by_severity: Dict[str, float]

    kev_counts_by_severity: Dict[str, int]
    max_age_days_kevs: Optional[int]

    hosts_with_1_to_5_vulns_count: int
    hosts_with_6_to_9_vulns_count: int
    hosts_with_10_or_more_vulns_count: int
    hosts_with_vulnerability_above_info_count: int

    owasp_category_counts: Dict[str, int]
    vulnerability_type_counts: Dict[str, int]

    information_gathered_count: int
    sensitive_content_count: int

    class Config:
        """Pydantic configuration."""

        orm_mode = True
        validate_assignment = True


class GetWasScanSummariesResponse(BaseModel):
    """Envelope returned by the DMZ sync WAS endpoint for scan summaries."""

    status: str = Field("ok")
    payload: List[WasScanSummarySchema]


class WasFinding(BaseModel):
    """Serializable representation of a WAS finding for API transport."""

    finding_uid: UUID
    finding_type: Optional[str] = None
    webapp_id: Optional[int] = None
    was_org_id: Optional[str] = None
    owasp_category: Optional[str] = None
    severity: Optional[str] = None
    times_detected: Optional[int] = None
    base_score: Optional[float] = None
    temporal_score: Optional[float] = None
    fstatus: Optional[str] = None
    last_detected: Optional[date] = None
    first_detected: Optional[date] = None
    is_remediated: Optional[bool] = None
    potential: Optional[bool] = None
    webapp_url: Optional[str] = None
    webapp_name: Optional[str] = None
    name: Optional[str] = None
    cvss_v3_attack_vector: Optional[str] = None
    cwe_list: Optional[List[Optional[int]]] = None
    wasc_list: Optional[List[Dict[str, Any]]] = None
    last_tested: Optional[date] = None
    fixed_date: Optional[date] = None
    is_ignored: Optional[bool] = None
    url: Optional[str] = None
    qid: Optional[int] = None
    response: Optional[str] = None
    cve_id: Optional[UUID] = Field(default=None)
    sub_domain_id: Optional[int] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)


class GetAllWasFindingsResponse(BaseModel):
    """Envelope returned by the DMZ sync WAS endpoint."""

    status: str
    payload: list[WasFinding]
    total_pages: int
    current_page: int
