"""Saved Search schemas."""
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json


class SavedSearch(BaseModel):
    """SavedSearch schema."""

    id: UUID
    name: str
    count: int
    sort_direction: str
    sort_field: str
    search_term: str
    search_path: str
    filters: Json[Any]
    created_at: datetime
    updated_at: datetime


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
