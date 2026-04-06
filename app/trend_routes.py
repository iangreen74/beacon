from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models import User, TrendAlert
from app.trend_detection import TrendDetector


router = APIRouter(prefix="/api/trends", tags=["trends"])


class TrendAnalysisResponse(BaseModel):
    team_id: str
    health_trend: dict
    blocker_patterns: dict
    anomalies: list
    analysis_timestamp: str


class AlertResponse(BaseModel):
    id: str
    team_id: str
    alert_type: str
    severity: str
    message: str
    metadata: dict
    timestamp: str
    acknowledged: bool


@router.post("/analyze/{team_id}")
async def analyze_team_trends(
    team_id: str,
    days: int = Query(default=14, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TrendAnalysisResponse:
    """Perform comprehensive trend analysis for a team."""
    detector = TrendDetector(db)
    
    health_trend = detector.analyze_team_health_trend(team_id, days)
    blocker_patterns = detector.detect_blocker_patterns(team_id, days)
    anomalies = detector.detect_anomalies(team_id, days)
    
    return TrendAnalysisResponse(
        team_id=team_id,
        health_trend=health_trend,
        blocker_patterns=blocker_patterns,
        anomalies=anomalies,
        analysis_timestamp=datetime.utcnow().isoformat()
    )


@router.get("/alerts/{team_id}")
async def get_team_alerts(
    team_id: str,
    unacknowledged_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[AlertResponse]:
    """Retrieve trend alerts for a team."""
    query = db.query(TrendAlert).filter(TrendAlert.team_id == team_id)
    
    if unacknowledged_only:
        query = query.filter(TrendAlert.acknowledged == False)
    
    alerts = query.order_by(TrendAlert.timestamp.desc()).limit(limit).all()
    
    return [
        AlertResponse(
            id=str(alert.id),
            team_id=alert.team_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            metadata=alert.metadata,
            timestamp=alert.timestamp.isoformat(),
            acknowledged=alert.acknowledged
        )
        for alert in alerts
    ]


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Mark a trend alert as acknowledged."""
    alert = db.query(TrendAlert).filter(TrendAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.acknowledged = True
    db.commit()
    
    return {"status": "acknowledged", "alert_id": alert_id}


@router.get("/dashboard/{team_id}")
async def get_dashboard_data(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Retrieve aggregated trend data for dashboard consumption."""
    detector = TrendDetector(db)
    
    health_trend = detector.analyze_team_health_trend(team_id, days=30)
    blocker_patterns = detector.detect_blocker_patterns(team_id, days=30)
    
    unacknowledged_alerts = db.query(TrendAlert).filter(
        TrendAlert.team_id == team_id,
        TrendAlert.acknowledged == False
    ).count()
    
    return {
        "team_id": team_id,
        "health_status": health_trend.get("status"),
        "health_score": health_trend.get("current_score"),
        "blocker_frequency": blocker_patterns.get("frequency"),
        "top_blockers": blocker_patterns.get("patterns", [])[:3],
        "unacknowledged_alerts": unacknowledged_alerts,
        "last_updated": datetime.utcnow().isoformat()
    }
