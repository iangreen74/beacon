"""Main FastAPI application entry point with OpenAPI documentation configuration."""

from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from app.routers import pulses, teams
from app.auth.middleware import AuthMiddleware
from app.middleware import DatabaseSessionMiddleware
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    if SENTRY_AVAILABLE and settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            environment=settings.ENVIRONMENT,
        )
    yield
    # Shutdown


app = FastAPI(
    title="Team Pulse API",
    description="""
## Team Pulse API

A comprehensive API for collecting and analyzing team sentiment through pulse surveys.

### Authentication

All endpoints (except `/health`) require authentication via Bearer token:

```
Authorization: Bearer <your_token>
```

### Rate Limits

- Default: 100 requests per minute per IP
- Authenticated: 1000 requests per minute per user
- Pulse submission: 10 per hour per user

### Error Codes

- `400` - Bad Request: Invalid input data
- `401` - Unauthorized: Missing or invalid authentication
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource does not exist
- `422` - Validation Error: Request data failed validation
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Unexpected server error

### Common Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```
    """,
    version="1.0.0",
    contact={
        "name": "Team Pulse Support",
        "email": "support@teampulse.example.com",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "pulses",
            "description": "Operations for pulse survey collection and sentiment tracking",
        },
        {
            "name": "teams",
            "description": "Team management and member operations",
        },
        {
            "name": "health",
            "description": "Health check and monitoring endpoints",
        },
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(DatabaseSessionMiddleware)

# Include routers
app.include_router(pulses.router, prefix="/api/v1/pulses", tags=["pulses"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])


@app.get(
    "/health",
    tags=["health"],
    summary="Health check endpoint",
    description="Returns the health status of the API. Does not require authentication.",
    response_description="Service health status",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {"status": "healthy", "version": "1.0.0"}
                }
            },
        },
    },
)
async def health_check() -> Dict[str, str]:
    """Check if the API service is running and healthy."""
    return {"status": "healthy", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )
