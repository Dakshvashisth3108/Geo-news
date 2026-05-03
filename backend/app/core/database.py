"""Async SQLAlchemy 2.0 engine, session factory, and Base declarative class.

Exports:
  * `Base`              — declarative base every model inherits from.
  * `engine`            — process-wide async engine.
  * `AsyncSessionLocal` — session factory for per-request sessions.
  * `get_db`            — FastAPI dependency yielding an `AsyncSession`.

Render.com PostgreSQL notes
---------------------------
* Render injects `DATABASE_URL` automatically. The format is
  `postgres://...` (legacy) and connections require SSL.
* SQLAlchemy + asyncpg need `postgresql+asyncpg://...`, and asyncpg does not
  understand `?sslmode=...` query params — SSL must be passed via
  `connect_args["ssl"]`. We normalize both transparently below.
"""

import ssl
from typing import Any, AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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


def _build_engine_kwargs(raw_url: str) -> tuple[str, dict[str, Any]]:
    """Normalize a Postgres URL for asyncpg and extract SSL into connect_args.

    Handles three real-world URL shapes:
      1. `postgres://...`                 (Render external/internal URL)
      2. `postgresql://...`               (libpq canonical)
      3. `postgresql+asyncpg://...`       (already correct)

    Strips `sslmode=` from the query string and converts it into an SSL
    context that asyncpg actually accepts.
    """
    parts = urlsplit(raw_url)

    # 1. Force the asyncpg driver.
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"

    # 2. Pull sslmode out of the query string; asyncpg can't parse it there.
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    sslmode: str | None = None
    remaining: list[tuple[str, str]] = []
    for key, value in query_pairs:
        if key == "sslmode":
            sslmode = value
        else:
            remaining.append((key, value))

    new_url = urlunsplit(
        (scheme, parts.netloc, parts.path, urlencode(remaining), parts.fragment)
    )

    connect_args: dict[str, Any] = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        # Render's managed cert chain isn't always in the system trust store,
        # so for `require` we deliberately don't verify. Bump to a stricter
        # context if you switch to a provider that publishes a verifiable CA.
        ctx = ssl.create_default_context()
        if sslmode == "require":
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    elif settings.ENVIRONMENT == "production":
        # Production safety net: even if the URL omits sslmode, force SSL.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    return new_url, connect_args


_db_url, _connect_args = _build_engine_kwargs(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,        # detect dropped Render connections gracefully
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,         # recycle every 30m to avoid idle disconnects
    connect_args=_connect_args,
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
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
