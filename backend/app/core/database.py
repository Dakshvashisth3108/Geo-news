"""Async SQLAlchemy 2.0 engine, session factory, and Base declarative class.

We expose:
  * `Base`              — declarative base every model inherits from.
  * `engine`            — process-wide async engine.
  * `AsyncSessionLocal` — session factory used to create per-request sessions.
  * `get_db`            — FastAPI dependency that yields an `AsyncSession`.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Common declarative base. Models import this and subclass it."""
    pass


# `echo` is on in debug to log SQL; `future=True` is implicit in SQLAlchemy 2.0.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. Yields a session and ensures it is closed."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables from metadata. Useful in dev; use Alembic in prod."""
    # Import models so they register with Base.metadata before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
