"""User schemas."""

# Standard Python Libraries
from datetime import datetime
from typing import List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .api_key import ApiKey
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
    apiKeys: Optional[List[ApiKey]] = []

    @classmethod
    def model_validate(cls, obj):
        # Convert fields before passing to Pydantic Schema
        user_dict = obj.__dict__.copy()
        user_dict["roles"] = [
            Role.model_validate(role).model_dump() for role in obj.roles.all()
        ]
        user_dict["apiKeys"] = [
            ApiKey.model_validate(api_key).model_dump() for api_key in obj.apiKeys.all()
        ]
        [ApiKey.from_orm(api_key) for api_key in obj]
        return cls(**user_dict)

    def model_dump(self, **kwargs):
        """Override model_dump to handle UUID serialization."""
        data = super().model_dump(**kwargs)
        if isinstance(data.get("id"), UUID):
            data["id"] = str(data["id"])  # Convert UUID to string
        return data

    class Config:
        from_attributes = True


class UpdateUser(BaseModel):
    firstName: str
    lastName: str
    email: str
    userType: str
    state: Optional[str]
