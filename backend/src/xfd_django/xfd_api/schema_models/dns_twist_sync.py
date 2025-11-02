"""Module containing schema models for syncing DNSTwist data."""

# Standard Python Libraries
from typing import Any

# Third-Party Libraries
from pydantic import BaseModel


class DnsTwistSyncResponse(BaseModel):
    """Response model for sync operations."""

    status: str


class DnsTwistSyncBody(BaseModel):
    """Request body for sync operations."""

    data: Any
