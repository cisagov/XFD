"""Api schema."""
# Standard Python Libraries
from datetime import datetime
from typing import Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel


class ApiKey(BaseModel):
    """Pydantic model for the ApiKey model."""

    id: str
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime]
    hashed_key: Optional[
        str
    ] = None  # Make optional to avoid validation error in response
    last_four: Optional[str]
    user: Optional[UUID] = None  # Make optional to avoid validation error in response
    api_key: Optional[
        str
    ] = None  # Add the actual key to the schema for response inclusion

    @classmethod
    def model_validate(cls, obj):
        """Model validate."""
        # Ensure that we convert the UUIDs to strings when validating
        api_key_data = obj.__dict__.copy()

        # Remove the '_state' field or any other unwanted internal fields
        api_key_data.pop("_state", None)
        api_key_data["user"] = api_key_data.pop("user_id", None)

        for key, val in api_key_data.items():
            # Convert any UUIDs to strings
            if isinstance(val, UUID):
                api_key_data[key] = str(val)
        return cls(**api_key_data)

    class Config:
        """Config."""

        from_attributes = True
