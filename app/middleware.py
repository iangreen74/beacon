"""Middleware components for request processing and rate limiting.

Provides rate limiting functionality to protect analysis endpoints
from abuse and ensure fair resource allocation.
"""

from typing import Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimiter:
    """Token bucket rate limiter for API endpoints.
    
    Implements per-user rate limiting with configurable limits
    and time windows. Thread-safe implementation.
    """
    
    def __init__(self, requests_per_minute: int = 10, requests_per_hour: int = 100):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per user
            requests_per_hour: Maximum requests per hour per user
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets: Dict[str, list] = defaultdict(list)
        self.hour_buckets: Dict[str, list] = defaultdict(list)
        self.lock = threading.Lock()
    
    def _clean_old_requests(self, bucket: list, window_seconds: int) -> None:
        """Remove expired timestamps from bucket.
        
        Args:
            bucket: List of request timestamps
            window_seconds: Time window in seconds
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """Check if user has exceeded rate limits.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        with self.lock:
            key = str(user_id)
            now = datetime.now()
            
            # Check minute limit
            minute_bucket = self.minute_buckets[key]
            self._clean_old_requests(minute_bucket, 60)
            
            if len(minute_bucket) >= self.requests_per_minute:
                return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
            
            # Check hour limit
            hour_bucket = self.hour_buckets[key]
            self._clean_old_requests(hour_bucket, 3600)
            
            if len(hour_bucket) >= self.requests_per_hour:
                return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
            
            # Add current request
            minute_bucket.append(now)
            hour_bucket.append(now)
            
            return True, ""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for applying rate limits to analysis endpoints.
    
    Automatically applies rate limiting to configured endpoint patterns.
    """
    
    def __init__(self, app, rate_limiter: RateLimiter, protected_paths: list = None):
        """Initialize rate limit middleware.
        
        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
            protected_paths: List of path patterns to protect (default: analysis endpoints)
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.protected_paths = protected_paths or ["/api/v1/analysis", "/api/v1/analyze"]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and apply rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler or rate limit error
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Check if path should be rate limited
        if any(request.url.path.startswith(path) for path in self.protected_paths):
            # Extract user_id from request (assuming it's in headers or auth)
            user_id = request.headers.get("X-User-ID")
            
            if not user_id:
                # Try to get from request state (set by auth middleware)
                user_id = getattr(request.state, "user_id", None)
            
            if user_id:
                try:
                    user_id_int = int(user_id)
                    allowed, message = self.rate_limiter.check_rate_limit(user_id_int)
                    
                    if not allowed:
                        raise HTTPException(status_code=429, detail=message)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid user ID")
        
        response = await call_next(request)
        return response
