"""React-based dashboard frontend serving and API integration.

Provides static file serving for React SPA and server-side rendering support.
Integrates with pulse, team, analytics, and notification APIs.
"""

from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Frontend build directory
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "build"
STATIC_DIR = FRONTEND_DIR / "static"


class DashboardConfig:
    """Configuration for dashboard features and API endpoints."""

    def __init__(self):
        self.api_base_url = "/api/v1"
        self.websocket_url = "/ws"
        self.refresh_interval = 30  # seconds
        self.chart_types = ["line", "bar", "pie", "timeline"]
        self.sentiment_colors = {
            "positive": "#10b981",
            "neutral": "#6b7280",
            "negative": "#ef4444"
        }

    def get_config(self) -> Dict[str, Any]:
        """Return frontend configuration as dict."""
        return {
            "apiBaseUrl": self.api_base_url,
            "websocketUrl": self.websocket_url,
            "refreshInterval": self.refresh_interval,
            "chartTypes": self.chart_types,
            "sentimentColors": self.sentiment_colors,
            "features": {
                "realTimeUpdates": True,
                "trendAnalysis": True,
                "teamComparison": True,
                "exportData": True
            }
        }


dashboard_config = DashboardConfig()


@router.get("/config", response_model=Dict[str, Any])
async def get_dashboard_config() -> Dict[str, Any]:
    """Get dashboard configuration for frontend."""
    return dashboard_config.get_config()


@router.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request) -> HTMLResponse:
    """Serve main dashboard SPA."""
    index_path = FRONTEND_DIR / "index.html"
    
    if not index_path.exists():
        logger.error(f"Frontend build not found at {FRONTEND_DIR}")
        raise HTTPException(
            status_code=503,
            detail="Dashboard is currently unavailable. Please contact support."
        )
    
    if AIOFILES_AVAILABLE:
        async with aiofiles.open(index_path, mode="r") as f:
            content = await f.read()
    else:
        with open(index_path, "r") as f:
            content = f.read()
    
    # Inject runtime config
    config_script = f"<script>window.__DASHBOARD_CONFIG__={dashboard_config.get_config()}</script>"
    content = content.replace("</head>", f"{config_script}</head>")
    
    return HTMLResponse(content=content)


@router.get("/teams/{team_id}", response_class=HTMLResponse)
async def serve_team_dashboard(team_id: int, request: Request) -> HTMLResponse:
    """Serve team-specific dashboard view."""
    return await serve_dashboard(request)


@router.get("/analytics", response_class=HTMLResponse)
async def serve_analytics_dashboard(request: Request) -> HTMLResponse:
    """Serve analytics dashboard view."""
    return await serve_dashboard(request)


def mount_static_files(app):
    """Mount static file directories for frontend assets."""
    if STATIC_DIR.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(STATIC_DIR)),
            name="static"
        )
        logger.info(f"Mounted static files from {STATIC_DIR}")
    else:
        logger.warning(f"Static directory not found at {STATIC_DIR}")
