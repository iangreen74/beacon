from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import PulseSchedule, Team, User, PulseResponse
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending pulse reminder notifications"""
    
    @staticmethod
    def get_pending_reminders(db: Session) -> List[PulseSchedule]:
        """Get schedules that need reminders sent"""
        now = datetime.utcnow()
        current_time = now.strftime("%H:%M")
        current_day = now.weekday()
        
        schedules = db.query(PulseSchedule).filter(
            PulseSchedule.enabled == True,
            PulseSchedule.trigger_time == current_time
        ).all()
        
        pending = []
        for schedule in schedules:
            # Check if schedule should trigger today
            if schedule.frequency == "daily":
                pending.append(schedule)
            elif schedule.frequency == "weekly" and current_day == 0:  # Monday
                pending.append(schedule)
            elif schedule.frequency == "biweekly":
                # Check if it's been 14 days since last reminder
                if schedule.last_triggered:
                    days_since = (now - schedule.last_triggered).days
                    if days_since >= 14:
                        pending.append(schedule)
                else:
                    pending.append(schedule)
        
        return pending
    
    @staticmethod
    def send_reminder(team: Team, db: Session) -> dict:
        """Send reminder to team members who haven't submitted pulse today"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get members who haven't responded today
        responded_user_ids = db.query(PulseResponse.user_id).filter(
            PulseResponse.team_id == team.id,
            PulseResponse.created_at >= today_start
        ).distinct().all()
        
        responded_ids = {uid[0] for uid in responded_user_ids}
        pending_members = [m for m in team.members if m.id not in responded_ids]
        
        # In production, integrate with email/slack/etc
        notifications_sent = []
        for member in pending_members:
            notification = {
                "user_id": member.id,
                "email": member.email,
                "team_name": team.name,
                "message": f"Reminder: Please submit your pulse for {team.name}",
                "timestamp": datetime.utcnow()
            }
            notifications_sent.append(notification)
            logger.info(f"Reminder sent to {member.email} for team {team.name}")
        
        return {
            "team_id": team.id,
            "notifications_sent": len(notifications_sent),
            "pending_members": len(pending_members)
        }
    
    @staticmethod
    def process_scheduled_reminders(db: Session) -> dict:
        """Process all pending pulse reminders"""
        pending_schedules = NotificationService.get_pending_reminders(db)
        results = []
        
        for schedule in pending_schedules:
            team = db.query(Team).filter(Team.id == schedule.team_id).first()
            if team:
                result = NotificationService.send_reminder(team, db)
                results.append(result)
                
                # Update last triggered timestamp
                schedule.last_triggered = datetime.utcnow()
                db.commit()
        
        return {
            "processed_schedules": len(pending_schedules),
            "results": results,
            "timestamp": datetime.utcnow()
        }
