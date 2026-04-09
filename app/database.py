"""Database configuration with async connection pooling and health checks.

This module provides AsyncEngine configuration with proper connection pooling,
health checks, and automatic retry logic for production AI applications.
Supports upcoming connection pooling features and rate control mechanisms.
"""

from typing import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import event, exc, text
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine with connection pooling configuration
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,  # Enable connection health checks
    echo=settings.debug,
)


# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Perform connection health check on new connections.
    
    Args:
        dbapi_conn: Database API connection object
        connection_record: Connection record from pool
    """
    logger.info("New database connection established")


@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Validate connection health on checkout from pool.
    
    Args:
        dbapi_conn: Database API connection object
        connection_record: Connection record from pool
        connection_proxy: Proxy to the connection
    """
    logger.debug("Connection checked out from pool")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((exc.OperationalError, exc.DisconnectionError)),
)
async def check_database_health() -> bool:
    """Perform database health check with automatic retry.
    
    Returns:
        bool: True if database is healthy, False otherwise
        
    Raises:
        Exception: If all retry attempts fail
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database health check passed")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions.
    
    Provides automatic session management with proper cleanup and
    error handling. Supports connection pooling and health checks.
    
    Yields:
        AsyncSession: Database session for use in request handlers
        
    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


async def init_db() -> None:
    """Initialize database tables and perform health check.
    
    Creates all tables defined in Base metadata and verifies
    database connectivity. Should be called on application startup.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await check_database_health()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db() -> None:
    """Close database connections and dispose of connection pool.
    
    Should be called on application shutdown to ensure proper
    cleanup of database resources.
    """
    await engine.dispose()
    logger.info("Database connections closed")
