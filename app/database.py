"""Database configuration with connection pooling and lifecycle management."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/dbname"

# Connection pool settings
POOL_SIZE = 5
MAX_OVERFLOW = 15
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600
POOL_PRE_PING = True

# Global engine instance
_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine with QueuePool configuration."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_timeout=POOL_TIMEOUT,
            pool_recycle=POOL_RECYCLE,
            pool_pre_ping=POOL_PRE_PING,
            echo=False,
        )
        logger.info(
            "Database engine created with QueuePool (size=%d, max_overflow=%d)",
            POOL_SIZE,
            MAX_OVERFLOW,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Session factory created")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def check_database_health() -> bool:
    """Perform database health check with retry logic."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
            logger.debug("Database health check passed")
            return True
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        raise


async def startup_database() -> None:
    """Initialize database connections on application startup."""
    logger.info("Starting database connections")
    try:
        engine = get_engine()
        # Warm up the connection pool
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database startup complete")
    except Exception as e:
        logger.error("Database startup failed: %s", str(e))
        raise


async def shutdown_database() -> None:
    """Gracefully close database connections on application shutdown."""
    global _engine, _session_factory
    logger.info("Shutting down database connections")
    try:
        if _engine is not None:
            await _engine.dispose()
            _engine = None
            _session_factory = None
            logger.info("Database connections closed gracefully")
    except Exception as e:
        logger.error("Error during database shutdown: %s", str(e))
        raise


@asynccontextmanager
async def lifespan_context():
    """Context manager for database lifecycle in FastAPI lifespan."""
    await startup_database()
    try:
        yield
    finally:
        await shutdown_database()
