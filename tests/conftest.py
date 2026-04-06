import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os

from app.main import app
from app.database import Base, get_db
from app.models import User, Team, Pulse
from app.auth import get_password_hash, create_access_token


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:testpass@localhost:5432/testdb")

engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        full_name="Test User",
        role="manager"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_team(db_session, test_user):
    """Create a test team."""
    team = Team(
        name="Engineering Team",
        manager_id=test_user.id,
        description="Test engineering team"
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture
def test_team_member(db_session, test_team):
    """Create a test team member."""
    member = User(
        email="member@example.com",
        hashed_password=get_password_hash("memberpass123"),
        full_name="Team Member",
        role="member",
        team_id=test_team.id
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)
    return member


@pytest.fixture
def test_pulses(db_session, test_team_member):
    """Create test pulse data."""
    pulses = [
        Pulse(
            user_id=test_team_member.id,
            mood_score=7,
            workload_level=6,
            blockers="None",
            achievements="Completed feature X",
            created_at=datetime.utcnow() - timedelta(days=i)
        )
        for i in range(5)
    ]
    db_session.add_all(pulses)
    db_session.commit()
    return pulses


@pytest.fixture
def auth_token(test_user):
    """Generate an authentication token for test user."""
    return create_access_token(data={"sub": test_user.email})


@pytest.fixture
def auth_headers(auth_token):
    """Generate authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def member_auth_token(test_team_member):
    """Generate an authentication token for test team member."""
    return create_access_token(data={"sub": test_team_member.email})


@pytest.fixture
def member_auth_headers(member_auth_token):
    """Generate authentication headers for team member."""
    return {"Authorization": f"Bearer {member_auth_token}"}
