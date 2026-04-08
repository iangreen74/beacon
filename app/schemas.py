from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    team_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    team_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PulseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class PulseCreate(PulseBase):
    team_id: int


class PulseResponse(PulseBase):
    id: int
    team_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PulseResponseBase(BaseModel):
    response_text: str = Field(..., min_length=1)


class PulseResponseCreate(PulseResponseBase):
    pulse_id: int
    user_id: int


class PulseResponseSchema(PulseResponseBase):
    id: int
    pulse_id: int
    user_id: int
    sentiment_score: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)


class NotificationCreate(NotificationBase):
    user_id: int


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisResultBase(BaseModel):
    analysis_type: str = Field(..., min_length=1, max_length=100)
    result_data: str = Field(..., min_length=1)


class AnalysisResultCreate(AnalysisResultBase):
    pulse_id: int


class AnalysisResultResponse(AnalysisResultBase):
    id: int
    pulse_id: int
    created_at: datetime

    class Config:
        from_attributes = True
