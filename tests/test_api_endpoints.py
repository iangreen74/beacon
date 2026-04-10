"""Integration tests for API endpoints."""

from datetime import datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User, Team, Pulse


class TestPulseEndpoints:
    """Test pulse submission and retrieval endpoints."""

    def test_submit_pulse_authenticated(self, authenticated_client: TestClient, test_team: Team) -> None:
        """Test submitting a pulse as authenticated user."""
        response = authenticated_client.post(
            "/api/v1/pulses",
            json={
                "team_id": test_team.id,
                "sentiment": 4,
                "comment": "Productive day"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sentiment"] == 4
        assert data["comment"] == "Productive day"
        assert data["team_id"] == test_team.id

    def test_submit_pulse_unauthenticated(self, client: TestClient, test_team: Team) -> None:
        """Test submitting pulse without authentication fails."""
        response = client.post(
            "/api/v1/pulses",
            json={
                "team_id": test_team.id,
                "sentiment": 4,
                "comment": "Test"
            }
        )
        assert response.status_code == 401

    def test_get_team_pulses(self, authenticated_client: TestClient, test_pulses: list[Pulse], test_team: Team) -> None:
        """Test retrieving team pulses."""
        response = authenticated_client.get(f"/api/v1/teams/{test_team.id}/pulses")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
        assert all(pulse["team_id"] == test_team.id for pulse in data)


class TestTeamEndpoints:
    """Test team management endpoints."""

    def test_create_team(self, authenticated_client: TestClient) -> None:
        """Test creating a new team."""
        response = authenticated_client.post(
            "/api/v1/teams",
            json={
                "name": "New Team",
                "description": "A new team for testing"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Team"
        assert data["description"] == "A new team for testing"

    def test_get_team(self, authenticated_client: TestClient, test_team: Team) -> None:
        """Test retrieving a team by ID."""
        response = authenticated_client.get(f"/api/v1/teams/{test_team.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_team.id
        assert data["name"] == test_team.name

    def test_list_user_teams(self, authenticated_client: TestClient, test_team: Team) -> None:
        """Test listing teams for current user."""
        response = authenticated_client.get("/api/v1/teams")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(team["id"] == test_team.id for team in data)


class TestTrendEndpoints:
    """Test trend detection and analysis endpoints."""

    def test_get_sentiment_trends(self, authenticated_client: TestClient, test_pulses: list[Pulse], test_team: Team) -> None:
        """Test retrieving sentiment trends for a team."""
        response = authenticated_client.get(f"/api/v1/teams/{test_team.id}/trends")
        assert response.status_code == 200
        data = response.json()
        assert "average_sentiment" in data
        assert "trend" in data
        assert isinstance(data["average_sentiment"], (int, float))

    def test_detect_anomalies(self, authenticated_client: TestClient, test_team: Team) -> None:
        """Test anomaly detection endpoint."""
        response = authenticated_client.get(f"/api/v1/teams/{test_team.id}/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
