from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models import Pulse, TrendAlert
from app.database import get_db


class TrendDetector:
    """Detect trends and anomalies in pulse data for team health monitoring."""
    
    def __init__(self, db: Session):
        self.db = db
        self.health_threshold = 0.3
        self.anomaly_std_threshold = 2.0
        self.blocker_frequency_threshold = 0.4
    
    def analyze_team_health_trend(self, team_id: str, days: int = 14) -> Dict[str, Any]:
        """Detect deteriorating team health trends over time."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pulses = self.db.query(Pulse).filter(
            and_(
                Pulse.team_id == team_id,
                Pulse.timestamp >= cutoff_date
            )
        ).order_by(Pulse.timestamp.asc()).all()
        
        if len(pulses) < 3:
            return {"status": "insufficient_data", "trend": None}
        
        # Calculate daily average health scores
        daily_scores = defaultdict(list)
        for pulse in pulses:
            date_key = pulse.timestamp.date()
            daily_scores[date_key].append(pulse.health_score)
        
        sorted_dates = sorted(daily_scores.keys())
        scores = [statistics.mean(daily_scores[date]) for date in sorted_dates]
        
        # Detect deterioration using moving average
        if len(scores) >= 7:
            recent_avg = statistics.mean(scores[-7:])
            earlier_avg = statistics.mean(scores[:7])
            decline_rate = (earlier_avg - recent_avg) / earlier_avg if earlier_avg > 0 else 0
            
            if decline_rate > self.health_threshold:
                self._create_alert(
                    team_id=team_id,
                    alert_type="health_deterioration",
                    severity="high",
                    message=f"Team health declined {decline_rate:.1%} over {days} days",
                    metadata={"decline_rate": decline_rate, "recent_avg": recent_avg}
                )
                return {"status": "deteriorating", "trend": decline_rate, "current_score": recent_avg}
        
        return {"status": "stable", "trend": 0.0, "current_score": scores[-1] if scores else 0}
    
    def detect_blocker_patterns(self, team_id: str, days: int = 30) -> Dict[str, Any]:
        """Identify recurring blocker patterns in team pulses."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pulses = self.db.query(Pulse).filter(
            and_(
                Pulse.team_id == team_id,
                Pulse.timestamp >= cutoff_date,
                Pulse.has_blockers == True
            )
        ).all()
        
        if not pulses:
            return {"patterns": [], "frequency": 0.0}
        
        # Extract and categorize blockers
        blocker_keywords = defaultdict(int)
        total_pulses = self.db.query(func.count(Pulse.id)).filter(
            and_(Pulse.team_id == team_id, Pulse.timestamp >= cutoff_date)
        ).scalar()
        
        for pulse in pulses:
            if pulse.blockers:
                words = pulse.blockers.lower().split()
                for word in words:
                    if len(word) > 4:
                        blocker_keywords[word] += 1
        
        # Find recurring patterns
        patterns = [
            {"keyword": keyword, "count": count}
            for keyword, count in sorted(blocker_keywords.items(), key=lambda x: x[1], reverse=True)[:5]
            if count >= 3
        ]
        
        blocker_frequency = len(pulses) / total_pulses if total_pulses > 0 else 0
        
        if blocker_frequency > self.blocker_frequency_threshold and patterns:
            self._create_alert(
                team_id=team_id,
                alert_type="recurring_blockers",
                severity="medium",
                message=f"Blockers present in {blocker_frequency:.1%} of pulses",
                metadata={"patterns": patterns, "frequency": blocker_frequency}
            )
        
        return {"patterns": patterns, "frequency": blocker_frequency}
    
    def detect_anomalies(self, team_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Detect anomalous pulse data points using statistical analysis."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        pulses = self.db.query(Pulse).filter(
            and_(
                Pulse.team_id == team_id,
                Pulse.timestamp >= cutoff_date
            )
        ).all()
        
        if len(pulses) < 10:
            return []
        
        scores = [p.health_score for p in pulses]
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores)
        
        anomalies = []
        for pulse in pulses:
            z_score = abs((pulse.health_score - mean_score) / std_dev) if std_dev > 0 else 0
            
            if z_score > self.anomaly_std_threshold:
                anomalies.append({
                    "pulse_id": pulse.id,
                    "user_id": pulse.user_id,
                    "timestamp": pulse.timestamp.isoformat(),
                    "health_score": pulse.health_score,
                    "z_score": z_score,
                    "deviation": pulse.health_score - mean_score
                })
        
        if anomalies:
            self._create_alert(
                team_id=team_id,
                alert_type="anomaly_detected",
                severity="medium",
                message=f"Detected {len(anomalies)} anomalous pulse(s)",
                metadata={"anomalies": anomalies[:5]}
            )
        
        return anomalies
    
    def _create_alert(self, team_id: str, alert_type: str, severity: str, message: str, metadata: Dict[str, Any]):
        """Create and store a trend alert."""
        alert = TrendAlert(
            team_id=team_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            metadata=metadata,
            timestamp=datetime.utcnow(),
            acknowledged=False
        )
        self.db.add(alert)
        self.db.commit()
