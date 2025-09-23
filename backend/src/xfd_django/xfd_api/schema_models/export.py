"""Export schema."""

# Standard Python Libraries
from datetime import date, timedelta
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union

# Third-Party Libraries
from pydantic import BaseModel, Field

# Misc Schemas ---------------------------------------


class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# Filter Schemas ---------------------------------------


class SummaryFilters(BaseModel):
    """SummaryFilters schema."""

    begin_date: Optional[date] = Field(default_factory=date.today)
    end_date: Optional[date] = Field(
        default_factory=lambda: date.today() - timedelta(days=30)
    )
    org_id: Optional[str] = None
    region_id: Optional[str] = None
    source: Optional[str] = "vs"

    class Config:
        """Config."""

        extra = "forbid"


DEFAULT_VULN_SEVERITY = [
    VulnerabilitySeverity.low,
    VulnerabilitySeverity.medium,
    VulnerabilitySeverity.high,
    VulnerabilitySeverity.critical,
]


class VulnerabilityFilters(BaseModel):
    """VulnerabilityFilters schema."""

    ticket_false_positive: Optional[bool] = True
    ticket_open: Optional[bool] = True
    org_id: Optional[str] = None
    region_id: Optional[str] | Optional[list[str]] = None
    source: Optional[str] = "vs"
    severity: Optional[list[VulnerabilitySeverity]] = DEFAULT_VULN_SEVERITY
    known_kev: Optional[str] = "all"  # all, known, unknown

    class Config:
        """Config."""

        extra = "forbid"


# Filter Schemas ---------------------------------------


# Column Schemas ---------------------------------------


class SummaryCol(str, Enum):
    """Summary column names."""

    organization_id = "organization_id"
    summary_date = "summary_date"
    assets_owned_count = "assets_owned_count"
    risky_services_count = "risky_services_count"
    unique_os_count = "unique_os_count"
    low_severity_count = "low_severity_count"
    medium_severity_count = "medium_severity_count"
    high_severity_count = "high_severity_count"
    critical_severity_count = "critical_severity_count"
    low_kev_count = "low_kev_count"
    medium_kev_count = "medium_kev_count"
    high_kev_count = "high_kev_count"
    critical_kev_count = "critical_kev_count"


DEFAULT_SUMMARY_COLS: list[SummaryCol] = [
    SummaryCol.summary_date,
    SummaryCol.assets_owned_count,  # Ticket wants scanned_asset_count
    SummaryCol.low_kev_count,
    SummaryCol.medium_kev_count,
    SummaryCol.high_kev_count,
    SummaryCol.critical_kev_count,
]


class VulnerabilityCol(str, Enum):
    """Vulnerability column names."""

    organization_id = "organization_id"
    ip_string = "ip_string"
    port = "port"
    protocol = "protocol"
    severity = "severity"
    is_kev = "is_kev"
    is_kev_ransomware = "is_kev_ransomware"
    opened_timestamp = "opened_timestamp"
    updated_timestamp = "updated_timestamp"
    closed_timestamp = "closed_timestamp"
    cvss_base_score = "cvss_base_score"
    cvss_version = "cvss_version"
    cvss_score_source = "cvss_score_source"
    vpr_score = "vpr_score"
    cve_string = "cve_string"
    vuln_name = "vuln_name"
    synopsis = "synopsis"
    description = "description"
    solution = "solution"
    plugin_id = "plugin_id"
    plugin_output = "plugin_output"
    operating_system = "operating_system"
    false_positive = "false_positive"
    risky_service_group = "risky_service_group"
    is_open = "is_open"
    # age = "age" # Is this computed on mat_vw_combined_vulns refresh


DEFAULT_VULNERABILITY_COLS: list[VulnerabilityCol] = [
    VulnerabilityCol.ip_string,
    VulnerabilityCol.severity,
    VulnerabilityCol.vuln_name,
    VulnerabilityCol.synopsis,
    VulnerabilityCol.description,
    VulnerabilityCol.is_open,
]

# Column Schemas ---------------------------------------


# Payload Schemas ---------------------------------------
class SummaryPayload(BaseModel):
    """SummaryPayload schema."""

    mode: Union[Literal["csv"], Literal["json"]]
    collection: Literal["summary"]
    filters: SummaryFilters
    columns: list[SummaryCol] | None = DEFAULT_SUMMARY_COLS


class VulnerabilityPayload(BaseModel):
    """VulnerabilityPayload schema."""

    mode: Union[Literal["csv"], Literal["json"]]
    collection: Literal["vulnerability"]
    filters: VulnerabilityFilters
    columns: list[VulnerabilityCol] | None = DEFAULT_VULNERABILITY_COLS
    # Add extra filter that specifies we do tickets or scanning collection?


# Payload Schemas ---------------------------------------


# Response Schemas  ---------------------------------------
class SummaryResult(BaseModel):
    """Summary result."""

    mode: Union[Literal["csv"], Literal["json"]]
    collection: Literal["summary"]
    data: Any


class VulnerabilityResult(BaseModel):
    """Vulnerability result."""

    mode: Union[Literal["csv"], Literal["json"]]
    collection: Literal["vulnerability"]
    data: Any


# Response Schemas  ---------------------------------------


ExportPayload = Annotated[
    Union[SummaryPayload, VulnerabilityPayload], Field(discriminator="collection")
]

ExportResponse = Annotated[
    Union[SummaryResult, VulnerabilityResult], Field(discriminator="collection")
]
