"""Tests for dashboard endpoints showing recent pulses."""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.database import PulseResponse, User, Team
from app.auth import create_access_token


def test_get_recent_pulses_authenticated(client: TestClient, db_session, test_user, test_team):
    """Test retrieving recent pulses as authenticated user."""
    # Create some test pulses
    for i in range(3):
        pulse = PulseResponse(
            user_id=test_user.id,
            health_score=7 + i,
            highlights=f"Test highlight {i}",
            blockers=f"Test blocker {i}" if i == 0 else None,
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        db_session.add(pulse)
    db_session.commit()
    
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/dashboard/recent-pulses", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "pulses" in data
    assert "total_count" in data
    assert data["total_count"] >= 3
    assert len(data["pulses"]) >= 3
    
    # Check pulse structure
    first_pulse = data["pulses"][0]
    assert "id" in first_pulse
    assert "user_name" in first_pulse
    assert "health_score" in first_pulse
    assert "blockers_exist" in first_pulse
    assert "submitted_at" in first_pulse


def test_get_recent_pulses_with_limit(client: TestClient, db_session, test_user):
    """Test recent pulses with limit parameter."""
    # Create 5 pulses
    for i in range(5):
        pulse = PulseResponse(
            user_id=test_user.id,
            health_score=8,
            highlights=f"Highlight {i}",
            created_at=datetime.utcnow() - timedelta(minutes=i * 10),
        )
        db_session.add(pulse)
    db_session.commit()
    
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/dashboard/recent-pulses?limit=2", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["pulses"]) <= 2
    assert data["showing_count"] <= 2


def test_get_recent_pulses_unauthorized(client: TestClient):
    """Test that unauthenticated users cannot access recent pulses."""
    response = client.get("/api/dashboard/recent-pulses")
    assert response.status_code == 401


def test_get_dashboard_stats(client: TestClient, db_session, test_user):
    """Test dashboard statistics endpoint."""
    # Create today's pulses
    for i in range(3):
        pulse = PulseResponse(
            user_id=test_user.id,
            health_score=8,
            highlights="Test",
            blockers="Blocker" if i == 0 else None,
            created_at=datetime.utcnow(),
        )
        db_session.add(pulse)
    db_session.commit()
    
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/dashboard/stats", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "total_pulses_today" in data
    assert "average_health_score" in data
    assert "active_blockers" in data
    assert "team_members_reported" in data
    assert data["total_pulses_today"] >= 3
    assert data["active_blockers"] >= 1


def test_get_dashboard_stats_empty(client: TestClient, test_user):
    """Test dashboard stats with no pulses."""
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/dashboard/stats", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_pulses_today"] == 0
    assert data["average_health_score"] == 0.0
    assert data["active_blockers"] == 0
