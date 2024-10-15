"""Category Schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from typing import Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Category(BaseModel):
    """Category schema."""

    id: UUID
    name: str
    number: str
    shortName: Optional[str]

    class Config:
        from_attributes = True
