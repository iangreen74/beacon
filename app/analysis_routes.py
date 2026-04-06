from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.database import get_db
from app.ai_analysis import ai_engine


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    pulse_id: str
    force_refresh: Optional[bool] = False


class AnalysisResponse(BaseModel):
    pulse_id: str
    sentiment: str
    sentiment_score: float
    themes: list[str]
    blockers: list[str]
    insights: list[str]
    summary: str
    response_count: int
    analyzed_at: str
    fallback: Optional[bool] = False


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_pulse(request: AnalysisRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    async with get_db() as db:
        pulse = await db.execute(
            "SELECT * FROM pulses WHERE id = ? AND team_id IN (SELECT team_id FROM team_members WHERE user_id = ?)",
            (request.pulse_id, current_user["id"])
        )
        pulse_data = await pulse.fetchone()
        
        if not pulse_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pulse not found or access denied"
            )
        
        cursor = await db.execute(
            """SELECT pr.*, u.email, q.question_text 
               FROM pulse_responses pr
               JOIN users u ON pr.user_id = u.id
               JOIN pulse_questions q ON pr.question_id = q.id
               WHERE pr.pulse_id = ?""",
            (request.pulse_id,)
        )
        responses = await cursor.fetchall()
        
        if not responses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No responses available for analysis"
            )
        
        response_dicts = [
            {
                "user_id": r["user_id"],
                "question": r["question_text"],
                "answer": r["response_text"],
                "submitted_at": r["submitted_at"]
            }
            for r in responses
        ]
        
        if request.force_refresh:
            cache_key = await ai_engine._get_cache_key(request.pulse_id)
            await ai_engine.initialize_redis()
            try:
                await ai_engine.redis_client.delete(cache_key)
            except Exception:
                pass
        
        analysis = await ai_engine.analyze_pulse_responses(request.pulse_id, response_dicts)
        
        return AnalysisResponse(**analysis)


@router.get("/pulse/{pulse_id}", response_model=AnalysisResponse)
async def get_pulse_analysis(pulse_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT pa.* FROM pulse_analyses pa
               JOIN pulses p ON pa.pulse_id = p.id
               WHERE pa.pulse_id = ? AND p.team_id IN 
               (SELECT team_id FROM team_members WHERE user_id = ?)""",
            (pulse_id, current_user["id"])
        )
        analysis = await cursor.fetchone()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis not found"
            )
        
        import json
        analysis_data = json.loads(analysis["analysis_data"])
        
        return AnalysisResponse(**analysis_data)


@router.get("/team/{team_id}/recent")
async def get_team_recent_analyses(team_id: str, limit: int = 10, current_user: Dict[str, Any] = Depends(get_current_user)):
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT pa.*, p.title FROM pulse_analyses pa
               JOIN pulses p ON pa.pulse_id = p.id
               WHERE p.team_id = ? AND p.team_id IN 
               (SELECT team_id FROM team_members WHERE user_id = ?)
               ORDER BY pa.created_at DESC LIMIT ?""",
            (team_id, current_user["id"], limit)
        )
        analyses = await cursor.fetchall()
        
        import json
        return [
            {
                "pulse_id": a["pulse_id"],
                "pulse_title": a["title"],
                "analysis": json.loads(a["analysis_data"]),
                "created_at": a["created_at"]
            }
            for a in analyses
        ]
