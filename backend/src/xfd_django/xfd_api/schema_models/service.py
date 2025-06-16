"""Service schema."""
# Standard Python Libraries
from datetime import datetime
from typing import Any, Optional

# Third-Party Libraries
from pydantic import BaseModel, Json


class Service(BaseModel):
    """Service schema."""

    id: Any
    created_at: datetime
    updated_at: datetime
    service_source: Optional[str]
    port: int
    service: Optional[str]
    last_seen: Optional[datetime]
    banner: Optional[str]
    products: Json[Any]
    censys_metadata: Json[Any]
    censys_ipv4_results: Json[Any]
    shodan_results: Json[Any]
    wappalyzer_results: Json[Any]
    domain: Optional[Any]
    discovered_by: Optional[Any]

    class Config:
        """Config."""

        from_attributes = True
