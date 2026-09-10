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
from database.rollback_engine import RollbackEngine
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


@pytest_asyncio.fixture
async def rollback_engine(uow):
    return RollbackEngine(uow)


class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_entity_changes(self, uow, rollback_engine):
        p = await uow.projects.create(name="Original Name", short_id="RB001")
        await uow.commit()
        await uow.projects.update(p.uuid, name="Modified Name")
        result = await rollback_engine.rollback_entity("project", p.uuid)
        assert result is True
        refreshed = await uow.projects.get_by_uuid(p.uuid)
        assert refreshed.name == "Original Name"

    @pytest.mark.asyncio
    async def test_rollback_across_multiple_entities(self, uow, rollback_engine):
        p1 = await uow.projects.create(name="Entity 1", short_id="ME001")
        p2 = await uow.projects.create(name="Entity 2", short_id="ME002")
        p3 = await uow.projects.create(name="Entity 3", short_id="ME003")
        await uow.commit()
        r1 = await rollback_engine.rollback_entity("project", p1.uuid)
        r2 = await rollback_engine.rollback_entity("project", p2.uuid)
        assert r1 is True
        assert r2 is True

    @pytest.mark.asyncio
    async def test_rollback_preserves_audit_trail(self, uow, rollback_engine):
        p = await uow.projects.create(name="Audit Trail", short_id="AT001")
        await uow.commit()
        await uow.projects.update(p.uuid, name="Changed")
        await uow.commit()
        await rollback_engine.rollback_entity("project", p.uuid)
        audit_logs = await uow.audit_logs.list(limit=10)
        assert len(audit_logs) >= 2

    @pytest.mark.asyncio
    async def test_rollback_invalid_entity(self, uow, rollback_engine):
        result = await rollback_engine.rollback_entity("project", "non_existent_uuid")
        assert result is False
