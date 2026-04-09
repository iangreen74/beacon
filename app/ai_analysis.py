"""AI analysis engine for sentiment and trend detection."""

import logging
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from sqlalchemy.orm import Session

from app.models import Pulse, Analysis
from app.schemas import AnalysisResult

logger = logging.getLogger(__name__)


class AnalysisProvider(str, Enum):
    """Available AI analysis providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0
        self.is_open = False

    def call(self, func, *args, **kwargs):
        if self.is_open:
            if time.time() - self.last_failure_time > self.timeout:
                self.is_open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.is_open = True
            raise e


class RateLimiter:
    """Rate limiter for API calls per user/team."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def check_limit(self, key: str) -> bool:
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []

        self.requests[key] = [ts for ts in self.requests[key] if now - ts < self.window_seconds]

        if len(self.requests[key]) >= self.max_requests:
            return False

        self.requests[key].append(now)
        return True


class AIAnalysisEngine:
    """Engine for analyzing team sentiment using AI providers."""

    SENTIMENT_PROMPT = """Analyze the following team sentiment data and provide insights.

Pulse responses:
{pulses}

Provide a brief analysis focusing on:
1. Overall sentiment trends
2. Key concerns or positive patterns
3. Recommended actions

Keep the response concise and actionable."""

    def __init__(self, provider: AnalysisProvider = AnalysisProvider.OPENAI):
        self.provider = provider
        self.circuit_breaker = CircuitBreaker()
        self.rate_limiter = RateLimiter()
        self._validate_api_keys()

    def _validate_api_keys(self) -> None:
        """Validate API keys at startup."""
        if self.provider == AnalysisProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            openai.api_key = api_key
        elif self.provider == AnalysisProvider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")

    def analyze_team_sentiment(self, team_id: int, db: Session) -> AnalysisResult:
        """Analyze sentiment for a team."""
        rate_key = f"team:{team_id}"
        if not self.rate_limiter.check_limit(rate_key):
            raise Exception("Rate limit exceeded for team")

        pulses = db.query(Pulse).filter(Pulse.team_id == team_id).order_by(Pulse.created_at.desc()).limit(50).all()

        if not pulses:
            return AnalysisResult(sentiment_score=0.0, summary="No data available", recommendations=[])

        pulse_text = "\n".join([f"- Mood: {p.mood}, Energy: {p.energy_level}, Comment: {p.comment or 'N/A'}" for p in pulses])
        prompt = self.SENTIMENT_PROMPT.format(pulses=pulse_text)

        analysis_text = self.circuit_breaker.call(self._call_ai_api, prompt)
        result = self._parse_analysis(analysis_text)

        analysis_record = Analysis(team_id=team_id, sentiment_score=result.sentiment_score, summary=result.summary, recommendations=result.recommendations)
        db.add(analysis_record)
        db.commit()

        return result

    def _call_ai_api(self, prompt: str) -> str:
        """Call the configured AI API."""
        if self.provider == AnalysisProvider.OPENAI:
            response = openai.ChatCompletion.create(model="gpt-4", messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=500)
            return response.choices[0].message.content
        elif self.provider == AnalysisProvider.ANTHROPIC:
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            response = client.messages.create(model="claude-3-sonnet-20240229", max_tokens=500, messages=[{"role": "user", "content": prompt}])
            return response.content[0].text
        raise ValueError(f"Unsupported provider: {self.provider}")

    def _parse_analysis(self, text: str) -> AnalysisResult:
        """Parse AI analysis response."""
        lines = text.strip().split("\n")
        sentiment_score = 0.5
        summary = ""
        recommendations = []

        for line in lines:
            if "positive" in line.lower():
                sentiment_score = 0.7
            elif "negative" in line.lower() or "concern" in line.lower():
                sentiment_score = 0.3
            if line.strip().startswith("-") or line.strip().startswith("•"):
                recommendations.append(line.strip().lstrip("-•").strip())

        summary = " ".join([l for l in lines if l.strip() and not l.strip().startswith(("-", "•"))])[:200]

        return AnalysisResult(sentiment_score=sentiment_score, summary=summary, recommendations=recommendations[:3])
