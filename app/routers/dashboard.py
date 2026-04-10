"""Dashboard router for displaying recent pulses and overview data."""
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field

from app.database import get_db, PulseResponse as PulseResponseModel, User as UserModel
from app.auth.dependencies import get_current_user
from app.models import User


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class RecentPulseItem(BaseModel):
    """Schema for a single recent pulse item."""
    id: int
    user_name: str
    team_name: Optional[str] = None
    health_score: int
    blockers_exist: bool
    submitted_at: datetime
    summary: Optional[str] = None

    model_config = {"from_attributes": True}


class RecentPulsesResponse(BaseModel):
    """Response schema for recent pulses widget."""
    pulses: List[RecentPulseItem]
    total_count: int
    showing_count: int


class DashboardStats(BaseModel):
    """Dashboard statistics summary."""
    total_pulses_today: int
    average_health_score: float
    active_blockers: int
    team_members_reported: int


@router.get("/recent-pulses", response_model=RecentPulsesResponse)
async def get_recent_pulses(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent pulses to return"),
    hours: int = Query(default=168, ge=1, le=720, description="Hours to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecentPulsesResponse:
    """Get recent pulses for dashboard widget.
    
    Returns the most recent pulse submissions visible to the current user.
    Admins see all pulses, team members see only their team's pulses.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = (
        db.query(PulseResponseModel)
        .join(UserModel, PulseResponseModel.user_id == UserModel.id)
        .filter(PulseResponseModel.created_at >= cutoff_time)
    )
    
    # Apply authorization filter
    if not current_user.is_admin:
        query = query.filter(UserModel.team_id == current_user.team_id)
    
    total_count = query.count()
    
    pulses_data = (
        query.order_by(desc(PulseResponseModel.created_at))
        .limit(limit)
        .all()
    )
    
    pulse_items = []
    for pulse in pulses_data:
        user = db.query(UserModel).filter(UserModel.id == pulse.user_id).first()
        if not user:
            continue
            
        pulse_items.append(
            RecentPulseItem(
                id=pulse.id,
                user_name=user.full_name or user.email,
                team_name=user.team.name if user.team else None,
                health_score=pulse.health_score,
                blockers_exist=bool(pulse.blockers),
                submitted_at=pulse.created_at,
                summary=pulse.highlights[:100] if pulse.highlights else None,
            )
        )
    
    return RecentPulsesResponse(
        pulses=pulse_items,
        total_count=total_count,
        showing_count=len(pulse_items),
    )


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardStats:
    """Get dashboard statistics for the current user's scope.
    
    Returns aggregated statistics for today's activity.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = db.query(PulseResponseModel).filter(
        PulseResponseModel.created_at >= today_start
    )
    
    # Apply authorization filter
    if not current_user.is_admin:
        query = (
            query.join(UserModel, PulseResponseModel.user_id == UserModel.id)
            .filter(UserModel.team_id == current_user.team_id)
        )
    
    pulses_today = query.all()
    total_pulses = len(pulses_today)
    
    if total_pulses > 0:
        avg_health = sum(p.health_score for p in pulses_today) / total_pulses
        active_blockers = sum(1 for p in pulses_today if p.blockers)
        unique_users = len(set(p.user_id for p in pulses_today))
    else:
        avg_health = 0.0
        active_blockers = 0
        unique_users = 0
    
    return DashboardStats(
        total_pulses_today=total_pulses,
        average_health_score=round(avg_health, 1),
        active_blockers=active_blockers,
        team_members_reported=unique_users,
    )
