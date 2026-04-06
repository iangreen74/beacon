import os
import psutil
from typing import Dict, Any

from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text

from app.database import get_db
from app.logging_config import get_logger


router = APIRouter(tags=["monitoring"])
logger = get_logger()


http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

db_connection_pool_size = Gauge(
    "db_connection_pool_size",
    "Current database connection pool size"
)

active_users_gauge = Gauge(
    "active_users",
    "Number of active users"
)

memory_usage_bytes = Gauge(
    "memory_usage_bytes",
    "Current memory usage in bytes"
)

cpu_usage_percent = Gauge(
    "cpu_usage_percent",
    "Current CPU usage percentage"
)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "pulse-analyzer",
        "version": "1.0.0"
    }


@router.get("/health/live")
async def liveness_probe() -> Dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe() -> Dict[str, Any]:
    """Kubernetes readiness probe with database check."""
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"
        db_healthy = False
    
    return {
        "status": "ready" if db_healthy else "not_ready",
        "database": db_status,
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with system metrics."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    memory_usage_bytes.set(memory_info.rss)
    cpu_usage_percent.set(process.cpu_percent())
    
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
        "system": {
            "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
        },
        "service": {
            "name": "pulse-analyzer",
            "version": "1.0.0",
        }
    }


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    memory_usage_bytes.set(memory_info.rss)
    cpu_usage_percent.set(process.cpu_percent())
    
    metrics_output = generate_latest()
    
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST
    )
