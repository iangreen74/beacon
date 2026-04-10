"""Email report generation and delivery service for staff performance reviews."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import User, Pulse, Team
from app.services.email import send_email
import logging

logger = logging.getLogger(__name__)


class PerformanceReportGenerator:
    """Generates weekly performance review reports for staff members."""

    def __init__(self, db: Session):
        self.db = db

    def generate_weekly_report(self, admin_id: int) -> Optional[Dict[str, Any]]:
        """Generate weekly performance report for an admin's team members."""
        try:
            admin = self.db.query(User).filter(User.id == admin_id).first()
            if not admin or admin.role != "admin":
                logger.warning(f"User {admin_id} is not an admin")
                return None

            teams = self.db.query(Team).filter(Team.admin_id == admin_id).all()
            if not teams:
                logger.info(f"No teams found for admin {admin_id}")
                return None

            team_ids = [team.id for team in teams]
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            staff_metrics = self._calculate_staff_metrics(
                team_ids, start_date, end_date
            )

            report_data = {
                "admin_name": admin.name,
                "admin_email": admin.email,
                "period_start": start_date.strftime("%Y-%m-%d"),
                "period_end": end_date.strftime("%Y-%m-%d"),
                "teams": [team.name for team in teams],
                "staff_metrics": staff_metrics,
                "summary": self._generate_summary(staff_metrics),
            }

            return report_data
        except Exception as e:
            logger.error(f"Error generating report for admin {admin_id}: {e}")
            return None

    def _calculate_staff_metrics(
        self, team_ids: List[int], start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Calculate performance metrics for staff members."""
        staff_members = (
            self.db.query(User)
            .filter(and_(User.team_id.in_(team_ids), User.role == "staff"))
            .all()
        )

        metrics = []
        for staff in staff_members:
            pulses = (
                self.db.query(Pulse)
                .filter(
                    and_(
                        Pulse.user_id == staff.id,
                        Pulse.created_at >= start_date,
                        Pulse.created_at <= end_date,
                    )
                )
                .all()
            )

            if pulses:
                sentiment_scores = [p.sentiment_score for p in pulses]
                avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                sentiment_trend = self._calculate_trend(sentiment_scores)
            else:
                avg_sentiment = None
                sentiment_trend = "no_data"

            metrics.append(
                {
                    "name": staff.name,
                    "email": staff.email,
                    "pulse_count": len(pulses),
                    "avg_sentiment": round(avg_sentiment, 2) if avg_sentiment else None,
                    "sentiment_trend": sentiment_trend,
                }
            )

        return sorted(metrics, key=lambda x: x["name"])

    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate general sentiment trend from scores."""
        if len(scores) < 2:
            return "stable"

        first_half = scores[: len(scores) // 2]
        second_half = scores[len(scores) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        diff = second_avg - first_avg
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        return "stable"

    def _generate_summary(self, staff_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for the report."""
        total_staff = len(staff_metrics)
        active_staff = len([m for m in staff_metrics if m["pulse_count"] > 0])
        
        sentiments = [m["avg_sentiment"] for m in staff_metrics if m["avg_sentiment"]]
        avg_team_sentiment = (
            round(sum(sentiments) / len(sentiments), 2) if sentiments else None
        )

        trends = [m["sentiment_trend"] for m in staff_metrics]
        improving = trends.count("improving")
        declining = trends.count("declining")

        return {
            "total_staff": total_staff,
            "active_staff": active_staff,
            "avg_team_sentiment": avg_team_sentiment,
            "improving_count": improving,
            "declining_count": declining,
        }

    def send_report_email(self, report_data: Dict[str, Any]) -> bool:
        """Send performance report via email."""
        try:
            subject = f"Weekly Staff Performance Review - {report_data['period_end']}"
            body = self._format_email_body(report_data)

            send_email(
                to_email=report_data["admin_email"],
                subject=subject,
                body=body,
            )
            logger.info(f"Report sent to {report_data['admin_email']}")
            return True
        except Exception as e:
            logger.error(f"Failed to send report email: {e}")
            return False

    def _format_email_body(self, report_data: Dict[str, Any]) -> str:
        """Format report data into email body."""
        lines = [
            f"Hello {report_data['admin_name']},",
            "",
            f"Here is your weekly staff performance review for {report_data['period_start']} to {report_data['period_end']}.",
            "",
            "SUMMARY",
            f"Total Staff: {report_data['summary']['total_staff']}",
            f"Active Staff: {report_data['summary']['active_staff']}",
            f"Average Team Sentiment: {report_data['summary']['avg_team_sentiment']}",
            f"Improving: {report_data['summary']['improving_count']}",
            f"Declining: {report_data['summary']['declining_count']}",
            "",
            "STAFF DETAILS",
        ]

        for metric in report_data["staff_metrics"]:
            lines.append(f"\n{metric['name']}:")
            lines.append(f"  Pulses: {metric['pulse_count']}")
            if metric["avg_sentiment"]:
                lines.append(f"  Sentiment: {metric['avg_sentiment']}")
                lines.append(f"  Trend: {metric['sentiment_trend']}")
            else:
                lines.append("  No data available")

        return "\n".join(lines)
