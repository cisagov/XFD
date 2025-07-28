"""Queue monitoring schemas."""
# Standard Python Libraries
from typing import List, Optional

# Third-Party Libraries
from pydantic import BaseModel


class QueueSearch(BaseModel):
    """Queue search schema."""

    page: int = 1
    sort: Optional[str] = "ASC"
    order: Optional[str] = "id"
    filters: Optional[dict] = None
    page_size: Optional[int] = 25


class QueueMetadata(BaseModel):
    """Queue metadata."""

    name: str
    messages_available: int
    messages_in_flight: int
    messages_delayed: int


class QueueListResponse(BaseModel):
    """Queue list response."""

    result: List[QueueMetadata]
    count: int
