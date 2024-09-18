"""Search Body schema"""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json


class SearchBody(BaseModel):
    """SearchBody schema."""

    current: int
    resultsPerPage: int
    searchTerm: str
    sortDirection: str
    sortField: str
    filters: Json[Any]
    organizationId: Optional[UUID]
    tagId: Optional[UUID]
