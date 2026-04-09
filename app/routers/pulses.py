"""API endpoints for pulse collection and retrieval."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import get_db
from app.models import Pulse, User
from app.schemas import PulseCreate, PulseResponse, PulseListResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/pulses", tags=["pulses"])


@router.post("", response_model=PulseResponse, status_code=201)
def create_pulse(
    pulse_data: PulseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PulseResponse:
    """Submit a new pulse with mood score and optional feedback."""
    try:
        if not (0.0 <= pulse_data.mood_score <= 10.0):
            raise HTTPException(status_code=400, detail="Mood score must be between 0 and 10")
        
        pulse = Pulse(
            user_id=current_user.id,
            team_id=current_user.team_id,
            mood_score=pulse_data.mood_score,
            feedback_text=pulse_data.feedback_text,
            metadata=pulse_data.metadata,
            created_at=datetime.utcnow(),
        )
        
        db.add(pulse)
        db.commit()
        db.refresh(pulse)
        
        return PulseResponse.from_orm(pulse)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create pulse: {str(e)}")


@router.get("", response_model=PulseListResponse)
def list_pulses(
    team_id: Optional[int] = Query(None, description="Filter by team ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PulseListResponse:
    """Retrieve pulses with pagination and filtering options."""
    try:
        filters = []
        
        if team_id is not None:
            filters.append(Pulse.team_id == team_id)
        
        if user_id is not None:
            filters.append(Pulse.user_id == user_id)
        
        if start_date is not None:
            filters.append(Pulse.created_at >= start_date)
        
        if end_date is not None:
            filters.append(Pulse.created_at <= end_date)
        
        query = db.query(Pulse)
        if filters:
            query = query.filter(and_(*filters))
        
        total = query.count()
        pulses = query.order_by(Pulse.created_at.desc()).offset(skip).limit(limit).all()
        
        return PulseListResponse(
            pulses=[PulseResponse.from_orm(p) for p in pulses],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve pulses: {str(e)}")
