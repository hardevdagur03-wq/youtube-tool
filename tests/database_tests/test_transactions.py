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


class TestTransactions:
    @pytest.mark.asyncio
    async def test_transaction_commit(self, uow):
        p = await uow.projects.create(name="Commit Test", short_id="CT001")
        await uow.commit()
        found = await uow.projects.get_by_uuid(p.uuid)
        assert found is not None
        assert found.name == "Commit Test"

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, uow):
        p = await uow.projects.create(name="Rollback Test", short_id="RT001")
        await uow.rollback()
        found = await uow.projects.get_by_uuid(p.uuid)
        assert found is None

    @pytest.mark.asyncio
    async def test_nested_transactions(self, uow):
        p1 = await uow.projects.create(name="Nested 1", short_id="NT001")
        await uow.projects.create(name="Nested 2", short_id="NT002")
        p3 = await uow.projects.create(name="Nested 3", short_id="NT003")
        await uow.commit()
        found1 = await uow.projects.get_by_uuid(p1.uuid)
        found3 = await uow.projects.get_by_uuid(p3.uuid)
        assert found1 is not None
        assert found3 is not None

    @pytest.mark.asyncio
    async def test_savepoint_rollback(self, uow):
        p1 = await uow.projects.create(name="Savepoint 1", short_id="SP001")
        sp = uow.session.begin_nested()
        p2 = await uow.projects.create(name="Savepoint 2", short_id="SP002")
        await sp.rollback()
        await uow.commit()
        found1 = await uow.projects.get_by_uuid(p1.uuid)
        found2 = await uow.projects.get_by_uuid(p2.uuid)
        assert found1 is not None
        assert found2 is None

    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, db_path):
        async def create_project_in_tx(name: str, short_id: str):
            mgr = DatabaseSessionManager._make_fresh()
            config = DatabaseConfig.for_testing(sqlite_path=db_path)
            mgr.initialize(config)
            await mgr.create_all()
            session = mgr.session_factory()
            uow_obj = UnitOfWork(session=session)
            await uow_obj.__aenter__()
            try:
                p = await uow_obj.projects.create(name=name, short_id=short_id)
                await uow_obj.commit()
                return p
            finally:
                await uow_obj.__aexit__(None, None, None)
                await session.close()
                await mgr.close()

        import asyncio
        results = await asyncio.gather(
            create_project_in_tx("Concurrent 1", "CC001"),
            create_project_in_tx("Concurrent 2", "CC002"),
            create_project_in_tx("Concurrent 3", "CC003"),
        )
        assert len(results) == 3
        assert results[0].name == "Concurrent 1"
        assert results[1].name == "Concurrent 2"
        assert results[2].name == "Concurrent 3"
