"""
SQLAlchemy database configuration and session management.
"""

from __future__ import annotations

from typing import AsyncGenerator, Optional

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Naming convention for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    metadata = metadata


# Create async engine only if database URL is configured
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None

if settings.database_url:
    # Import NullPool for serverless environments
    from sqlalchemy.pool import NullPool
    
    # Determine if we're in a serverless environment (Cloud Run, etc.)
    is_serverless = settings.app_env == "prod"
    
    # Configure engine with serverless-optimized settings
    engine_kwargs = {
        "echo": settings.is_development,
        # CRITICAL: pool_pre_ping validates connections before use
        # This prevents "closed transport" errors from stale connections
        "pool_pre_ping": True,
        # CRITICAL: Aggressively recycle connections (30s for serverless)
        # Cloud Run instances can be paused/resumed, causing stale connections
        "pool_recycle": 30 if is_serverless else 300,
        # Enable connection pooling optimizations
        "connect_args": {
            "charset": "utf8mb4",
            "autocommit": False,
            "sql_mode": "TRADITIONAL",
            # Add these for proper emoji support
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "use_unicode": True,
            # CRITICAL: Set connection timeout to detect dead connections faster
            "connect_timeout": 10,
        } if "mysql" in settings.database_url else {}
    }
    
    if is_serverless:
        # Use NullPool for Cloud Run - no connection pooling
        # Each request gets a fresh connection, preventing stale connection issues
        engine_kwargs["poolclass"] = NullPool
    else:
        # Use connection pooling for non-serverless (dev/local)
        engine_kwargs.update({
            "pool_size": 5,  # Smaller pool for better resource management
            "max_overflow": 10,  # Allow some overflow connections
            "pool_timeout": 30,  # Timeout for getting connection from pool
        })
    
    engine = create_async_engine(
        settings.database_url,
        **engine_kwargs
    )
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        RuntimeError: If database is not configured
    """
    if async_session_maker is None:
        raise RuntimeError("Database is not configured. Please set DATABASE_URL environment variable.")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            # Rollback on any error to prevent leaving transactions open
            await session.rollback()
            raise
        finally:
            # Always close the session to return connection to pool (or dispose if NullPool)
            await session.close()
