"""Response schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Response(BaseModel):
    """Response schema."""

    id: UUID
    selection: str
    assessmentId: Optional[Any]
    questionId: Optional[Any]
