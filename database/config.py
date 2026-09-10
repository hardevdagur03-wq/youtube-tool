from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class DatabaseConfig:
    driver: Literal["sqlite", "postgresql"] = "sqlite"
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    database: str = "yt_blog"
    sqlite_path: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_pre_ping: bool = True
    pool_recycle: int = 3600
    echo: bool = False
    connect_timeout: int = 10
    statement_timeout_ms: int = 30000
    ssl_mode: str = "prefer"
    application_name: str = "yt_blog_platform"

    @property
    def database_url(self) -> str:
        if self.driver == "sqlite":
            path = self.sqlite_path or str(Path.cwd() / "data" / "yt_blog.db")
            os.makedirs(str(Path(path).parent), exist_ok=True)
            return f"sqlite+aiosqlite:///{path}"
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
            f"?application_name={self.application_name}"
            f"&connect_timeout={self.connect_timeout}"
        )

    @property
    def sync_database_url(self) -> str:
        if self.driver == "sqlite":
            path = self.sqlite_path or str(Path.cwd() / "data" / "yt_blog.db")
            os.makedirs(str(Path(path).parent), exist_ok=True)
            return f"sqlite:///{path}"
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @classmethod
    def from_env(cls) -> DatabaseConfig:
        driver = os.getenv("DB_DRIVER", "sqlite").lower()
        return cls(
            driver=driver,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "yt_blog"),
            sqlite_path=os.getenv("DB_SQLITE_PATH", ""),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            pool_pre_ping=os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
            statement_timeout_ms=int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000")),
            ssl_mode=os.getenv("DB_SSL_MODE", "prefer"),
        )

    @classmethod
    def for_testing(cls, sqlite_path: str = ":memory:") -> DatabaseConfig:
        return cls(driver="sqlite", sqlite_path=sqlite_path, echo=False)
