from typing import List, Dict, Any
import asyncio
from datetime import datetime, timedelta
import arq
from arq import create_pool
from arq.connections import RedisSettings

from app.database import get_db, get_settings
from app.repositories import PulseRepository, TeamRepository
from app.ai_analysis import AIAnalysisEngine
from app.notifications import NotificationService
from app.cache import cache_manager


async def send_pulse_reminders(ctx: Dict[str, Any]):
    """Send pulse reminders to team members who haven't responded."""
    async for db in get_db():
        pulse_repo = PulseRepository(db)
        notification_service = NotificationService()
        
        # Find active pulses with pending responses
        cutoff_time = datetime.utcnow() - timedelta(hours=12)
        pending_pulses = await pulse_repo.find_pending_pulses(cutoff_time)
        
        for pulse_data in pending_pulses:
            await notification_service.send_reminder(
                user_id=pulse_data["user_id"],
                pulse_id=pulse_data["pulse_id"],
                team_id=pulse_data["team_id"]
            )
        
        return {"reminders_sent": len(pending_pulses)}


async def batch_analyze_pulses(ctx: Dict[str, Any], team_id: str, start_date: str, end_date: str):
    """Batch analyze pulses for a team within date range."""
    async for db in get_db():
        pulse_repo = PulseRepository(db)
        ai_engine = AIAnalysisEngine()
        
        pulses = await pulse_repo.find_by_team_and_date_range(
            team_id=team_id,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date)
        )
        
        results = []
        for pulse in pulses:
            analysis = await ai_engine.analyze_sentiment(pulse["response_text"])
            results.append({"pulse_id": pulse["id"], "analysis": analysis})
        
        # Cache batch results
        cache_key = f"batch_analysis:{team_id}:{start_date}:{end_date}"
        await cache_manager.set(cache_key, results, ttl=7200)
        
        return {"analyzed_count": len(results), "cache_key": cache_key}


async def generate_team_report(ctx: Dict[str, Any], team_id: str, report_type: str = "weekly"):
    """Generate comprehensive team report."""
    async for db in get_db():
        pulse_repo = PulseRepository(db)
        team_repo = TeamRepository(db)
        ai_engine = AIAnalysisEngine()
        
        team = await team_repo.find_by_id(team_id)
        if not team:
            return {"error": "Team not found"}
        
        # Calculate date range based on report type
        end_date = datetime.utcnow()
        if report_type == "weekly":
            start_date = end_date - timedelta(days=7)
        elif report_type == "monthly":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Gather and analyze data
        pulses = await pulse_repo.find_by_team_and_date_range(team_id, start_date, end_date)
        
        sentiment_scores = []
        themes = []
        
        for pulse in pulses:
            analysis = await ai_engine.analyze_sentiment(pulse["response_text"])
            sentiment_scores.append(analysis.get("score", 0))
            if "themes" in analysis:
                themes.extend(analysis["themes"])
        
        report = {
            "team_id": team_id,
            "team_name": team["name"],
            "report_type": report_type,
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_responses": len(pulses),
            "avg_sentiment": sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
            "top_themes": list(set(themes))[:5],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Cache report
        cache_key = f"report:{team_id}:{report_type}:{end_date.date()}"
        await cache_manager.set(cache_key, report, ttl=86400)
        
        return report


async def startup(ctx: Dict[str, Any]):
    """Initialize background task worker."""
    await cache_manager.initialize()
    ctx["cache_manager"] = cache_manager


async def shutdown(ctx: Dict[str, Any]):
    """Cleanup background task worker."""
    await cache_manager.close()


class WorkerSettings:
    """ARQ worker settings."""
    
    functions = [
        send_pulse_reminders,
        batch_analyze_pulses,
        generate_team_report
    ]
    
    on_startup = startup
    on_shutdown = shutdown
    
    redis_settings = RedisSettings(
        host="localhost",
        port=6379,
        database=0
    )
    
    # Cron jobs
    cron_jobs = [
        arq.cron(send_pulse_reminders, hour={9, 17}, minute=0)
    ]
