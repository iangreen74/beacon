"""Tests for database connection pooling and lifecycle management."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.database import (
    check_database_health,
    get_engine,
    get_session,
    get_session_factory,
    shutdown_database,
    startup_database,
)


@pytest.fixture
def mock_engine():
    """Fixture for mocked database engine."""
    engine = MagicMock()
    engine.dispose = AsyncMock()
    return engine


@pytest.fixture
def mock_connection():
    """Fixture for mocked database connection."""
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock()
    return conn


@pytest.mark.asyncio
class TestDatabase:
    """Test suite for database operations."""

    async def test_get_engine_creates_queuepool(self):
        """Test that get_engine creates engine with QueuePool."""
        with patch("app.database._engine", None):
            with patch("app.database.create_async_engine") as mock_create:
                mock_create.return_value = MagicMock()
                engine = get_engine()
                assert engine is not None
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["pool_size"] == 5
                assert call_kwargs["max_overflow"] == 15
                assert call_kwargs["pool_pre_ping"] is True

    async def test_get_session_factory(self):
        """Test session factory creation."""
        with patch("app.database._session_factory", None):
            with patch("app.database.get_engine") as mock_get_engine:
                mock_get_engine.return_value = MagicMock()
                factory = get_session_factory()
                assert factory is not None

    async def test_check_database_health_success(self, mock_engine, mock_connection):
        """Test successful database health check."""
        mock_engine.connect.return_value = mock_connection
        with patch("app.database.get_engine", return_value=mock_engine):
            result = await check_database_health()
            assert result is True
            mock_connection.execute.assert_called_once()

    async def test_check_database_health_failure(self, mock_engine):
        """Test database health check failure with retry."""
        mock_engine.connect.side_effect = Exception("Connection failed")
        with patch("app.database.get_engine", return_value=mock_engine):
            with pytest.raises(Exception):
                await check_database_health()

    async def test_startup_database(self, mock_engine, mock_connection):
        """Test database startup initialization."""
        mock_engine.connect.return_value = mock_connection
        with patch("app.database.get_engine", return_value=mock_engine):
            await startup_database()
            mock_connection.execute.assert_called_once_with("SELECT 1")

    async def test_shutdown_database(self, mock_engine):
        """Test graceful database shutdown."""
        with patch("app.database._engine", mock_engine):
            await shutdown_database()
            mock_engine.dispose.assert_called_once()

    async def test_get_session_commit(self):
        """Test session commits on success."""
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock()

        with patch("app.database.get_session_factory", return_value=mock_factory):
            async for session in get_session():
                assert session is mock_session
            mock_session.commit.assert_called_once()

    async def test_get_session_rollback_on_error(self):
        """Test session rollback on exception."""
        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock()

        with patch("app.database.get_session_factory", return_value=mock_factory):
            with pytest.raises(ValueError):
                async for session in get_session():
                    raise ValueError("Test error")
            mock_session.rollback.assert_called_once()
