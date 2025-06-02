"""Module containing schema models for syncing data."""

# Standard Python Libraries
from typing import Any

# Third-Party Libraries
from pydantic import BaseModel


class SyncResponse(BaseModel):
    """Response model for sync operations."""

    status: str


class SyncBody(BaseModel):
    """Request body model for sync operations."""

    data: Any
