"""User schemas."""

# Standard Python Libraries
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

# Third-Party Libraries
from pydantic import BaseModel

from .api_key import ApiKey
from .role import Role


class UserType(Enum):
    """User Type."""

    GLOBAL_ADMIN = "globalAdmin"
    GLOBAL_VIEW = "globalView"
    REGIONAL_ADMIN = "regionalAdmin"
    READY_SET_CYBER = "readySetCyber"
    STANDARD = "standard"


class User(BaseModel):
    """User schema."""

    id: UUID
    cognito_id: Optional[str]
    login_gov_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    first_name: str
    last_name: str
    full_name: str
    email: str
    invite_pending: bool
    first_login: Optional[bool] = None
    can_select_own_state: Optional[bool] = False
    login_blocked_by_maintenance: bool
    cognito_use_case_description: Optional[str] = None
    date_approved: Optional[datetime] = None
    approved_by: Optional[Dict[str, str]] = None
    date_accepted_terms: Optional[datetime]
    accepted_terms_version: Optional[str]
    last_logged_in: Optional[datetime]
    user_type: UserType
    region_id: Optional[str]
    state: Optional[str]
    okta_id: Optional[str]
    roles: Optional[List[Role]] = []
    api_keys: Optional[List[ApiKey]] = []


class UserResponse(BaseModel):
    """User response schema."""

    cognito_id: Optional[str]
    login_gov_id: Optional[str]
    first_name: str
    last_name: str
    full_name: str
    email: str
    invite_pending: bool
    first_login: Optional[bool] = None
    can_select_own_state: Optional[bool] = False
    login_blocked_by_maintenance: bool
    date_accepted_terms: Optional[datetime]
    accepted_terms_version: Optional[str]
    last_logged_in: Optional[datetime]
    user_type: UserType
    region_id: Optional[str]
    state: Optional[str]
    okta_id: Optional[str]
    roles: Optional[List[Role]] = []
    api_keys: Optional[List[ApiKey]] = []

    @classmethod
    def model_validate(cls, obj):
        """Model validate."""
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
            data["id"] = str(data["id"])
        return data

    class Config:
        """Config."""

        from_attributes = True


class UserRoleOrg(BaseModel):
    """User role organization schema."""

    id: str
    name: str


class UserRole(BaseModel):
    """User role schema."""

    id: str
    role: str
    approved: bool
    organization: Optional[UserRoleOrg] = None


class NewUser(BaseModel):
    """New user schema."""

    email: str
    first_name: str
    last_name: str
    organization: Optional[str] = None
    organization_admin: Optional[bool] = None
    region_id: Optional[str] = None
    state: Optional[str] = None
    user_type: Optional[UserType] = None


class NewUserResponseModel(BaseModel):
    """New user response schema."""

    id: str
    first_name: str
    last_name: str
    email: str
    invite_pending: bool
    user_type: UserType
    roles: Optional[List[UserRole]] = []


class UpdateUser(BaseModel):
    """Update user schema."""

    first_name: Optional[str]
    full_name: Optional[str]
    invite_pending: Optional[bool]
    first_login: Optional[bool]
    can_select_own_state: Optional[bool] = False
    last_name: Optional[str]
    login_blocked_by_maintenance: Optional[bool]
    organization: Optional[str]
    region_d: Optional[str]
    role: Optional[str]
    state: Optional[str]
    user_type: Optional[UserType]


class UpdateUserV2(BaseModel):
    """Schema for updating a user."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    state: Optional[str] = None
    user_type: Optional[str] = None
    invite_pending: Optional[bool] = None
    first_login: Optional[bool] = None
    can_select_own_state: Optional[bool] = False
    date_approved: Optional[datetime] = None
    approved_by: Optional[Any] = None


class RegisterUserResponse(BaseModel):
    """Register or deny user response."""

    status_code: int
    body: str


class VersionModel(BaseModel):
    """Version model."""

    version: str


class UserResponseV2(BaseModel):
    """Schema for returning user data."""

    id: str
    created_at: str
    updated_at: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    accepted_terms_version: Optional[str] = None
    date_accepted_terms: Optional[datetime] = None
    cognito_use_case_description: Optional[str] = None
    date_approved: Optional[datetime] = None
    approved_by: Optional[Dict[str, str]] = None
    last_logged_in: Optional[datetime] = None
    region_id: Optional[str] = None
    state: Optional[str] = None
    user_type: Optional[str] = None
    roles: List[Dict[str, Optional[Any]]]
    first_login: Optional[bool] = None
    can_select_own_state: Optional[bool] = False
