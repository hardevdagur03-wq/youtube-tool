"""DB Session Lifecycle — wires DatabaseSessionManager into FastAPI app lifecycle.

Usage in webapp/main.py:

    from database.db_session import db_lifespan

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with db_lifespan():
            yield
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from database.config import DatabaseConfig
from database.session import db_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_lifespan(config: DatabaseConfig | None = None) -> AsyncIterator[None]:
    """FastAPI lifespan context manager for database lifecycle.

    Initializes the database connection pool on startup,
    creates tables if they don't exist, and disposes the pool on shutdown.
    """
    db_manager.initialize(config or DatabaseConfig.from_env())
    await db_manager.create_all()
    logger.info("Database tables ready")
    try:
        yield
    finally:
        await db_manager.close()
        logger.info("Database connections closed")


async def get_db_health() -> dict:
    """Return database health status."""
    healthy = db_manager.is_healthy()
    return {
        "healthy": healthy,
        "driver": db_manager._config.driver if db_manager._config else "unknown",
    }
