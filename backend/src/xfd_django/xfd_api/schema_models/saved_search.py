"""Saved Search schemas."""
# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class SavedSearchFilters(BaseModel):
    """SavedSearchFilters schema."""

    field: str
    values: List[Any]


class SavedSearch(BaseModel):
    """SavedSearch schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    search_term: str = ""
    sort_direction: str
    sort_field: str
    count: int
    filters: List[SavedSearchFilters]
    search_path: str
    createdBy_id: UUID
