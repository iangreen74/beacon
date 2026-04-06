import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


request_id_context: ContextVar[str] = ContextVar("request_id", default="")


def configure_logging(log_level: str = "INFO", log_file: str = "app.log") -> None:
    """Configure structured logging with loguru."""
    logger.remove()
    
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "request_id={extra[request_id]} | "
        "<level>{message}</level>"
    )
    
    logger.configure(
        extra={"request_id": ""}
    )
    
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
    )
    
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
    )
    
    logger.info("Logging configured successfully")


def configure_sentry(dsn: str, environment: str = "production") -> None:
    """Configure Sentry for error tracking."""
    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not installed, skipping Sentry configuration")
        return
    
    if not dsn:
        logger.warning("Sentry DSN not provided, skipping Sentry configuration")
        return
    
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )
    logger.info(f"Sentry configured for environment: {environment}")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging and performance monitoring."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(time.time_ns()))
        request_id_context.set(request_id)
        
        log = logger.bind(request_id=request_id)
        
        start_time = time.perf_counter()
        
        log.info(
            f"Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        try:
            response = await call_next(request)
            
            duration = time.perf_counter() - start_time
            
            log.info(
                f"Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(duration * 1000, 2))
            
            return response
            
        except Exception as exc:
            duration = time.perf_counter() - start_time
            
            log.error(
                f"Request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(exc),
                }
            )
            raise


def get_logger():
    """Get logger instance with current request context."""
    request_id = request_id_context.get()
    return logger.bind(request_id=request_id)


def utc_now() -> datetime:
    """Return current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)
