"""Trend detection service for analyzing sentiment patterns and anomalies.

Provides statistical analysis including moving averages and anomaly detection
for pulse sentiment data using async repository pattern.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from statistics import mean, stdev

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.sql import and_

from app.models import Pulse, Team
from app.schemas import TrendAlert


class TrendDetector:
    """Detects sentiment trends and anomalies using statistical methods."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.default_window_days = 7
        self.default_threshold = 2.0  # Standard deviations for anomaly detection

    async def get_team_pulses(self, team_id: int, days: int) -> List[Pulse]:
        """Retrieve pulses for a team within specified time window."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(Pulse)
            .where(
                and_(
                    Pulse.team_id == team_id,
                    Pulse.submitted_at >= cutoff_date,
                    Pulse.submitted_at.isnot(None)
                )
            )
            .order_by(Pulse.submitted_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def calculate_moving_average(
        self, team_id: int, window_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Calculate moving average of sentiment scores."""
        window_days = window_days or self.default_window_days
        pulses = await self.get_team_pulses(team_id, window_days)

        if not pulses:
            return {"team_id": team_id, "average": None, "count": 0}

        scores = [p.sentiment_score for p in pulses if p.sentiment_score is not None]
        if not scores:
            return {"team_id": team_id, "average": None, "count": 0}

        return {
            "team_id": team_id,
            "average": mean(scores),
            "count": len(scores),
            "window_days": window_days,
        }

    async def detect_anomalies(
        self, team_id: int, threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Detect sentiment anomalies using standard deviation method."""
        threshold = threshold or self.default_threshold
        pulses = await self.get_team_pulses(team_id, self.default_window_days)

        if len(pulses) < 3:
            return []

        scores = [p.sentiment_score for p in pulses if p.sentiment_score is not None]
        if len(scores) < 3:
            return []

        avg = mean(scores)
        std = stdev(scores)

        anomalies = []
        for pulse in pulses:
            if pulse.sentiment_score is None:
                continue
            z_score = (pulse.sentiment_score - avg) / std if std > 0 else 0
            if abs(z_score) >= threshold:
                anomalies.append(
                    {
                        "pulse_id": pulse.id,
                        "user_id": pulse.user_id,
                        "sentiment_score": pulse.sentiment_score,
                        "z_score": z_score,
                        "submitted_at": pulse.submitted_at,
                    }
                )

        return anomalies

    async def analyze_team_trends(
        self, team_id: int, alert_threshold: Optional[float] = None
    ) -> TrendAlert:
        """Analyze team sentiment trends and generate alerts if needed."""
        moving_avg = await self.calculate_moving_average(team_id)
        anomalies = await self.detect_anomalies(team_id, alert_threshold)

        # Determine trend direction
        trend_direction = "stable"
        if moving_avg["average"] is not None:
            if moving_avg["average"] < 3.0:
                trend_direction = "declining"
            elif moving_avg["average"] > 7.0:
                trend_direction = "improving"

        alert_needed = len(anomalies) > 0 or trend_direction == "declining"

        stmt = select(Team).where(Team.id == team_id)
        result = await self.session.execute(stmt)
        team = result.scalar_one_or_none()

        return TrendAlert(
            team_id=team_id,
            team_name=team.name if team else "Unknown",
            alert_needed=alert_needed,
            trend_direction=trend_direction,
            moving_average=moving_avg["average"],
            anomaly_count=len(anomalies),
            anomalies=anomalies,
            analyzed_at=datetime.utcnow(),
        )

    async def analyze_all_teams(self) -> List[TrendAlert]:
        """Analyze trends for all teams and return alerts."""
        stmt = select(Team).where(Team.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        teams = list(result.scalars().all())

        alerts = []
        for team in teams:
            custom_threshold = team.alert_threshold if hasattr(team, "alert_threshold") else None
            alert = await self.analyze_team_trends(team.id, custom_threshold)
            if alert.alert_needed:
                alerts.append(alert)

        return alerts
