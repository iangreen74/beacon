from typing import Optional, Any
import json
import redis.asyncio as redis
from functools import wraps
import hashlib
from datetime import timedelta

from app.database import get_settings


class RedisCache:
    """Redis cache manager for AI analysis results and frequently accessed data."""
    
    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection pool."""
        settings = get_settings()
        redis_url = settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379/0"
        
        self._pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=20,
            decode_responses=True
        )
        self._client = redis.Redis(connection_pool=self._pool)
    
    async def close(self):
        """Close Redis connection pool."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._client:
            return None
        
        value = await self._client.get(key)
        if value:
            return json.loads(value)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL in seconds."""
        if not self._client:
            return
        
        serialized = json.dumps(value)
        await self._client.setex(key, ttl, serialized)
    
    async def delete(self, key: str):
        """Delete key from cache."""
        if not self._client:
            return
        
        await self._client.delete(key)
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        if not self._client:
            return
        
        keys = await self._client.keys(pattern)
        if keys:
            await self._client.delete(*keys)
    
    def generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and parameters."""
        params = f"{args}:{kwargs}"
        hash_suffix = hashlib.md5(params.encode()).hexdigest()[:8]
        return f"{prefix}:{hash_suffix}"


# Global cache instance
cache_manager = RedisCache()


def cached(prefix: str, ttl: int = 3600):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = cache_manager.generate_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


async def get_cache_manager() -> RedisCache:
    """Dependency for getting cache manager instance."""
    return cache_manager
