from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Any
from datetime import datetime, timedelta
import os

from app.auth import get_current_user
from app.models import User
from app.database import db

router = APIRouter(prefix="/ui", tags=["frontend"])

# Setup templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

# Setup static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """Render main dashboard with team overview and pulse visualizations."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "page_title": "Team Pulse Dashboard"
        }
    )


@router.get("/team/{team_id}", response_class=HTMLResponse)
async def get_team_view(request: Request, team_id: str, current_user: User = Depends(get_current_user)):
    """Render detailed team view with historical data and AI insights."""
    team = await db.get_team(team_id)
    if not team:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Team not found"},
            status_code=404
        )
    
    return templates.TemplateResponse(
        "team_detail.html",
        {
            "request": request,
            "user": current_user,
            "team": team,
            "page_title": f"Team: {team.get('name', 'Unknown')}"
        }
    )


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """API endpoint for dashboard statistics."""
    teams = await db.get_user_teams(current_user.id)
    total_pulses = 0
    active_teams = 0
    alerts = []
    
    for team in teams:
        pulses = await db.get_team_pulses(team["id"], days=7)
        total_pulses += len(pulses)
        if pulses:
            active_teams += 1
            
            # Check for trend alerts
            recent_scores = [p.get("sentiment_score", 0) for p in pulses[-5:]]
            if recent_scores and sum(recent_scores) / len(recent_scores) < -0.3:
                alerts.append({
                    "team_id": team["id"],
                    "team_name": team["name"],
                    "type": "negative_trend",
                    "message": "Team sentiment declining"
                })
    
    return {
        "total_teams": len(teams),
        "active_teams": active_teams,
        "total_pulses_week": total_pulses,
        "alerts": alerts,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/api/team/{team_id}/pulse_history")
async def get_pulse_history(team_id: str, days: int = 30, current_user: User = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """API endpoint for historical pulse data visualization."""
    pulses = await db.get_team_pulses(team_id, days=days)
    
    history = []
    for pulse in pulses:
        history.append({
            "date": pulse.get("created_at", datetime.utcnow()).isoformat(),
            "sentiment_score": pulse.get("sentiment_score", 0),
            "mood": pulse.get("mood"),
            "response_count": 1
        })
    
    return history


@router.get("/api/team/{team_id}/insights")
async def get_team_insights(team_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """API endpoint for AI-generated team insights."""
    analysis = await db.get_latest_analysis(team_id)
    
    if not analysis:
        return {
            "summary": "No insights available yet",
            "trends": [],
            "recommendations": []
        }
    
    return {
        "summary": analysis.get("summary", ""),
        "sentiment": analysis.get("overall_sentiment", "neutral"),
        "trends": analysis.get("key_trends", []),
        "recommendations": analysis.get("action_items", []),
        "generated_at": analysis.get("created_at", datetime.utcnow()).isoformat()
    }
