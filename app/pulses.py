from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_user
from app.models import User, Team, PulseResponse, PulseSchedule
from app.repositories import PulseRepository
import asyncio
from collections import defaultdict

router = APIRouter(prefix="/pulses", tags=["pulses"])

# Rate limiting storage (in-memory, replace with Redis in production)
rate_limit_storage = defaultdict(list)
MAX_PULSES_PER_HOUR = 10


class PulseSubmission(BaseModel):
    team_id: int
    mood: int = Field(..., ge=1, le=5, description="Mood rating 1-5")
    energy: int = Field(..., ge=1, le=5, description="Energy rating 1-5")
    blockers: Optional[str] = Field(None, max_length=500)
    comments: Optional[str] = Field(None, max_length=1000)

    @validator('blockers', 'comments')
    def strip_whitespace(cls, v):
        return v.strip() if v else None


class PulseScheduleCreate(BaseModel):
    team_id: int
    frequency: str = Field(..., regex="^(daily|weekly|biweekly)$")
    trigger_time: str = Field(..., regex="^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    enabled: bool = True


class PulseResponseOut(BaseModel):
    id: int
    user_id: int
    team_id: int
    mood: int
    energy: int
    blockers: Optional[str]
    comments: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


def check_rate_limit(user_id: int) -> bool:
    """Check if user has exceeded rate limit"""
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=1)
    
    # Clean old entries
    rate_limit_storage[user_id] = [
        ts for ts in rate_limit_storage[user_id] if ts > cutoff
    ]
    
    if len(rate_limit_storage[user_id]) >= MAX_PULSES_PER_HOUR:
        return False
    
    rate_limit_storage[user_id].append(now)
    return True


@router.post("/submit", response_model=PulseResponseOut, status_code=status.HTTP_201_CREATED)
def submit_pulse(
    pulse: PulseSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a pulse response"""
    # Check rate limit
    if not check_rate_limit(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 10 pulses per hour."
        )
    
    # Verify user is member of team
    team = db.query(Team).filter(Team.id == pulse.team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if current_user not in team.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this team"
        )
    
    # Create pulse response
    pulse_response = PulseResponse(
        user_id=current_user.id,
        team_id=pulse.team_id,
        mood=pulse.mood,
        energy=pulse.energy,
        blockers=pulse.blockers,
        comments=pulse.comments,
        created_at=datetime.utcnow()
    )
    
    db.add(pulse_response)
    db.commit()
    db.refresh(pulse_response)
    
    return pulse_response


@router.get("/team/{team_id}", response_model=List[PulseResponseOut])
def get_team_pulses(
    team_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent pulse responses for a team"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    if current_user not in team.members:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this team"
        )
    
    pulses = db.query(PulseResponse).filter(
        PulseResponse.team_id == team_id
    ).order_by(PulseResponse.created_at.desc()).limit(limit).all()
    
    return pulses


@router.post("/schedule", status_code=status.HTTP_201_CREATED)
def create_pulse_schedule(
    schedule: PulseScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a scheduled pulse trigger for a team"""
    team = db.query(Team).filter(Team.id == schedule.team_id).first()
    if not team or team.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owners can create pulse schedules"
        )
    
    pulse_schedule = PulseSchedule(
        team_id=schedule.team_id,
        frequency=schedule.frequency,
        trigger_time=schedule.trigger_time,
        enabled=schedule.enabled,
        created_at=datetime.utcnow()
    )
    
    db.add(pulse_schedule)
    db.commit()
    
    return {"message": "Pulse schedule created successfully", "schedule_id": pulse_schedule.id}
