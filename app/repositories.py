"""Repository pattern implementation for data access."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.database import User, Team, PulseResponse, AnalysisResult


class UserRepository:
    """Repository for user data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Create a new user."""
        self.session.add(user)
        await self.session.flush()
        return user


class TeamRepository:
    """Repository for team data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, team_id: int) -> Optional[Team]:
        """Get team by ID."""
        result = await self.session.execute(
            select(Team).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: int) -> List[Team]:
        """Get all teams owned by a user."""
        result = await self.session.execute(
            select(Team).where(Team.owner_id == owner_id)
        )
        return list(result.scalars().all())

    async def create(self, team: Team) -> Team:
        """Create a new team."""
        self.session.add(team)
        await self.session.flush()
        return team


class PulseResponseRepository:
    """Repository for pulse response data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_team(self, team_id: int) -> List[PulseResponse]:
        """Get all pulse responses for a team."""
        result = await self.session.execute(
            select(PulseResponse).where(PulseResponse.team_id == team_id)
        )
        return list(result.scalars().all())

    async def create(self, pulse_response: PulseResponse) -> PulseResponse:
        """Create a new pulse response."""
        self.session.add(pulse_response)
        await self.session.flush()
        return pulse_response


class AnalysisResultRepository:
    """Repository for analysis result data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_team(self, team_id: int) -> List[AnalysisResult]:
        """Get all analysis results for a team."""
        result = await self.session.execute(
            select(AnalysisResult).where(AnalysisResult.team_id == team_id)
        )
        return list(result.scalars().all())

    async def create(self, analysis_result: AnalysisResult) -> AnalysisResult:
        """Create a new analysis result."""
        self.session.add(analysis_result)
        await self.session.flush()
        return analysis_result
