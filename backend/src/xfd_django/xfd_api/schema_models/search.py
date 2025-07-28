"""Search schemas."""
# Standard Python Libraries
from typing import Any, List, Optional

# Third-Party Libraries
from pydantic import BaseModel


# Input request schema
class Filter(BaseModel):
    """Filter."""

    field: str
    values: List[str]
    type: str


# TODO this is based on current payload just as needed
class SearchRequest(BaseModel):
    """Search request."""

    current: int
    filters: List[Filter]
    results_per_page: int
    search_term: Optional[str] = ""
    sort_direction: str = "asc"
    sort_field: str = "name"


# Response schema (based on your example)
class SearchResponse(BaseModel):
    """Search response."""

    took: int
    timed_out: bool
    _shards: Any
    hits: Any
    aggregations: Any


class DomainSearchBody(BaseModel):
    """Elastic search domain model."""

    current: Optional[int] = 1
    filters: Optional[List[dict]] = []
    resultsPerPage: Optional[int] = 15
    searchTerm: Optional[str] = ""
    sortDirection: Optional[str] = "asc"
    sortField: Optional[str] = "name"
