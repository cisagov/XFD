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
    createdAt: datetime
    updatedAt: datetime
    name: str
    searchTerm: str = ""
    sortDirection: str
    sortField: str
    count: int
    filters: List[SavedSearchFilters]
    searchPath: str
    createdById: UUID
