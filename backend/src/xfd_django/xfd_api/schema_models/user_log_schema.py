"""User event log schema."""

# Standard Python Libraries
from datetime import datetime
from typing import Any, Dict, List, Optional

# Third-Party Libraries
from pydantic import BaseModel, validator


class Filter(BaseModel):
    """Filter schema for string-based log fields."""

    value: str
    operator: Optional[str] = "contains"

    @validator("operator")
    def validate_operator(cls, v):
        """Validate the operator for string-based filters."""
        allowed = [
            "contains",
            "equals",
            "startswith",
            "endswith",
            "isempty",
            "isnotempty",
            "isanyof",
            "doesnotcontain",
            "doesnotequal",
        ]
        if v and v not in allowed:
            raise ValueError(f"Operator must be one of {allowed}")
        return v


class DateFilter(BaseModel):
    """Date filter schema for date-based log fields."""

    value: str
    operator: str

    @validator("operator")
    def validate_operator(cls, v):
        """Validate the date operator value."""
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
    """Schema for basic log search queries."""

    event_type: Optional[Filter] = None
    result: Optional[Filter] = None
    timestamp: Optional[DateFilter] = None
    payload: Optional[str] = None

    @validator("payload")
    def validate_payload(cls, v):
        """Validate the payload value."""
        if v and not isinstance(v, str):
            raise ValueError("Payload must be a string")
        return v


class LogSearchResponse(BaseModel):
    """Response model for log search results."""

    result: List[Any]
    count: int


class LogFilterCondition(BaseModel):
    """Represents a filter condition for a log field."""

    operator: str
    value: Optional[datetime]  # Pydantic will auto-parse ISO 8601


class LogFilters(BaseModel):
    """Schema for available log filter options."""

    event_type: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[Dict[str, Any]] = None
    payload_user_email: Optional[Dict[str, Any]] = None
    payload_user_performed_assignment_email: Optional[Dict[str, Any]] = None
    payload_organization_name: Optional[Dict[str, Any]] = None
    payload_user_performed_assignment_region_id: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic config for LogFilters."""

        from_attributes = True
        arbitrary_types_allowed = True


class FilterCondition(BaseModel):
    """Represents a filter condition for log search."""

    operator: str
    value: Optional[Any] = None

    @validator("value", always=True)
    def validate_value(cls, v, values):
        """Validate the filter value based on operator."""
        operator = values.get("operator", "").lower()
        if operator == "isanyof":
            return v
        if operator in ["isempty", "isnotempty"] and v is not None:
            raise ValueError(f"Value must be null for operator '{operator}'")
        if operator not in ["isempty", "isnotempty"] and v is None:
            raise ValueError(f"Value is required for operator '{operator}'")
        return v


class LogSearchFilter(BaseModel):
    """Schema for advanced log search filters."""

    page: int = 1
    page_size: int = 15
    filters: Dict[str, FilterCondition] = {}

    @validator("filters")
    def validate_filters(cls, v):
        """Validate allowed fields and operators in filters."""
        allowed_fields = [
            "event_type",
            "result",
            "timestamp",
            "payload.user.full_name",
            "payload.user.email",
            "payload.user_performed_assignment.email",
            "payload.user_performed_assignment.full_name",
            "payload.user_to_approved.user_type",
            "payload.user.user_type",
            "payload.user_performed_assignment.region_id",
            "payload.organization.name",
            "payload.role",
            "payload.state",
        ]
        allowed_operators = [
            "contains",
            "equals",
            "startswith",
            "endswith",
            "isempty",
            "isnotempty",
            "isanyof",
            "doesnotcontain",
            "doesnotequal",
        ]
        allowed_date_operators = [
            "is empty",
            "is not empty",
            "is",
            "equals",
            "is not",
            "is after",
            "after",
            "not",
            "is on or after",
            "on or after",
            "is before",
            "before",
            "is on or before",
            "on or before",
            "isempty",
            "isnotempty",
        ]
        for field, condition in v.items():
            if field not in allowed_fields:
                raise ValueError(f"Invalid filter field: {field}")
            # Normalize the operator string
            operator = (
                condition.operator.replace("_", " ")
                .replace("-", " ")
                .replace("Or", " or ")
                .replace("And", " and ")
                .lower()
                .strip()
            )
            if field == "timestamp":
                if operator not in allowed_date_operators:
                    raise ValueError(f"Invalid operator for timestamp: {operator}")
            else:
                if operator not in allowed_operators:
                    raise ValueError(f"Invalid operator for {field}: {operator}")
        return v


class GetLogResponse(BaseModel):
    """Schema for a single log entry in the API response."""

    id: str
    event_type: str
    result: str
    created_at: str
    payload: Dict[str, Any]

    class Config:
        """Pydantic config for GetLogResponse."""

        from_attributes = True


class LogSearchResponseFilters(BaseModel):
    """Response model for filtered log search results."""

    result: List[GetLogResponse]
    count: int
