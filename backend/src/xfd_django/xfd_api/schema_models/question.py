"""Question schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from typing import Any, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Question(BaseModel):
    """Question schema."""

    id: UUID
    name: str
    description: str
    longForm: str
    number: str
    categoryId: Optional[Any]
