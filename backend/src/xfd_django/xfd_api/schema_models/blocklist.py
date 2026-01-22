"""Blocklist Schemas."""
# Third-Party Libraries
from pydantic import BaseModel, RootModel


class BlocklistCheckResponse(BaseModel):
    """BlocklistCheckResponse schema."""

    attacks: int
    reports: int


class BulkBlocklistCheckResponse(RootModel[dict[str, BlocklistCheckResponse]]):
    """BulkBlocklistCheckResponse schema."""

    root: dict[str, BlocklistCheckResponse]


class BulkBlocklistCheckRequest(BaseModel):
    """BulkBlocklistCheckRequest schema."""

    ip_addresses: list[str]
