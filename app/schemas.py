"""Pydantic schemas for request/response validation."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TeamBase(BaseModel):
    """Base team schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    pass


class TeamUpdate(BaseModel):
    """Schema for updating a team."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True


class PaginatedTeamMembers(BaseModel):
    """Schema for paginated team members."""
    members: List[TeamMemberResponse]
    total: int
    skip: int
    limit: int


class PulseBase(BaseModel):
    """Base pulse schema."""
    sentiment_score: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class PulseCreate(PulseBase):
    """Schema for creating a pulse."""
    team_id: int


class PulseResponse(PulseBase):
    """Schema for pulse response."""
    id: int
    user_id: int
    team_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    database: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    """Schema for metrics response."""
    total_pulses: int
    total_teams: int
    total_users: int
    average_sentiment: float
