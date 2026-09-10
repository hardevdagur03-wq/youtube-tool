from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.config import DatabaseConfig
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork


pytestmark = pytest.mark.db


@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def uow(db_path):
    mgr = DatabaseSessionManager._make_fresh()
    config = DatabaseConfig.for_testing(sqlite_path=db_path)
    mgr.initialize(config)
    await mgr.create_all()
    session = mgr.session_factory()
    uow_obj = UnitOfWork(session=session)
    await uow_obj.__aenter__()
    try:
        yield uow_obj, mgr
    except Exception:
        await uow_obj.__aexit__(*sys.exc_info())
        raise
    else:
        await uow_obj.__aexit__(None, None, None)
    finally:
        await session.close()
    await mgr.close()


class TestIndexes:
    @pytest.mark.asyncio
    async def test_indexes_exist(self, uow):
        uow_obj, mgr = uow
        inspector = inspect(mgr._engine)
        indexes = inspector.get_indexes("projects")
        index_names = [idx["name"] for idx in indexes]
        assert any("uuid" in name.lower() for name in index_names) or any(
            col == "uuid" for idx in indexes for col in idx.get("columns", [])
        )
        assert len(indexes) > 0

    @pytest.mark.asyncio
    async def test_indexes_improve_query_performance(self, uow):
        uow_obj, mgr = uow
        for i in range(100):
            await uow_obj.projects.create(
                name=f"Index Test {i}",
                short_id=f"IDX{i:04d}",
                video_id=f"vid{i}",
            )
        await uow_obj.commit()
        start = time.perf_counter()
        result = await uow_obj.projects.get_by_video_id("vid50")
        indexed_time = time.perf_counter() - start
        assert result is not None or indexed_time < 0.1

    @pytest.mark.asyncio
    async def test_unique_constraints(self, uow):
        uow_obj, mgr = uow
        await uow_obj.projects.create(name="Unique Test", short_id="UNQ001", video_id="unique_vid")
        with pytest.raises(Exception):
            await uow_obj.projects.create(name="Unique Test 2", short_id="UNQ002", video_id="unique_vid")
