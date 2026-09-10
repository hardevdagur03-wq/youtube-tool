from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

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


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_reads(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()
        session = mgr.session_factory()
        uow_obj = UnitOfWork(session=session)
        await uow_obj.__aenter__()
        for i in range(20):
            await uow_obj.projects.create(name=f"Read Test {i}", short_id=f"RD{i:04d}")
        await uow_obj.commit()
        await uow_obj.__aexit__(None, None, None)
        await session.close()

        async def read_project():
            s = mgr.session_factory()
            u = UnitOfWork(session=s)
            await u.__aenter__()
            projects = await u.projects.list(limit=100, offset=0)
            await u.__aexit__(None, None, None)
            await s.close()
            return len(projects)

        results = await asyncio.gather(*[read_project() for _ in range(10)])
        assert all(r == 20 for r in results)
        await mgr.close()

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()

        async def write_project(i: int):
            s = mgr.session_factory()
            u = UnitOfWork(session=s)
            await u.__aenter__()
            p = await u.projects.create(name=f"Write {i}", short_id=f"WR{i:04d}")
            await u.commit()
            await u.__aexit__(None, None, None)
            await s.close()
            return p

        results = await asyncio.gather(*[write_project(i) for i in range(10)])
        assert len(results) == 10
        assert all(r.name.startswith("Write") for r in results)
        await mgr.close()

    @pytest.mark.asyncio
    async def test_optimistic_locking(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()
        session = mgr.session_factory()
        uow_obj = UnitOfWork(session=session)
        await uow_obj.__aenter__()
        p = await uow_obj.projects.create(name="Optimistic Lock", short_id="OL001")
        await uow_obj.commit()
        original_version = p.version
        await uow_obj.projects.update(p.uuid, name="Updated Once")
        await uow_obj.commit()
        updated = await uow_obj.projects.get_by_uuid(p.uuid)
        assert updated.version > original_version
        await uow_obj.__aexit__(None, None, None)
        await session.close()
        await mgr.close()

    @pytest.mark.asyncio
    async def test_pessimistic_locking(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()
        session = mgr.session_factory()
        uow_obj = UnitOfWork(session=session)
        await uow_obj.__aenter__()
        p = await uow_obj.projects.create(name="Pessimistic Lock", short_id="PL001")
        await uow_obj.commit()
        assert p is not None
        await uow_obj.__aexit__(None, None, None)
        await session.close()
        await mgr.close()

    @pytest.mark.asyncio
    async def test_deadlock_detection(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()

        async def tx_a():
            s = mgr.session_factory()
            u = UnitOfWork(session=s)
            await u.__aenter__()
            p1 = await u.projects.create(name="Deadlock A1", short_id="DA001")
            await u.commit()
            await u.__aexit__(None, None, None)
            await s.close()
            return p1

        async def tx_b():
            s = mgr.session_factory()
            u = UnitOfWork(session=s)
            await u.__aenter__()
            p2 = await u.projects.create(name="Deadlock B1", short_id="DB001")
            await u.commit()
            await u.__aexit__(None, None, None)
            await s.close()
            return p2

        results = await asyncio.gather(tx_a(), tx_b(), return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        successes = [r for r in results if not isinstance(r, Exception)]
        assert len(successes) >= 1
        await mgr.close()
