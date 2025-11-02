"""Saved Search schemas."""
# Standard Python Libraries
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class SavedSearchFilters(BaseModel):
    """SavedSearchFilters schema."""

    type: Optional[str]
    field: str
    values: List[Any]


class SavedSearchCreate(BaseModel):
    """Saved search create."""

    name: str
    search_term: str
    sort_direction: str
    sort_field: str
    count: int
    filters: List[SavedSearchFilters]
    search_path: str


class SavedSearchUpdate(BaseModel):
    """Saved search update."""

    name: str
    search_term: str
    sort_direction: str
    sort_field: str
    count: int
    filters: List[SavedSearchFilters]
    search_path: str


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
    filters: List[SavedSearchFilters]
    search_path: str
    created_by_id: UUID


class SavedSearchList(BaseModel):
    """SavedSearchList schema."""

    result: List[SavedSearch]
    count: int
