"""User event log schema."""

# Standard Python Libraries
from typing import Any, List, Optional

# Third-Party Libraries
from pydantic import BaseModel, validator


class Filter(BaseModel):
    """Filter schema."""

    value: str
    operator: Optional[str] = "contains"

    @validator("operator")
    def validate_operator(cls, v):
        """Validate operator."""
        allowed = [
            "is",
            "not",
            "after",
            "on_or_after",
            "before",
            "on_or_before",
            "empty",
            "not_empty",
        ]
        if v and v not in allowed:
            raise ValueError(f"Operator must be one of {allowed}")
        return v


class DateFilter(BaseModel):
    """Date filter schema."""

    value: str
    operator: str

    @validator("operator")
    def validate_operator(cls, v):
        """Validate operator."""
        allowed = [
            "is",
            "not",
            "after",
            "on_or_after",
            "before",
            "on_or_before",
            "empty",
            "not_empty",
        ]
        if v not in allowed:
            raise ValueError(f"Operator must be one of {allowed}")
        return v


class LogSearch(BaseModel):
    """Log search schema."""

    event_type: Optional[Filter] = None
    result: Optional[Filter] = None
    timestamp: Optional[DateFilter] = None
    payload: Optional[str] = None

    @validator("payload")
    def validate_payload(cls, v):
        """Validate payload."""
        if v:
            if not isinstance(v, str):
                raise ValueError("Payload must be a string")
        return v


class LogSearchResponse(BaseModel):
    """Log search response model."""

    result: List[Any]
    count: int
