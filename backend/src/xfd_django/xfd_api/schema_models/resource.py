"""Resource schema."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class Resource(BaseModel):
    """Resource schema."""

    id: UUID
    description: str
    name: str
    type: str
    url: str

    class Config:
        from_attributes = True
