from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.base import Base
from database.config import DatabaseConfig
from database.session import DatabaseSessionManager


pytestmark = pytest.mark.db


class TestMigrations:
    @pytest.mark.asyncio
    async def test_migration_applies_cleanly(self):
        config = DatabaseConfig.for_testing()
        mgr = DatabaseSessionManager._make_fresh()
        mgr.initialize(config)
        await mgr.create_all()
        inspector = inspect(mgr._engine)
        tables = inspector.get_table_names()
        expected_tables = {
            "projects", "videos", "transcripts", "analysis",
            "knowledge_graphs", "seo_analyses", "outlines", "sections",
            "drafts", "reviews", "optimizations", "exports",
            "versions", "pipeline_states", "audit_logs", "background_jobs",
        }
        for table in expected_tables:
            assert table in tables, f"Table '{table}' missing after migration"
        await mgr.close()

    @pytest.mark.asyncio
    async def test_migration_rollback(self):
        config = DatabaseConfig.for_testing()
        mgr = DatabaseSessionManager._make_fresh()
        mgr.initialize(config)
        await mgr.create_all()
        inspector = inspect(mgr._engine)
        tables_before = set(inspector.get_table_names())
        Base.metadata.drop_all(mgr._engine)
        inspector = inspect(mgr._engine)
        tables_after = set(inspector.get_table_names())
        assert len(tables_after) < len(tables_before)
        await mgr.create_all()
        inspector = inspect(mgr._engine)
        tables_restored = set(inspector.get_table_names())
        assert tables_restored == tables_before
        await mgr.close()

    @pytest.mark.asyncio
    async def test_migration_idempotent(self):
        config = DatabaseConfig.for_testing()
        mgr = DatabaseSessionManager._make_fresh()
        mgr.initialize(config)
        await mgr.create_all()
        inspector = inspect(mgr._engine)
        tables_first = set(inspector.get_table_names())
        await mgr.create_all()
        tables_second = set(inspector.get_table_names())
        assert tables_first == tables_second
        await mgr.close()

    @pytest.mark.asyncio
    async def test_schema_after_migration(self):
        config = DatabaseConfig.for_testing()
        mgr = DatabaseSessionManager._make_fresh()
        mgr.initialize(config)
        await mgr.create_all()
        inspector = inspect(mgr._engine)
        columns = {col["name"] for col in inspector.get_columns("projects")}
        expected_columns = {
            "uuid", "name", "short_id", "video_id", "status",
            "language", "description", "raw_data",
            "created_at", "updated_at", "is_deleted", "version",
        }
        assert expected_columns.issubset(columns), (
            f"Missing columns: {expected_columns - columns}"
        )
        await mgr.close()
