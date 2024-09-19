"""Schemas.py."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel, Json

from .schema_models.assessment import Assessment
from .schema_models.category import Category
from .schema_models.cpe import Cpe
from .schema_models.cve import Cve
from .schema_models.domain import Domain, DomainFilters, DomainSearch
from .schema_models.notification import Notification
from .schema_models.organization import Organization
from .schema_models.question import Question
from .schema_models.resource import Resource
from .schema_models.response import Response
from .schema_models.role import Role
from .schema_models.scan import Scan
from .schema_models.searchbody import SearchBody
from .schema_models.service import Service
from .schema_models.user import User
from .schema_models.vulnerability import (
    Vulnerability,
    VulnerabilityFilters,
    VulnerabilitySearch,
)
