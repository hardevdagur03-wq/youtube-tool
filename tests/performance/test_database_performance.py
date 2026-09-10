from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from database.config import DatabaseConfig
from database.session import DatabaseSessionManager
from database.unit_of_work import UnitOfWork


pytestmark = pytest.mark.performance


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
        yield uow_obj
    except Exception:
        await uow_obj.__aexit__(*sys.exc_info())
        raise
    else:
        await uow_obj.__aexit__(None, None, None)
    finally:
        await session.close()
    await mgr.close()


class TestDatabasePerformance:
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, uow, performance_config):
        start = time.perf_counter()
        for i in range(100):
            await uow.projects.create(
                name=f"Bulk Project {i}",
                short_id=f"BP{i:04d}",
                video_id=f"vid{i}",
            )
        duration = time.perf_counter() - start
        assert duration < performance_config["bulk_insert_threshold_s"], (
            f"Bulk insert 100 projects took {duration:.3f}s, threshold {performance_config['bulk_insert_threshold_s']}s"
        )

    @pytest.mark.asyncio
    async def test_complex_query_performance(self, uow, performance_config):
        for i in range(50):
            await uow.projects.create(
                name=f"Query Project {i}",
                short_id=f"QP{i:03d}",
                video_id=f"qvid{i}",
                status="completed" if i % 2 == 0 else "running",
                language="en" if i % 3 == 0 else "es",
            )
        start = time.perf_counter()
        results = await uow.projects.search_text("Query")
        duration = (time.perf_counter() - start) * 1000
        assert duration < performance_config["db_query_threshold_ms"], (
            f"Search query took {duration:.1f}ms, threshold {performance_config['db_query_threshold_ms']}ms"
        )
        assert len(results) >= 50

    @pytest.mark.asyncio
    async def test_pagination_performance(self, uow, performance_config):
        for i in range(100):
            await uow.projects.create(
                name=f"Page Project {i}",
                short_id=f"PP{i:04d}",
            )
        start = time.perf_counter()
        page = await uow.projects.paginate(page=5, page_size=20)
        duration = (time.perf_counter() - start) * 1000
        assert duration < performance_config["db_query_threshold_ms"], (
            f"Pagination took {duration:.1f}ms, threshold {performance_config['db_query_threshold_ms']}ms"
        )
        assert len(page.items) == 20
        assert page.total == 100

    @pytest.mark.asyncio
    async def test_full_text_search_performance(self, uow, performance_config):
        for i in range(30):
            await uow.projects.create(
                name=f"Searchable Unique Project {i}",
                short_id=f"SUP{i:03d}",
                description=f"A unique description for project number {i}",
            )
        start = time.perf_counter()
        results = await uow.projects.search_text("Unique Project")
        duration = (time.perf_counter() - start) * 1000
        assert duration < performance_config["db_query_threshold_ms"], (
            f"Full text search took {duration:.1f}ms, threshold {performance_config['db_query_threshold_ms']}ms"
        )
        assert len(results) >= 30
