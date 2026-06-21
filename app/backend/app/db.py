from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine(url: str) -> AsyncEngine:
    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        # StaticPool keeps a single underlying connection alive — required for
        # `:memory:` and shared-cache in-memory URIs (each new connection would
        # otherwise see an empty database).
        from sqlalchemy.pool import StaticPool

        return create_async_engine(
            url,
            echo=False,
            future=True,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
    return create_async_engine(
        url,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


_settings = get_settings()
engine: AsyncEngine = _build_engine(_settings.database_url)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def rebind_engine(url: str) -> None:
    # Used by tests to swap in an in-memory SQLite engine after import.
    global engine, SessionLocal
    engine = _build_engine(url)
    SessionLocal = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )
