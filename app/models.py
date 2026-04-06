from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class TeamRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        return v.strip()

    @field_validator('description')
    @classmethod
    def sanitize_description(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('name')
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else None

    @field_validator('description')
    @classmethod
    def sanitize_description(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else None


class Team(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class TeamMemberBase(BaseModel):
    user_id: str
    role: TeamRole = TeamRole.MEMBER


class TeamMemberCreate(TeamMemberBase):
    pass


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamMember(TeamMemberBase):
    model_config = ConfigDict(from_attributes=True)

    team_id: str
    added_at: datetime


class InvitationBase(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    role: TeamRole = TeamRole.MEMBER

    @field_validator('email')
    @classmethod
    def sanitize_email(cls, v: str) -> str:
        return v.strip().lower()


class InvitationCreate(InvitationBase):
    pass


class Invitation(InvitationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    team_id: str
    invited_by: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
