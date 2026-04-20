from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Metric, Trend


class TrendDetectionService:
    """Service for detecting and analyzing trends in metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_trends(
        self,
        metric_name: str,
        days: int = 7,
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """Detect trends in a specific metric over a time period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(Metric).where(
            Metric.name == metric_name,
            Metric.timestamp >= cutoff_date
        ).order_by(Metric.timestamp.asc())
        result = await self.db.execute(query)
        metrics = list(result.scalars().all())

        if len(metrics) < 2:
            return {"trend": "insufficient_data", "metrics_count": len(metrics)}

        values = [m.value for m in metrics]
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_first == 0:
            return {"trend": "no_baseline", "metrics_count": len(metrics)}

        change = (avg_second - avg_first) / avg_first

        if change > threshold:
            trend = "increasing"
        elif change < -threshold:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "change_percentage": round(change * 100, 2),
            "metrics_count": len(metrics),
            "avg_first_period": round(avg_first, 2),
            "avg_second_period": round(avg_second, 2)
        }

    async def save_trend(
        self,
        metric_name: str,
        trend_type: str,
        change_percentage: float,
        metadata: Dict[str, Any]
    ) -> Trend:
        """Save detected trend to database."""
        trend = Trend(
            metric_name=metric_name,
            trend_type=trend_type,
            change_percentage=change_percentage,
            detected_at=datetime.utcnow(),
            metadata=metadata
        )
        self.db.add(trend)
        await self.db.commit()
        await self.db.refresh(trend)
        return trend

    async def get_recent_trends(
        self,
        days: int = 7,
        limit: int = 20
    ) -> List[Trend]:
        """Get recent trends."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(Trend).where(
            Trend.detected_at >= cutoff_date
        ).order_by(Trend.detected_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def analyze_all_metrics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Analyze trends for all unique metrics."""
        query = select(Metric.name).distinct()
        result = await self.db.execute(query)
        metric_names = result.scalars().all()

        trends = []
        for metric_name in metric_names:
            trend_data = await self.detect_trends(metric_name, days)
            if trend_data["trend"] not in ["insufficient_data", "no_baseline"]:
                trends.append({
                    "metric_name": metric_name,
                    **trend_data
                })
        return trends
