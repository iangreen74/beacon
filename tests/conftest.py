"""Pytest configuration and shared fixtures."""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, Team, Pulse
from app.auth.dependencies import get_current_user


# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """Create test client with database dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        full_name="Test User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_team(db: Session, test_user: User) -> Team:
    """Create a test team."""
    team = Team(
        name="Test Team",
        owner_id=test_user.id,
        description="A test team"
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@pytest.fixture
def test_pulses(db: Session, test_user: User, test_team: Team) -> list[Pulse]:
    """Create test pulses with varying sentiments."""
    pulses_data = [
        {"sentiment": 5, "comment": "Great day!"},
        {"sentiment": 4, "comment": "Good progress"},
        {"sentiment": 3, "comment": "Okay"},
        {"sentiment": 2, "comment": "Struggling"},
        {"sentiment": 1, "comment": "Very difficult"},
    ]
    
    pulses = []
    for pulse_data in pulses_data:
        pulse = Pulse(
            user_id=test_user.id,
            team_id=test_team.id,
            sentiment=pulse_data["sentiment"],
            comment=pulse_data["comment"]
        )
        db.add(pulse)
        pulses.append(pulse)
    
    db.commit()
    for pulse in pulses:
        db.refresh(pulse)
    return pulses


@pytest.fixture
def authenticated_client(client: TestClient, test_user: User) -> TestClient:
    """Create an authenticated test client."""
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    return client


@pytest.fixture(autouse=True)
def reset_overrides():
    """Reset dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()
