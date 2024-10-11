"""Saved Search schemas."""
# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class SavedSearch(BaseModel):
    """SavedSearch schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    search_term: str
    sort_direction: str
    sort_field: str
    count: int
    filters: List[Dict[str, Any]]


class SavedSearchFilters(BaseModel):
    """SavedSearchFilters schema."""

    id: Optional[UUID]
    name: Optional[str]
    sort_direction: Optional[str]
    sort_field: Optional[str]
    search_term: Optional[str]
    search_path: Optional[str]
    created_by: Optional[UUID]


class SavedSearchSearch(BaseModel):
    """SavedSearchSearch schema."""

    page: int
    sort: Optional[str]
    order: str
    filters: Optional[SavedSearchFilters]
    pageSize: Optional[int]
    groupBy: Optional[str]
