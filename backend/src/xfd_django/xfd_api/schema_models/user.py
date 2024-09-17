"""User schemas."""
# Third-Party Libraries
# from pydantic.types import UUID1, UUID
# Standard Python Libraries
from datetime import datetime
from typing import List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .role import Role


class User(BaseModel):
    """User schema."""

    id: UUID
    cognitoId: Optional[str]
    loginGovId: Optional[str]
    createdAt: datetime
    updatedAt: datetime
    firstName: str
    lastName: str
    fullName: str
    email: str
    invitePending: bool
    loginBlockedByMaintenance: bool
    dateAcceptedTerms: Optional[datetime]
    acceptedTermsVersion: Optional[str]
    lastLoggedIn: Optional[datetime]
    userType: str
    regionId: Optional[str]
    state: Optional[str]
    oktaId: Optional[str]
    roles: Optional[List[Role]] = []

    @classmethod
    def from_orm(cls, obj):
        # Convert roles to a list of RoleSchema before passing to Pydantic
        user_dict = obj.__dict__.copy()
        user_dict["roles"] = [Role.from_orm(role) for role in obj.roles.all()]
        return cls(**user_dict)

    class Config:
        orm_mode = True
        from_attributes = True
