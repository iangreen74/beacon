"""Beacon — AI-powered team pulse checker."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import datetime
import os

from app.routers.pulses import router as pulses_router
from app.trend_routes import router as trends_router
from app.teams import router as teams_router
from app.monitoring import router as monitoring_router

app = FastAPI(title="Beacon", version="0.1.0")

templates = Jinja2Templates(directory="app/templates")

app.include_router(pulses_router)
app.include_router(trends_router)
app.include_router(teams_router)
app.include_router(monitoring_router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "beacon",
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Render dashboard home page."""
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "page_title": "Beacon Dashboard"}
    )


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    """Render dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "page_title": "Beacon Dashboard"}
    )
