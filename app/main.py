"""Main FastAPI application with comprehensive OpenAPI documentation."""

from typing import Dict, Any
from fastapi import FastAPI, status
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

from app.routers import pulses, teams
from app.auth.middleware import AuthMiddleware
from app.middleware import DatabaseSessionMiddleware


def create_app() -> FastAPI:
    """Create and configure FastAPI application with OpenAPI documentation."""
    app = FastAPI(
        title="Team Pulse API",
        description="""Team sentiment tracking and analytics platform.
        
## Authentication

All endpoints except `/health` and `/metrics` require authentication.

**API Key Authentication:**
- Header: `X-API-Key: your-api-key`
- Obtain API keys from team settings

**Rate Limits:**
- 100 requests per minute per API key
- 1000 requests per hour per API key

## Webhooks

**Slack Integration:**
```
POST /webhooks/slack
Content-Type: application/json
```

**Microsoft Teams Integration:**
```
POST /webhooks/teams
Content-Type: application/json
```

## Error Codes

- `400` Bad Request - Invalid input data
- `401` Unauthorized - Missing or invalid authentication
- `403` Forbidden - Insufficient permissions
- `404` Not Found - Resource does not exist
- `422` Validation Error - Request data validation failed
- `429` Too Many Requests - Rate limit exceeded
- `500` Internal Server Error - Server-side error

## Architecture

The API follows a layered architecture:
- **Router Layer**: HTTP endpoint handlers
- **Service Layer**: Business logic
- **Data Layer**: Database models and queries
- **Cache Layer**: Redis for performance

## Database Schema

**Teams Table:**
- id: UUID (primary key)
- name: String
- created_at: DateTime

**Users Table:**
- id: UUID (primary key)
- email: String (unique)
- team_id: UUID (foreign key)

**Pulses Table:**
- id: UUID (primary key)
- user_id: UUID (foreign key)
- sentiment: Integer (1-5)
- timestamp: DateTime
        """,
        version="1.0.0",
        contact={
            "name": "API Support",
            "email": "support@teampulse.example.com",
        },
        license_info={
            "name": "MIT",
        },
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthMiddleware)
    app.add_middleware(DatabaseSessionMiddleware)

    # Routers
    app.include_router(
        pulses.router,
        prefix="/api/v1/pulses",
        tags=["Pulses"],
    )
    app.include_router(
        teams.router,
        prefix="/api/v1/teams",
        tags=["Teams"],
    )

    @app.get(
        "/health",
        tags=["Health"],
        status_code=status.HTTP_200_OK,
        response_description="Service health status",
        responses={
            200: {
                "description": "Service is healthy",
                "content": {
                    "application/json": {
                        "example": {"status": "ok", "version": "1.0.0"}
                    }
                },
            }
        },
    )
    async def health_check() -> Dict[str, str]:
        """Health check endpoint for monitoring and load balancers."""
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
