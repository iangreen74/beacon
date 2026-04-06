from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os
import json
import asyncio
from enum import Enum

from anthropic import AsyncAnthropic
import openai
from openai import AsyncOpenAI
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.database import get_db
from app.models import PulseResponse


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AIAnalysisEngine:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "openai")
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.redis_client = None
        self.cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self.timeout = int(os.getenv("AI_TIMEOUT_SECONDS", "30"))

    async def initialize_redis(self):
        if not self.redis_client:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(redis_url, decode_responses=True)

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()

    def _build_analysis_prompt(self, responses: List[Dict[str, Any]]) -> str:
        responses_text = "\n\n".join([
            f"Response {i+1}:\nQuestion: {r['question']}\nAnswer: {r['answer']}\nUser: {r['user_id']}"
            for i, r in enumerate(responses)
        ])
        
        return f"""Analyze the following pulse responses from a team. Provide a structured analysis.

{responses_text}

Provide your analysis in JSON format with these keys:
- sentiment: overall sentiment (positive/neutral/negative)
- sentiment_score: numerical score from -1.0 to 1.0
- themes: array of identified themes/topics
- blockers: array of identified blockers or issues
- insights: array of key insights or observations
- summary: brief summary (2-3 sentences)

Respond with valid JSON only."""

    async def _get_cache_key(self, pulse_id: str) -> str:
        return f"ai_analysis:{pulse_id}"

    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        await self.initialize_redis()
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    async def _set_cache(self, cache_key: str, data: Dict[str, Any]):
        await self.initialize_redis()
        try:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(data)
            )
        except Exception:
            pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APIError, openai.APITimeoutError))
    )
    async def _call_openai(self, prompt: str) -> str:
        response = await asyncio.wait_for(
            self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            ),
            timeout=self.timeout
        )
        return response.choices[0].message.content

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_anthropic(self, prompt: str) -> str:
        response = await asyncio.wait_for(
            self.anthropic_client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            ),
            timeout=self.timeout
        )
        return response.content[0].text

    async def _fallback_analysis(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "themes": ["Unable to analyze"],
            "blockers": [],
            "insights": ["AI analysis temporarily unavailable"],
            "summary": f"Analysis unavailable for {len(responses)} responses.",
            "fallback": True
        }

    async def analyze_pulse_responses(self, pulse_id: str, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        cache_key = await self._get_cache_key(pulse_id)
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result

        if not responses:
            return await self._fallback_analysis(responses)

        prompt = self._build_analysis_prompt(responses)
        
        try:
            if self.provider == AIProvider.ANTHROPIC:
                response_text = await self._call_anthropic(prompt)
            else:
                response_text = await self._call_openai(prompt)
            
            analysis = json.loads(response_text)
            analysis["analyzed_at"] = datetime.utcnow().isoformat()
            analysis["pulse_id"] = pulse_id
            analysis["response_count"] = len(responses)
            
            await self._set_cache(cache_key, analysis)
            await self._store_analysis(pulse_id, analysis)
            
            return analysis
            
        except Exception:
            fallback = await self._fallback_analysis(responses)
            await self._store_analysis(pulse_id, fallback)
            return fallback

    async def _store_analysis(self, pulse_id: str, analysis: Dict[str, Any]):
        async with get_db() as db:
            await db.execute(
                """INSERT INTO pulse_analyses (pulse_id, analysis_data, created_at)
                   VALUES (?, ?, ?) ON CONFLICT(pulse_id) DO UPDATE SET
                   analysis_data = excluded.analysis_data, updated_at = ?""",
                (pulse_id, json.dumps(analysis), datetime.utcnow(), datetime.utcnow())
            )
            await db.commit()


ai_engine = AIAnalysisEngine()
