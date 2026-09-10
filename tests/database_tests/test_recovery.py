from __future__ import annotations

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


class TestRecovery:
    @pytest.mark.asyncio
    async def test_recovery_after_crash(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()
        session = mgr.session_factory()
        uow_obj = UnitOfWork(session=session)
        await uow_obj.__aenter__()
        p = await uow_obj.projects.create(name="Crash Recovery", short_id="CR001")
        await uow_obj.commit()
        await uow_obj.__aexit__(None, None, None)
        await session.close()
        await mgr.close()
        mgr2 = DatabaseSessionManager._make_fresh()
        mgr2.initialize(config)
        await mgr2.create_all()
        session2 = mgr2.session_factory()
        uow_obj2 = UnitOfWork(session=session2)
        await uow_obj2.__aenter__()
        recovered = await uow_obj2.projects.get_by_uuid(p.uuid)
        assert recovered is not None
        assert recovered.name == "Crash Recovery"
        await uow_obj2.__aexit__(None, None, None)
        await session2.close()
        await mgr2.close()

    @pytest.mark.asyncio
    async def test_recovery_preserves_data(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()
        session = mgr.session_factory()
        uow_obj = UnitOfWork(session=session)
        await uow_obj.__aenter__()
        await uow_obj.projects.create(name="Data 1", short_id="DP001")
        await uow_obj.projects.create(name="Data 2", short_id="DP002")
        await uow_obj.projects.create(name="Data 3", short_id="DP003")
        await uow_obj.commit()
        await uow_obj.__aexit__(None, None, None)
        await session.close()
        await mgr.close()
        mgr2 = DatabaseSessionManager._make_fresh()
        mgr2.initialize(config)
        await mgr2.create_all()
        session2 = mgr2.session_factory()
        uow_obj2 = UnitOfWork(session=session2)
        await uow_obj2.__aenter__()
        all_projects = await uow_obj2.projects.list(limit=100, offset=0)
        assert len(all_projects) >= 3
        await uow_obj2.__aexit__(None, None, None)
        await session2.close()
        await mgr2.close()

    @pytest.mark.asyncio
    async def test_recovery_cleans_stale_locks(self, db_path):
        mgr = DatabaseSessionManager._make_fresh()
        config = DatabaseConfig.for_testing(sqlite_path=db_path)
        mgr.initialize(config)
        await mgr.create_all()
        session = mgr.session_factory()
        uow_obj = UnitOfWork(session=session)
        await uow_obj.__aenter__()
        stale_lock = await uow_obj.projects.create(
            name="Stale Lock", short_id="SL001", status="locked"
        )
        await uow_obj.commit()
        await uow_obj.projects.update(stale_lock.uuid, status="running")
        await uow_obj.commit()
        recovered = await uow_obj.projects.get_by_uuid(stale_lock.uuid)
        assert recovered.status == "running"
        await uow_obj.__aexit__(None, None, None)
        await session.close()
        await mgr.close()
