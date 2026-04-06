from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, validator, constr
import bleach


class MoodEnum(str, Enum):
    great = "great"
    good = "good"
    okay = "okay"
    bad = "bad"
    terrible = "terrible"


class UserRole(str, Enum):
    admin = "admin"
    manager = "manager"
    member = "member"


class SanitizedStr(constr):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            return bleach.clean(v, tags=[], strip=True)
        return v


class UserBase(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)

    @validator('email')
    def sanitize_email(cls, v):
        return bleach.clean(v, tags=[], strip=True).lower()

    @validator('full_name')
    def sanitize_name(cls, v):
        if v:
            return bleach.clean(v, tags=[], strip=True)
        return v


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        orm_mode = True


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

    @validator('name', 'description')
    def sanitize_text(cls, v):
        if v:
            return bleach.clean(v, tags=[], strip=True)
        return v


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    id: int
    manager_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class PulseBase(BaseModel):
    mood: MoodEnum
    feedback: Optional[str] = Field(None, max_length=2000)
    is_anonymous: bool = False

    @validator('feedback')
    def sanitize_feedback(cls, v):
        if v:
            return bleach.clean(v, tags=[], strip=True)
        return v


class PulseCreate(PulseBase):
    team_id: int


class PulseResponse(PulseBase):
    id: int
    team_id: int
    user_id: Optional[int]
    created_at: datetime

    class Config:
        orm_mode = True


class AnalysisRequest(BaseModel):
    team_id: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]


class AnalysisResponse(BaseModel):
    team_id: int
    insights: str
    sentiment_score: float
    generated_at: datetime


class TrendResponse(BaseModel):
    team_id: int
    trend_type: str
    severity: str
    description: str
    detected_at: datetime


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., max_length=128)

    @validator('email')
    def sanitize_email(cls, v):
        return bleach.clean(v, tags=[], strip=True).lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
