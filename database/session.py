from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from database.base import Base
from database.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    _instance: DatabaseSessionManager | None = None
    _engine: AsyncEngine | None = None
    _session_factory: async_sessionmaker[AsyncSession] | None = None
    _config: DatabaseConfig | None = None

    def __new__(cls) -> DatabaseSessionManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, config: DatabaseConfig | None = None) -> None:
        if self._engine is not None:
            return

        self._config = config or DatabaseConfig.from_env()
        url = self._config.database_url

        engine_kwargs: dict = {
            "echo": self._config.echo,
            "pool_pre_ping": self._config.pool_pre_ping,
            "pool_recycle": self._config.pool_recycle,
            "connect_args": {},
        }

        if self._config.driver == "sqlite":
            engine_kwargs["connect_args"]["check_same_thread"] = False
            if ":memory:" in url:
                engine_kwargs["poolclass"] = StaticPool
            else:
                engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = self._config.pool_size
            engine_kwargs["max_overflow"] = self._config.max_overflow
            engine_kwargs["connect_args"]["command_timeout"] = self._config.connect_timeout

            if self._config.statement_timeout_ms:
                engine_kwargs["connect_args"]["server_settings"] = {
                    "statement_timeout": str(self._config.statement_timeout_ms),
                }

        self._engine = create_async_engine(url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info(
            "Database initialized: driver=%s, pool=%d",
            self._config.driver, self._config.pool_size,
        )

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError("DatabaseSessionManager not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("DatabaseSessionManager not initialized. Call initialize() first.")
        return self._session_factory

    async def create_all(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created.")

    async def drop_all(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("All database tables dropped.")

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connection closed.")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def session_no_commit(self) -> AsyncIterator[AsyncSession]:
        session = self.session_factory()
        try:
            yield session
        finally:
            await session.close()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session() as session:
            yield session

    def is_healthy(self) -> bool:
        return self._engine is not None


db_manager = DatabaseSessionManager()
