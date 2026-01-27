"""
Database session factory and context managers for SQLAlchemy.
"""
import os
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://recipenow:recipenow@localhost:5432/recipenow")

# Convert to psycopg3 dialect for both sync and async
if DATABASE_URL.startswith("postgresql://"):
    SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
else:
    SYNC_DATABASE_URL = DATABASE_URL
    ASYNC_DATABASE_URL = DATABASE_URL

# Disable prepared statements for Supabase transaction-mode pooler compatibility
# See: https://supabase.com/docs/guides/database/connecting-to-postgres#transaction-pooler
CONNECT_ARGS = {"prepare_threshold": 0}

# Create sync engine (for background jobs and CLI)
engine = create_engine(
    SYNC_DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using them
    connect_args=CONNECT_ARGS,
)

# Create async engine (for FastAPI)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using them
    connect_args=CONNECT_ARGS,
)

# Session factories
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
AsyncSessionLocal = sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Sync context manager for database sessions.
    Usage:
        with get_db_session() as db:
            db.query(Recipe).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    Usage:
        async with get_async_db_session() as db:
            await db.execute(select(Recipe))
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_session() -> Session:
    """
    Dependency for FastAPI endpoints to get a database session.
    Usage in endpoints:
        def my_endpoint(db: Session = Depends(get_session)):
            ...
    """
    return SessionLocal()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency for FastAPI endpoints.
    """
    async with get_async_db_session() as session:
        yield session
