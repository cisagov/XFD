"""Schema models for WAS synchronization."""
# Standard Python Libraries
from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, ConfigDict, Field


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
