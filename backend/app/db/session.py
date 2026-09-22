from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _to_async_url(url: str) -> str:
    """sqlite:///x -> sqlite+aiosqlite:///x ; postgresql://x -> postgresql+asyncpg://x. Already-async
    URLs (sqlite+aiosqlite://, postgresql+asyncpg://) pass through unchanged."""
    if "+aiosqlite" in url or "+asyncpg" in url:
        return url
    if url.startswith("sqlite://"):
        return "sqlite+aiosqlite://" + url[len("sqlite://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    raise ValueError(f"Don't know the async driver for database URL scheme: {url.split('://', 1)[0]}")


def _sqlite_pragmas(dbapi_connection, _record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class Database:
    """Dual-mode during the sync->async migration.

    `session()` (sync, unchanged) keeps every not-yet-migrated caller working exactly as before.
    `async_session()` is the new path for migrated code. Both engines point at the same
    database - on SQLite, WAL mode lets the sync writer and the async writer coexist safely.
    Once every caller is migrated, delete the sync half (`engine`, `_factory`, `session()`).
    """

    def __init__(self, url: str):
        is_sqlite = _is_sqlite(url)

        # --- sync (legacy path, being phased out) ---
        connect_args = {"check_same_thread": False} if is_sqlite else {}
        self.engine = create_engine(url, connect_args=connect_args)
        if is_sqlite:
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)

        # --- async (the migration target) ---
        self.async_engine: AsyncEngine = create_async_engine(_to_async_url(url), connect_args=connect_args)
        if is_sqlite:
            # aiosqlite still opens real sqlite3 connections under the hood; pragmas attach the
            # same way, just on the engine's underlying sync_engine.
            event.listen(self.async_engine.sync_engine, "connect", _sqlite_pragmas)
        self._async_factory = async_sessionmaker(self.async_engine, expire_on_commit=False, class_=AsyncSession)

    def create_all(self) -> None:
        # Schema creation stays on the sync engine for now - both engines share one file/database,
        # so tables created here are immediately visible to the async engine too.
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:  # legacy sync path, being phased out
        session = self._factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def async_session(self) -> AsyncIterator[AsyncSession]:
        session = self._async_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def aclose(self) -> None:
        await self.async_engine.dispose()
